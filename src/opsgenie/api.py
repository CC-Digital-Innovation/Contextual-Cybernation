import opsgenie_sdk

class OpsgenieApi:
    def __init__(self, api_key):
        conf = opsgenie_sdk.Configuration()
        conf.api_key['Authorization'] = api_key
        api_client = opsgenie_sdk.ApiClient(configuration=conf)
        self.alert_api = opsgenie_sdk.AlertApi(api_client=api_client)

    def add_alert_details(self, id, details, user=None, source=None, note=None):
        # aka extra properties and custom properties
        body = opsgenie_sdk.AddDetailsToAlertPayload(user, note, source, details)
        response = self.alert_api.add_details(id, body)
        return response

    def add_alert_tags(self, id, tags, user=None, source=None, note=None):
        body = opsgenie_sdk.AddTagsToAlertPayload(user, note, source, tags)
        response = self.alert_api.add_tags(id, body)
        return response

    def close_alert(self, id, user=None, source=None, note=None):
        body = opsgenie_sdk.CloseAlertPayload(user, note, source)
        response = self.alert_api.close_alert(id, close_alert_payload=body)
        return response
