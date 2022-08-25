import logging.handlers
import sys

import uvicorn
from loguru import logger

from config import config
import api

if __name__ == '__main__':
    # configure logging
    if 'console' in config['logger']:
        CONSOLE_LEVEL = config['logger']['console'].get('log_level', 'INFO').upper()

        # remove default handler
        logger.remove()
        logger.add(sys.stderr, level=CONSOLE_LEVEL)

    if 'file' in config['logger']:
        FILE_NAME = config['logger']['file']['name']
        FILE_LEVEL = config['logger']['file'].get('log_level', 'INFO').upper()

        logger.add(FILE_NAME, level=FILE_LEVEL)

    if 'syslog' in config['logger']:
        SYSLOG_HOST = config['logger']['syslog']['host']
        SYSLOG_PORT = config['logger']['syslog'].get('port', 514)
        SYSLOG_LEVEL = config['logger']['syslog'].get('log_level', 'INFO').upper()

        handler = logging.handlers.SysLogHandler(
            address=(SYSLOG_HOST, SYSLOG_PORT))
        logger.add(handler, level=SYSLOG_LEVEL)

    HOST = config['web'].get('host', '0.0.0.0')
    PORT = config['web'].get('port', 8080)
    LOG_LEVEL = config['web'].get('log_level', 'INFO')
    PROXY = config['web'].get('proxy', '/')

    # start api
    uvicorn.run(api.app, host=HOST, port=PORT, root_path=PROXY, log_level=LOG_LEVEL)
