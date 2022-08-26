import secrets

from fastapi import Depends, FastAPI, HTTPException, Security, status, Query
from fastapi.security import APIKeyHeader
from loguru import logger
from prtg import PrtgApi

import check_all
import geocode
from config import config
from meraki_api import MerakiOrgApi
from opsgenie import OpsgenieApi, OpsgenieRequest
from pysnow.exceptions import NoResults
from snow import SnowApi

TOKEN = config['web']['token']
PRTG_API = PrtgApi(config['prtg']['url'], config['prtg']['username'], config['prtg']['password'], is_passhash=config['prtg'].get('is_passhash', False))
OPSGENIE_API = OpsgenieApi(config['opsgenie']['api_key'])
SNOW_API = SnowApi(config['snow']['instance'], config['snow']['username'], config['snow']['password'])
SNOW_FILTER = config['snow']['filter']
MERAKI_API = MerakiOrgApi(api_key=config['meraki']['api_key'], org_id=config['meraki'].get('org_id', None), org_name=config['meraki'].get('org_name', None))

app = FastAPI()

api_key = APIKeyHeader(name='X-API-Key')

def authorize(key: str = Security(api_key)):
    if not secrets.compare_digest(key, TOKEN):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid token')

@app.get('/checkSite', dependencies=[Depends(authorize)])
def check_site(site_name: str):
    try:
        site = SNOW_API.get_site_by_name(site_name)
    except NoResults:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'Could not find site {site_name}')
    if not site['longitude'] or not site['latitude']:
        address = ', '.join((site['street'], site['city'], site['state']))
        address = ' '.join((address, site['zip']))
        logger.info(f'Location is missing long/lat values. Geocoding address: {address}')
        long, lat = geocode.get_long_lat(address)
        site = SNOW_API.set_long_lat(site['sys_id'], long, lat)
    logger.info('Found site "' + site_name + '". Getting power status...')
    return check_all.check(site, PRTG_API, MERAKI_API, SNOW_API, SNOW_FILTER)

@app.post('/webhook/ops', dependencies=[Depends(authorize)])
def webhook_ops(opsgenie_req: OpsgenieRequest, company: str, caller: str, opened_by: str = Query(alias='openedBy')):
    import json
    logger.debug(json.dumps(opsgenie_req.dict(), indent=2, sort_keys=True))
    site_name = opsgenie_req.alert.extra_properties.group
    alert_id = opsgenie_req.alert.id
    create_outage_incident = False
    try:
        try:
            site = SNOW_API.get_site_by_name(site_name)
        except NoResults:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'Could not find site {site_name}')
        if not site['longitude'] or not site['latitude']:
            address = ', '.join((site['street'], site['city'], site['state']))
            address = ' '.join((address, site['zip']))
            logger.info(f'Location is missing long/lat values. Geocoding address: {address}')
            long, lat = geocode.get_long_lat(address)
            site = SNOW_API.set_long_lat(site['sys_id'], long, lat)
        logger.info('Found site ' + site_name + '. Getting power status...')
        details = check_all.check(site, PRTG_API, MERAKI_API, SNOW_API, SNOW_FILTER)

        if details['Power_SitePower'] == 'Down':
            # add tag for site down
            add_tag_status_code = OPSGENIE_API.add_alert_tags(alert_id, ['SitePowerDown'], note=f'Automated action {opsgenie_req.action_name} detected site power is down. Tag has been added.')
            if add_tag_status_code == 202:
                logger.info(f'Successfully added tags to alert {alert_id}.')
            else:
                logger.error(f'Could not add tags to alert {alert_id}')
            # set flag to create incident
            create_outage_incident = True

        # update alert with collected statuses
        note = f'Automated action {opsgenie_req.action_name} completed. Details of collected statuses have been added as extra properties.'

        post_details_status_code = OPSGENIE_API.add_alert_details(alert_id, details, note=note)
        if post_details_status_code == 202:
            logger.info(f'Successfully posted details to alert {alert_id}.')
        else:
            logger.error(f'Could not post details to alert {alert_id}')

        # merge outage details
        extra_str = '\n'.join([': '.join((key,str(val))) for key, val in details.items()])

        opsgenie_req.alert.description = '\n'.join(('Power Check Details', extra_str, '', 'Alert Details', opsgenie_req.alert.description))
    finally:
        impact = int(opsgenie_req.alert.priority[1:]) - 1
        if create_outage_incident:
            # create power outage incident
            SNOW_API.create_incident(company, caller, opened_by,
                    f'[ADARCA] Power outage detected for site {site_name}',
                    opsgenie_req.alert.description,
                    impact)
        else:
            # forward opsgenie alert to snow incident
            SNOW_API.create_incident(company, caller, opened_by,
                    opsgenie_req.alert.message,
                    opsgenie_req.alert.description,
                    impact)

        OPSGENIE_API.close_alert(alert_id, source='python opsgenie-sdk/2.1.5', note='Alert closed by ADARCA.')
