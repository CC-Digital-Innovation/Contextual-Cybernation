import requests

class NetCloudApi:
    def __init__(self, url, cp_id, cp_key, ecm_id, ecm_key):
        self.url = url if url[-1] != '/' else url[:-1]
        self.auth = {
            'X-CP-API-ID': cp_id,
            'X-CP-API-KEY': cp_key,
            'X-ECM-API-ID': ecm_id,
            'X-ECM-API-KEY': ecm_key
        }

    def get_router_status_by_name(self, name):
        '''Returns the status of a given router name in NetCloud.
        '''

        url = self.url + '/api/v2/routers'
        headers = self.auth
        params = {'name': name}

        # Send a request to get the router's status.
        response = requests.get(url, params, headers=headers)
        
        # Check if we were able to find the router in NetCloud.
        response.raise_for_status()
        
        # Return the router's status.
        return response.json()['data'][0]['state'] == 'online'
