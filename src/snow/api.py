import pysnow
import requests

class SnowApi:
    def __init__(self, instance, username, password, limit=10000, offset=0, display_value=False):
        self.client = pysnow.Client(instance=instance, user=username, password=password)
        self.client.parameters.limit = limit
        self.client.parameters.offset = offset
        self.client.parameters.display_value = display_value
        self.instance = instance
        self.username = username
        self.password = password

    def get_site_by_name(self, name):
        location_table = self.client.resource(api_path='/table/cmn_location')
        return location_table.get(query={'name': name}).one()

    def get_cis_filtered_by(self, filters):
        ci_table = self.client.resource(api_path='/table/cmdb_ci')

        copy_filters = filters.copy()
        try:
            first_k, first_v = copy_filters.popitem()
        except KeyError:
            return ci_table.get().all()
        # first query
        query = pysnow.QueryBuilder().field(first_k)
        if first_v[0]:
            query.equals(first_v[0])
        else:
            query.is_empty()
        for i in range(1, len(first_v)):
            query.OR().field(first_k)
            if first_v[i]:
                query.equals(first_v[i])
            else:
                query.is_empty()
        # subsequent queries appended by AND()
        for k, v in copy_filters.items():
            query.AND().field(k)
            if v[0]:
                query.equals(v[0])
            else:
                query.is_empty()
            for i in range(1, len(v)):
                query.OR().field(k)
                if v[i]:
                    query.equals(v[i])
                else:
                    query.is_empty()
        response = ci_table.get(query=query)
        return response.all()

    def set_long_lat(self, sys_id, long, lat):
        update = {
            'longitude': long,
            'latitude': lat
        }
        ci_table = self.client.resource(api_path='/table/cmn_location')
        location = ci_table.update(query={'sys_id': sys_id}, payload=update)
        return location

    def create_incident(self, customer, caller, opened_by, message, description, impact, location, ci=''):
        incident_table = self.client.resource(api_path='/table/incident')
        new_incident = {
            'company': customer,
            'u_customer': customer,
            'caller_id': caller,
            'opened_by': opened_by,
            'short_description': message,
            'description': description,
            'impact': impact,
            'urgency': impact,
            'severity': impact,
            'location': location,
            'cmdb_ci': ci
        }
        response = incident_table.create(payload=new_incident)
        return response.one()

    def set_field(self, sys_id, name, value):
        update = {name: value}
        ci_table = self.client.resource(api_path='/table/cmdb_ci')
        response = ci_table.update(query={'sys_id': sys_id}, payload=update)
        return response[name] == value

    def get_record(self, link):
        response = requests.get(link, auth=(self.username, self.password))
        response.raise_for_status()
        return response.json()['result']

    def get_incident_link(self, sys_id):
        return f'https://{self.instance}.service-now.com/incident?sys_id={sys_id}'
