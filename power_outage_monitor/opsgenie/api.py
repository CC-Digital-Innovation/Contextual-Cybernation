import requests
from loguru import logger

class OpsgenieApi:
    def __init__(self, key, id_type = 'id'):
        self.auth = {
            'Authorization': f'GenieKey {key}'
        }
        if id_type != 'id' and id_type != 'tiny' and id_type != 'alias':
            raise ValueError(f'Unrecognized identifier type: "{id_type}". Use one of "id | tiny | alias".')
        self.params = {
            'identifierType': id_type
        }

    def add_alert_details(self, id, details, user=None, source=None, note=None):
        url = 'https://api.opsgenie.com/v2/alerts/' + id + '/details'
        payload = {
            'details': details,
            'user': user,
            'source': source,
            'note': note
        }

        logger.info('POSTing alert api to update details')
        request = requests.post(url, json=payload, headers=self.auth, params=self.params)

        request.raise_for_status()

    def add_alert_tags(self, id, tags, user=None, source=None, note=None):
        url = 'https://api.opsgenie.com/v2/alerts/' + id + '/tags'
        payload = {
            'tags': tags,
            'user': user,
            'source': source,
            'note': note
        }

        logger.info('POSTing alert api to add tags')
        request = requests.post(url, json=payload, headers=self.auth, params=self.params)

        request.raise_for_status()

    def close_alert(self, id, user=None, source=None, note=None):
        url = 'https://api.opsgenie.com/v2/alerts/' + id + '/close'
        payload = {
            'user': user,
            'source': source,
            'note': note
        }

        logger.info('POSTing alert api to close alert')
        request = requests.post(url, json=payload, headers=self.auth, params=self.params)

        request.raise_for_status()
