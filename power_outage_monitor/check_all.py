import json
import re

from loguru import logger

import check_outage
from meraki_api.exceptions import ObjectNotFound

MERAKI_RE = re.compile('meraki', re.I)

def check(site,
        prtg_api,
        meraki_api,
        snow_api,
        snow_filter,
        netcloud_api):
    # payload to post for alert extra properties
    details = {'SiteName': site['name']}

    # get gis outage status
    logger.info('Checking gis dataset for outages...')
    gis_response = check_outage.get_site_status(site)
    logger.debug(json.dumps(gis_response, indent=2, sort_keys=True))
    details['Power_ProviderStatus'] = ''
    if gis_response:
        if 'PowerStatus' in gis_response:
            if gis_response['PowerStatus'] == 'Active':
                logger.info('No outages found near the site!=.')
                details['Power_ProviderStatus'] = 'Up'
            elif gis_response['PowerStatus'] == 'Inactive':
                logger.info('Outage found near the site. Adding outage details...')
                del details['PowerStatus']
                # prefix keys
                prefixed = {'Power_' + k: v for k, v in gis_response.items()}
                details.update(prefixed)
                details['Power_ProviderStatus'] = 'Down'
            else:
                logger.error(f'PowerStatus {gis_response["PowerStatus"]} is not a valid response.')
        else:
            logger.error('Cannot parse outage status.')
    else:
        logger.error('Unable to retrieve outage status.')

    # get pi status
    logger.info('Checking status of PI device...')
    pi_response = prtg_api.get_sensors_by_name('Ping', 'PI - LTE', site['name'])
    pi_is_up = None
    details['PRTG_PiStatus'] = ''
    if 'sensors' in pi_response:
        if len(pi_response['sensors']) == 1:
            if 'status' in pi_response['sensors'][0]:
                details['PRTG_PiStatus'] = pi_response['sensors'][0]['status']
                if re.match('Up|Unusual|Warning',  details['PRTG_PiStatus']):
                    logger.info('PI device is up.')
                    pi_is_up = True
                elif re.match('Down.*', details['PRTG_PiStatus']):
                    logger.info('PI device is down.')
                    pi_is_up = False
                # else pi is Paused|Unknown
            else:
                logger.error('Could not parse pi sensor status.')
        elif len(pi_response['sensors']) > 1:
            logger.error('More than one pi sensor was found.')
        else:
            logger.error('Could not find pi sensor.')
    else:
        logger.error('Cannot parse pi sensors in payload.')

    # get probe status
    logger.info('Checking status of Probe device...')
    probe_response = prtg_api.get_sensors_by_name('Probe Health', site['name'], 'Probe Device')
    probe_is_up = None
    details['PRTG_ProbeStatus'] = ''
    if 'sensors' in probe_response:
        if len(probe_response['sensors']) == 1:
            if 'status' in probe_response['sensors'][0]:
                details['PRTG_ProbeStatus'] = probe_response['sensors'][0]['status']
                if re.match('Up|Unusual|Warning',  details['PRTG_ProbeStatus']):
                    logger.info('Probe device is up.')
                    probe_is_up = True
                elif re.match('Down.*', details['PRTG_ProbeStatus']):
                    logger.info('Probe device is down.')
                    probe_is_up = False
                # else pi is Paused|Unknown
            else:
                logger.error('Could not parse probe device status.')
        elif len(probe_response['sensors']) > 1:
            logger.error('More than one probe device was found.')
        else:
            logger.error('Could not find probe device.')
    else:
        logger.error('Cannot parse probe devices in payload.')

    # get meraki device and status
    logger.info('Checking status of Meraki device...')
    cis = snow_api.get_cis_filtered_by(snow_filter)
    meraki_is_up = None
    try:
        ap = next(ci for ci in cis if MERAKI_RE.search(ci['name']))
    except StopIteration:
        logger.error('Cannot find meraki device')
        details['Cisco_MerakiStatus'] = ''
    else:
        try:
            if not ap['serial_number']:
                try:
                    device = meraki_api.get_device_by_mac(ap['mac_address'])
                except ObjectNotFound:
                    device = meraki_api.get_device_by_name(ap['name'])
                ap['serial_number'] = device['serial']
            meraki_is_up = meraki_api.get_device_status(ap['serial_number'])
        except ObjectNotFound:
            details['Cisco_MerakiStatus'] = ''
        else:
            if meraki_is_up:
                logger.info('Meraki device is up.')
                details['Cisco_MerakiStatus'] = 'Up'
            else:
                logger.info('Meraki device is down.')
                details['Cisco_MerakiStatus'] = 'Down'

    # get cradlepoint status
    logger.info('Checking status of Cradlepoint device...')
    cradle_is_up = netcloud_api.get_router_status_by_name(site)
    if cradle_is_up:
        logger.info('Router is up.')
        details['Cradlepoint_RouterStatus'] = 'Up'
    else:
        logger.info('Router is down.')
        details['Cradlepoint_RouterStatus'] = 'Down'

    # Site power output
    logger.info('Determining if power outage based on collected data...')
    if any((meraki_is_up, pi_is_up, probe_is_up, cradle_is_up)):
        logger.info('At least one sensor/device is up: not a power outage.')
        details['Power_SitePower'] = 'Up'
    elif details['Power_ProviderStatus'] == 'Up':
        if all(status is None for status in (meraki_is_up, pi_is_up, probe_is_up, cradle_is_up)):
            logger.info('Could not retrieve some data but provider suggests no outage.')
            details['Power_SitePower'] = 'Likely Up'
        else:
            logger.info('Could not retrieve some data but overall data suggests an outage.')
            details['Power_SitePower'] = 'Likely Down'
    else:
        logger.info('All sensors/devices are down and power outage detected. It is most likely an outage.')
        details['Power_SitePower'] = 'Down'

    return details
