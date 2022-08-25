import re

from loguru import logger

import check_outage
from meraki.exceptions import ObjectNotFound

MERAKI_RE = re.compile('meraki', re.I)

def check(site, alert_id, action_name,
            prtg_api, opsgenie_api, meraki_api, 
            snow_api, snow_filter):
    # payload to post for alert extra properties
    details = {"SiteName": site['name']}

    # get gis outage status
    gis_response = check_outage.get_site_status(site)
    if gis_response:
        if "PowerStatus" in gis_response:
            if gis_response["PowerStatus"] == "Active":
                details["Power_ProviderStatus"] = "Up"
            elif gis_response["PowerStatus"] == "Inactive":
                # prefix keys
                prefixed = {}
                for key, val in gis_response.items():
                    prefixed["Power_" + key] = val
                details.update(prefixed)
                del details["Power_PowerStatus"]
                details["Power_ProviderStatus"] = "Down"
            else:
                logger.error("PowerStatus '" + gis_response["PowerStatus"] + "' is not a valid response.")
                details["Power_ProviderStatus"] = ""
        else:
            logger.error("Cannot parse outage status.")
            details["Power_ProviderStatus"] = ""
    else:
        logger.error("Unable to retrieve outage status.")
        details["Power_ProviderStatus"] = ""

    # get pi status
    pi_response = prtg_api.get_sensors_by_name('Ping', 'PI - LTE', site['name'])
    pi_is_up = None
    if "sensors" in pi_response:
        if len(pi_response["sensors"]) == 1:
            if "status" in pi_response["sensors"][0]:
                details["PRTG_PiStatus"] = pi_response["sensors"][0]["status"]
                if re.match("Up|Unusual|Warning",  details["PRTG_PiStatus"]):
                    pi_is_up = True
                elif re.match("Down.*", details["PRTG_PiStatus"]):
                    pi_is_up = False
                # else pi is Paused|Unknown
            else:
                logger.error("Could not parse pi sensor status.")
                details["PRTG_PiStatus"] = ''
        elif len(pi_response["sensors"]) > 1:
            logger.error("More than one pi sensor was found.")
            details["PRTG_PiStatus"] = ''
        else:
            logger.error("Could not find pi sensor.")
            details["PRTG_PiStatus"] = ''
    else:
        logger.error("Cannot parse pi sensors in payload.")
        details["PRTG_PiStatus"] = ''

    # get probe status
    probe_response = prtg_api.get_sensors_by_name('Probe Health', site['name'], 'Probe Device')
    probe_is_up = None
    if "sensors" in probe_response:
        if len(probe_response["sensors"]) == 1:
            if "status" in probe_response["sensors"][0]:
                details["PRTG_ProbeStatus"] = probe_response["sensors"][0]["status"]
                if re.match("Up|Unusual|Warning",  details["PRTG_ProbeStatus"]):
                    probe_is_up = True
                elif re.match("Down.*", details["PRTG_ProbeStatus"]):
                    probe_is_up = False
                # else pi is Paused|Unknown
            else:
                logger.error("Could not parse probe device status.")
                details["PRTG_ProbeStatus"] = ''
        elif len(probe_response["sensors"]) > 1:
            logger.error("More than one probe device was found.")
            details["PRTG_ProbeStatus"] = ''
        else:
            logger.error("Could not find probe device.")
            details["PRTG_ProbeStatus"] = ''
    else:
        logger.error("Cannot parse probe devices in payload.")
        details["PRTG_ProbeStatus"] = ''

    # get meraki device and status
    meraki_is_up = None
    cis = snow_api.get_cis_filtered_by(snow_filter)
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
            if meraki_is_up:
                details['Cisco_MerakiStatus'] = 'Up'
            else:
                details['Cisco_MerakiStatus'] = 'Down'
        except ObjectNotFound:
            details['Cisco_MerakiStatus'] = ''

    # Site power output
    if any((meraki_is_up, pi_is_up, probe_is_up)):
        details['Power_SitePower'] = 'Up'
    elif details['Power_ProviderStatus'] == 'Up':
        if all(status is None for status in (meraki_api, pi_is_up, probe_is_up)):
            details['Power_SitePower'] = 'Likely Up'
        else:
            details['Power_SitePower'] = 'Likely Down'
    else:
        details['Power_SitePower'] = 'Down'
        # add tag for site down
        add_tag_status_code = opsgenie_api.add_alert_tags(alert_id, ["SitePowerDown"], note=f"Automated action {action_name} detected site power is down with high confidence. Tag has been added.")
        if add_tag_status_code == 202:
            logger.info(f"Successfully added tags to alert {alert_id}.")
        else:
            logger.error(f"Could not add tags to alert {alert_id}")

    # User input validity check
    details["PowerCheckValidation"] = ""

    # update alert with collected statuses
    note = f"Automated action {action_name} completed. Details of collected statuses have been added as extra properties."

    post_details_status_code = opsgenie_api.add_alert_details(alert_id, details, note=note)
    if post_details_status_code == 202:
        logger.info(f"Successfully posted details to alert {alert_id}.")
    else:
        logger.error(f"Could not post details to alert {alert_id}")

    return details
