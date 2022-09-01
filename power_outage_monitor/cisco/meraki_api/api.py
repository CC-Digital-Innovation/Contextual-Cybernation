import meraki

from .exceptions import ObjectNotFound

class MerakiOrgApi:
    def __init__(self, org_name=None, org_id=None, api_key=None):
        self.db = meraki.DashboardAPI(suppress_logging=True) if not api_key else meraki.DashboardAPI(api_key, suppress_logging=True)
        if org_id:
            org = self.db.organizations.getOrganization(org_id)
            try:
                org['id']
            except KeyError:
                raise ObjectNotFound(f'Cannot find organization: {org_id}')
        elif org_name:
            orgs = self.db.organizations.getOrganizations()
            try:
                org = next(o for o in orgs if o['name'] == org_name)
            except StopIteration:
                raise ObjectNotFound(f'Cannot find organization: {org_name}')
        else:
            orgs = self.db.organizations.getOrganizations()
            try:
                org = orgs[0]
            except IndexError:
                raise ObjectNotFound(f'Cannot find organization')
        self.id = org['id']
        self.name = org['name']
        self.url = org['url']

    def get_device_by_name(self, name):
        response = self.db.organizations.getOrganizationDevices(self.id, name=name)
        try:
            return response[0]
        except IndexError:
            raise ObjectNotFound(f"Cannot get device status with name: {name}")

    def get_device_by_mac(self, mac):
        response = self.db.organizations.getOrganizationDevices(self.id, mac=mac)
        try:
            return response[0]
        except IndexError:
            raise ObjectNotFound(f"Cannot get device status with mac: {mac}")

    def get_device_status(self, serial):
        response = self.db.organizations.getOrganizationDevicesStatuses(self.id, serials=serial)
        try:
            if response[0]['status'] == 'offline' or response[0]['status'] == 'dormant':
                return False
            return True
        except IndexError:
            raise ObjectNotFound(f"Cannot get device status with serial: {serial}")
