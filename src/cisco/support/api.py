from oauthlib.oauth2 import BackendApplicationClient

from requests_oauthlib import OAuth2Session

class SupportApi:
    def __init__(self, client_id, client_secret):
        client = BackendApplicationClient(client_id)
        oauth = OAuth2Session(client=client)
        token = oauth.fetch_token(
            token_url='https://cloudsso.cisco.com/as/token.oauth2',
            client_id=client_id,
            client_secret=client_secret)
        self.session = OAuth2Session(client_id, token=token)

    def get_coverage_summary_by_sn(self, serial_numbers):
        url = 'https://api.cisco.com/sn2info/v2/coverage/summary/serial_numbers/'
        sn_path_params = ','.join(serial_numbers)
        response = self.session.get(url + sn_path_params)
        response.raise_for_status()
        payload = response.json()
        summeries = payload['serial_numbers']
        for i in range(2, payload['pagination_response_record']['last_index']):
            params = {'page_index': i}
            response = self.session.get(url + sn_path_params, params=params)
            response.raise_for_status()
            payload = response.json()
            summeries.extend(payload['serial_numbers'])
        return summeries

# for demo purposes
import requests
from config import config
URL = config['cisco']['url']
class SimulatedSupportApi:
    '''Simulated version of Cisco Support API. This simulation
    ignores OAuth2 credential required by the real API.
    View simulated API at: https://github.com/CC-Digital-Innovation/NetCloud-FastAPI
    '''
    def get_coverage_summary_by_sn(self, serial_numbers):
        url = URL + '/sn2info/v2/coverage/summary/serial_numbers/'
        sn_path_params = ','.join(serial_numbers)
        response = requests.get(url + sn_path_params)
        response.raise_for_status()
        payload = response.json()
        summeries = payload['serial_numbers']
        for i in range(2, payload['pagination_response_record']['last_index']):
            params = {'page_index': i}
            response = requests.get(url + sn_path_params, params=params)
            response.raise_for_status()
            payload = response.json()
            summeries.extend(payload['serial_numbers'])
        return summeries
