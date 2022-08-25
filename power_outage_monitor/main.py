import logging.handlers
import os
import subprocess
import sys
from pathlib import Path

import requests
import uvicorn
from loguru import logger

import config

if __name__ == '__main__':
    with logger.catch():
        # set configurations
        config_path = Path(__file__).with_name('config.yaml')
        if not config_path.is_file():
            # get JWT
            with open(os.environ['JWT_PATH']) as fp:
                jwt = fp.read().strip()

            # get token from vault
            VAULT_ADDR = os.environ['VAULT_ADDR']
            url = f'{VAULT_ADDR}/v1/auth/kubernetes/login'
            body = {
                'role': 'sops',
                'jwt': jwt
            }
            response = requests.post(url, json=body)
            response.raise_for_status()

            # set token
            os.putenv('VAULT_TOKEN', response.json()['auth']['client_token']) 

            # decrypt config file
            subprocess.run(['sops', '-d', f'{VAULT_ADDR}/v1/sops/keys/first-key', 'encrypted.yaml', '>', 'config.yaml'], check=True)
        config.set_config(config_path)

        HOST = config.config['web']['host']
        PORT = config.config['web']['port']
        LOG_LEVEL = config.config['web']['log_level']
        PROXY = config.config['web']['proxy']

        # configure logging
        logger.remove() # remove default handler
        if 'console' in config.config['logger']:
            logger.add(sys.stderr, level=config.config['logger']['console']['log_level'].upper())
        if 'file' in config.config['logger']:
            logger.add(config.config['logger']['file']['name'], level=config.config['logger']['file']['log_level'].upper())
        if 'syslog' in config.config['logger']:
            handler = logging.handlers.SysLogHandler(
                address=(config.config["logger"]["syslog"]["host"], config.config["logger"]["syslog"]["port"]))
            logger.add(handler, level=config.config['logger']['syslog']['log_level'].upper())

        # start api
        logger.info('Starting Power Outage Check API.')
        uvicorn.run('api:app', host=HOST, port=PORT, root_path=PROXY, log_level=LOG_LEVEL)
