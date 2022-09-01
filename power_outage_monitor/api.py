import json
import secrets
import textwrap

import tweepy
from fastapi import Depends, FastAPI, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from loguru import logger
from prtg import PrtgApi

import checks
import geocode
from config import config
# replace SupportApi in production
# from cisco.support import SupportApi
from cisco.support import SimulatedSupportApi
from cisco.meraki_api import MerakiOrgApi
from netcloud import NetCloudApi
from opsgenie import OpsgenieApi, OpsgenieRequest
from pysnow.exceptions import NoResults
from snow import SnowApi

TOKEN = config['web']['token']

PRTG_API = PrtgApi(config['prtg']['url'], 
                   config['prtg']['username'], 
                   config['prtg']['password'], 
                   is_passhash=config['prtg'].get('is_passhash', False))

OPSGENIE_API = OpsgenieApi(config['opsgenie']['api_key'])
OPS_TO_SNOW_SEVERITY = {
    5: 3,
    4: 3,
    3: 2,
    2: 1,
    1: 0,
    0: 0
}

SNOW_API = SnowApi(config['snow']['instance'], 
                   config['snow']['username'], 
                   config['snow']['password'])
SNOW_COMPANY = config['snow']['company']
SNOW_CALLER = config['snow']['caller']
SNOW_OPENED_BY = config['snow']['opened_by']

MERAKI_API = MerakiOrgApi(api_key=config['meraki']['api_key'], 
                          org_id=config['meraki'].get('org_id', None), 
                          org_name=config['meraki'].get('org_name', None))

NETCLOUD_API = NetCloudApi(config['netcloud']['url'], 
                           config['netcloud']['cp_id'], 
                           config['netcloud']['cp_key'], 
                           config['netcloud']['ecm_id'], 
                           config['netcloud']['ecm_key'])

TWITTER_CLIENT = tweepy.Client(consumer_key=config['twitter']['conskey'],
                               consumer_secret=config['twitter']['conssec'],
                               access_token=config['twitter']['acctoken'],
                               access_token_secret=config['twitter']['tokensec'])
# replace SupportApi in production
SIM_CISCO_SUPPORT_API = SimulatedSupportApi()

app = FastAPI()

api_key = APIKeyHeader(name='X-API-Key')

def authorize(key: str = Security(api_key)):
    if not secrets.compare_digest(key, TOKEN):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid token')

def _check_site_outage(site_name):
    try:
        logger.info('Gathering site details...')
        site = SNOW_API.get_site_by_name(site_name)
    except NoResults as e:
        logger.error(str(e))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'Could not find site {site_name}')
    if not site['longitude'] or not site['latitude']:
        address = ', '.join((site['street'], site['city'], site['state']))
        address = ' '.join((address, site['zip']))
        logger.info(f'Location is missing long/lat values. Geocoding address: {address}')
        try:
            long, lat = geocode.get_long_lat(address)
        except (geocode.NoCandidateFound, geocode.LowScore) as e:
            logger.error(str(e))
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        logger.info('Updating record on SNOW CMDB...')
        site = SNOW_API.set_long_lat(site['sys_id'], long, lat)
    logger.info('Found site ' + site_name + '. Getting power status...')
    return checks.check_outage(site, PRTG_API, MERAKI_API, SNOW_API, NETCLOUD_API, SIM_CISCO_SUPPORT_API)

def _check_warranty(name, site_name):
    filter = {'name': name, 'location':site_name}
    try:
        ci = SNOW_API.get_cis_filtered_by(filter)[0]
    except IndexError as e:
        logger.error(str(e))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    logger.info(f'Found configuration item for {name} at {site_name}.')
    return checks.check_warranty(ci, SIM_CISCO_SUPPORT_API, SNOW_API)

@app.get('/checkSiteOutage', dependencies=[Depends(authorize)])
def check_site_outage(site_name: str):
    return _check_site_outage(site_name)

@app.get('/checkWarranty', dependencies=[Depends(authorize)])
def check_warranty(name: str, site_name: str):
    return _check_warranty(name, site_name)

@app.post('/webhook/ops', dependencies=[Depends(authorize)])
def webhook_ops(opsgenie_req: OpsgenieRequest):
    logger.info(f'Alert "{opsgenie_req.alert.message}" triggered ADARCA.')
    logger.debug(json.dumps(opsgenie_req.dict(), indent=2, sort_keys=True))
    site_name = opsgenie_req.alert.extra_properties.group
    device = opsgenie_req.alert.extra_properties.device
    alert_id = opsgenie_req.alert.id
    create_outage_incident = False
    try:
        logger.info(f'Beginning data collection for site {site_name}.')
        # check warranty
        warranty_details = _check_warranty(device, site_name)
        if warranty_details:
            logger.info('Creating expired warranty incident...')
            # create warranty incident
            incident = SNOW_API.create_incident(SNOW_COMPANY, SNOW_CALLER, SNOW_OPENED_BY,
                    f'[ADARCA] Warranty of configuration item {device} is expired.',
                    warranty_details,
                    3,
                    site_name,
                    ci=device)
        logger.info(f'Expired warranty incident created here: {SNOW_API.get_incident_link(incident["sys_id"])}.')

        # check power outage
        details = _check_site_outage(site_name)
        # User input validity check
        details['PowerCheckValidation'] = ''
        if details['Power_SitePower'] == 'Down':
            # add tag for site down
            logger.info('Adding outage tag to alert...')
            add_tag_status_code = OPSGENIE_API.add_alert_tags(alert_id, ['SitePowerDown'], note=f'Automated action {opsgenie_req.action_name} detected site power is down. Tag has been added.')
            if add_tag_status_code == 202:
                logger.info(f'Successfully added tag to alert {alert_id}.')
            else:
                logger.error(f'Could not add tag to alert {alert_id}')
            # merge outage details
            extra_str = '\n'.join([': '.join((key,str(val))) for key, val in details.items()])
            opsgenie_req.alert.description = '\n'.join(('Power Check Details', extra_str, '', 'Alert Details', opsgenie_req.alert.description))
            # set flag to create incident
            create_outage_incident = True

        # update alert with collected statuses
        note = f'Automated action {opsgenie_req.action_name} completed. Details of collected statuses have been added as extra properties.'
        logger.info('Adding collected status details to alert...')
        post_details_status_code = OPSGENIE_API.add_alert_details(alert_id, details, note=note)
        if post_details_status_code == 202:
            logger.info(f'Successfully posted details to alert {alert_id}.')
        else:
            logger.error(f'Could not post details to alert {alert_id}')
    finally:
        ops_impact = int(opsgenie_req.alert.priority[1:]) - 1
        impact = OPS_TO_SNOW_SEVERITY[ops_impact]
        logger.info('Forwarding alert to ITSM...')
        if create_outage_incident:
            # create power outage incident
            incident = SNOW_API.create_incident(SNOW_COMPANY, SNOW_CALLER, SNOW_OPENED_BY,
                    f'[ADARCA] Power outage detected for site {site_name}',
                    opsgenie_req.alert.description,
                    impact,
                    site_name)
            # notify power outage to external platform
            logger.info('Tweeting outage details...')
            TWITTER_CLIENT.create_tweet(text=textwrap.dedent(f'''\
                Start Date: {details['Power_StartDate']}
                Type: {details['Power_OutageType']}
                Cause: {details['Power_Cause']}
                Estimated Restore Date: {details['Power_EstimatedRestoreDate']}'''))
        else:
            # forward opsgenie alert to snow incident
            incident = SNOW_API.create_incident(SNOW_COMPANY, SNOW_CALLER, SNOW_OPENED_BY,
                    opsgenie_req.alert.message,
                    opsgenie_req.alert.description,
                    impact,
                    site_name)
        logger.info(f'Incident created at: {SNOW_API.get_incident_link(incident["sys_id"])}.')
        logger.info('Closing alert on Opsgenie...')
        OPSGENIE_API.close_alert(alert_id, source='python opsgenie-sdk/2.1.5', note='Alert closed by ADARCA.')
        logger.info('ADARCA request complete!')
        return 'ADARCA request complete. Incident has been created and this alert will close.'
