import secrets

from fastapi import Depends, FastAPI, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from loguru import logger
from prtg import PrtgApi

import check_all
import geocode
from config import config
from meraki_api import MerakiOrgApi
from opsgenie import OpsgenieApi
from pysnow.exceptions import NoResults
from snow import SnowApi

TOKEN = config["web"]["token"]
try:
    PRTG_API = PrtgApi(config['prtg']['url'], config['prtg']['username'], config['prtg']['password'], is_passhash=config['prtg']['is_passhash'])
except KeyError:
    PRTG_API = PrtgApi(config['prtg']['url'], config['prtg']['username'], config['prtg']['password'])
try:
    OPSGENIE_API = OpsgenieApi(config['opsgenie']['api_key'], config['opsgenie']['identifier_type'])
except KeyError:
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

@app.get("/checkSite", dependencies=[Depends(authorize)])
def check_site(siteName: str, alertId: str, actionName: str):
    try:
        site = SNOW_API.get_site_by_name(siteName)
    except NoResults:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'Could not find site {siteName}')
    if not site['longitude'] or not site['latitude']:
        address = ', '.join((site['street'], site['city'], site['state']))
        address = ' '.join((address, site['zip']))
        logger.info(f'Location is missing long/lat values. Geocoding address: {address}')
        long, lat = geocode.get_long_lat(address)
        site = SNOW_API.set_long_lat(site['sys_id'], long, lat)
    logger.info("Found site '" + siteName + ".' Getting power status...")
    return check_all.check(site, alertId, actionName, PRTG_API, OPSGENIE_API, MERAKI_API, SNOW_API, SNOW_FILTER)
