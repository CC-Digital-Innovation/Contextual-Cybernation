import json
import re
from datetime import date, datetime, timezone

from loguru import logger
from requests.exceptions import HTTPError

import provider
from cisco.meraki_api.exceptions import ObjectNotFound
from meraki.exceptions import APIError

MERAKI_RE = re.compile('meraki', re.I)

def check_outage(site,
        prtg_api,
        meraki_api,
        snow_api,
        netcloud_api):
    # payload to post for alert extra properties
    details = {'SiteName': site['name']}

    # get gis outage status
    logger.info('Checking gis dataset for outages...')
    gis_response = provider.get_site_status(site)
    logger.debug(json.dumps(gis_response, indent=2, sort_keys=True))
    details['Power_ProviderStatus'] = ''
    if gis_response:
        if 'PowerStatus' in gis_response:
            if gis_response['PowerStatus'] == 'Active':
                logger.info('No outages found near the site!')
                details['Power_ProviderStatus'] = 'Up'
            elif gis_response['PowerStatus'] == 'Inactive':
                logger.info('Outage found near the site. Adding outage details...')
                del gis_response['PowerStatus']
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
    pi_response = prtg_api.get_sensors_by_name('Ping', site['name'], 'PI - LTE')
    pi_is_up = None
    details['PRTG_PiStatus'] = ''
    if len(pi_response) == 1:
        if 'status' in pi_response[0]:
            details['PRTG_PiStatus'] = pi_response[0]['status']
            if re.match('Up|Unusual|Warning',  details['PRTG_PiStatus']):
                logger.info('PI device is up.')
                pi_is_up = True
            elif re.match('Down.*', details['PRTG_PiStatus']):
                logger.info('PI device is down.')
                pi_is_up = False
            # else pi is Paused|Unknown
        else:
            logger.error('Could not parse pi sensor status.')
    elif len(pi_response) > 1:
        logger.error('More than one pi sensor was found.')
    else:
        logger.error('Could not find pi sensor.')

    # get probe status
    logger.info('Checking status of Probe device...')
    probe_response = prtg_api.get_sensors_by_name('Probe Health', site['name'], 'Probe Device')
    probe_is_up = None
    details['PRTG_ProbeStatus'] = ''
    if len(probe_response) == 1:
        if 'status' in probe_response[0]:
            details['PRTG_ProbeStatus'] = probe_response[0]['status']
            if re.match('Up|Unusual|Warning',  details['PRTG_ProbeStatus']):
                logger.info('Probe device is up.')
                probe_is_up = True
            elif re.match('Down.*', details['PRTG_ProbeStatus']):
                logger.info('Probe device is down.')
                probe_is_up = False
            # else pi is Paused|Unknown
        else:
            logger.error('Could not parse probe device status.')
    elif len(probe_response) > 1:
        logger.error('More than one probe device was found.')
    else:
        logger.error('Could not find probe device.')

    # get meraki device and status
    logger.info('Checking status of Meraki device...')
    cis = snow_api.get_cis_filtered_by({'sys_class_name': ['cmdb_ci_wap_network'], 'location.name': [site['name']]})
    meraki_is_up = None
    details['Cisco_MerakiStatus'] = ''
    try:
        ap = next(ci for ci in cis if MERAKI_RE.search(ci['name']))
    except StopIteration:
        logger.error('Cannot find meraki device in CMDB.')
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
            logger.error('Cannot find device in Meraki.')
        except APIError as e:
            logger.error(str(e))
        else:
            if meraki_is_up:
                logger.info('Meraki device is up.')
                details['Cisco_MerakiStatus'] = 'Up'
            else:
                logger.info('Meraki device is down.')
                details['Cisco_MerakiStatus'] = 'Down'

    # get cradlepoint status
    logger.info('Checking status of Cradlepoint device...')
    details['Cradlepoint_RouterStatus'] = ''
    cradle_is_up = None
    try:
        cradle_is_up = netcloud_api.get_router_status_by_name(site['name'])
    except HTTPError as e:
        logger.error(str(e))
    else:
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

def check_warranty(ci, support_api, snow_api):
    logger.info(f'Checking warranty information for configuration item {ci["name"]}.')
    if snow_api.get_record(ci['manufacturer']['link'])['name'] != 'Cisco':
        logger.info('Unsupported manufacturer for checking warranty.')
        return
    serial_number = ci['serial_number']
    if not serial_number:
        logger.warning(f'Configuration item {ci["name"]} is missing serial number.')
        return
    coverage_summary = support_api.get_coverage_summary_by_sn(ci['serial_number'])[0]
    if not coverage_summary['warranty_end_date']:
        logger.warning(f'Cannot retrieve warranty information for configuration item {ci["name"]}.')
        return
    if coverage_summary['warranty_end_date'] != ci['warranty_expiration']:
        logger.info('Warranty dates do not match. Updating ITSM with latest warranty...')
        snow_api.set_field(ci['sys_id'], 'warranty_expiration', coverage_summary['warranty_end_date'])
    expiration_date = date.fromisoformat(coverage_summary['warranty_end_date'])
    today = datetime.now(timezone.utc).date()
    if expiration_date <= today:
        logger.info(f'Discovered warranty is expired for configuration item {ci["name"]}.')
        diff = (today - expiration_date).days
        return f'Warranty expired {diff} day(s) ago on {expiration_date} for {ci["name"]}.'
