import json
from copy import deepcopy
from datetime import datetime

import pytz
import requests
from loguru import logger

from config import config

def convert_epoch_to_datetime(epoch):
    """convert epoch to datetime with config-specified timezone
    
    Parameters
    ----------
    epoch : int
        The timestamp to convert

    Returns
    -------
    datetime
        The converted time with config-specified timezone.
        If it is not specified, timezone defaults to local.
    """

    converted_datetime = datetime.fromtimestamp(epoch, datetime.now().astimezone().tzinfo)
    if config["date-time"]["timezone"]:
        return converted_datetime.astimezone(pytz.timezone(config["date-time"]["timezone"]))
    return converted_datetime

def get_gis_power_status(site):
    """checks the power status of a site using CalOES's Power Outage Incident API.
    (more at: https://gis.data.ca.gov/datasets/CalEMA::power-outage-incidents/about)

    Parameters
    ----------
    site : SiteData

    Returns
    -------
    dict
        A dictionary with outage status and outage information if it is active or
        simply site information if it is restored

    None
        If missing keys, missing key values, or incorrect longitude and latitude values.
    """

    # check argument
    try:
        if not site["longitude"]:
            logger.error("Missing longitude value")
            return None
        if not site["latitude"]:
            logger.error("Missing latitude value")
            return None
    except KeyError as err:
        logger.exception("Argument is missing required key: " + err.args[0])
        return None
        
    url = "https://services.arcgis.com/BLN4oKB0N1YSgvY8/arcgis/rest/services/Power_Outages_(View)/FeatureServer/0/query"
    headers = deepcopy(config["gis-api"]["headers"])
    params = deepcopy(config["gis-api"]["params"])

    params["geometry"] = str(site["longitude"]) + "," + str(site["latitude"])
    params["inSR"] = "4326"
    params["geometryType"] = "esriGeometryPoint"

    response = requests.get(url, headers=headers, params=params)

    response_content = json.loads(response.content)

    # get list of outages
    try:
        statuses = response_content['features']
    except KeyError:
        logger.error(response_content)
        return None

    if not statuses:
        return {"PowerStatus": "Active"}
    elif len(statuses) > 1:
        logger.info("More than one outage found.")
        for outage in statuses:
            logger.info(json.dumps(outage, indent=4, sort_keys=True))

    site_status = statuses[0]["attributes"]
    
    # convert epoch to formatted datetime
    if "StartDate" in site_status:
        if site_status["StartDate"]:
            site_status["StartDate"] = convert_epoch_to_datetime(site_status["StartDate"]//(10**3)).strftime(config["date-time"]["timeFormat"])
    if "EstimatedRestoreDate" in site_status:
        if site_status["EstimatedRestoreDate"]:
            site_status["EstimatedRestoreDate"] = convert_epoch_to_datetime(site_status["EstimatedRestoreDate"]//(10**3)).strftime(config["date-time"]["timeFormat"])

    del site_status["OutageStatus"]
    site_status["PowerStatus"] = "Inactive"
    return site_status
        

def get_pge_power_status(site):
    """checks the power status of a site using PG&E's API

    Parameters
    ----------
    site : SiteData

    Returns
    -------
    dict
        A dictionary with outage status and outage information if it is active or
        simply site information if it is restored

    None
        If missing keys, missing key values, or incorrect longitude and latitude values.
    """

    # check argument
    try:
        if not site["city"]:
            logger.error("Missing region value.")
            return None
        if not site["longitude"]:
            logger.error("Missing longitude value.")
            return None
        if not site["latitude"]:
            logger.error("Missing latitude value.")
            return None
    except KeyError as err:
        logger.exception("Argument is missing required key: " + err.args[0])
        return None

    url = "https://apim.cloud.pge.com/cocoutage/outages/getOutagesRegions"
    headers = deepcopy(config["pge-api"]["headers"])
    params = deepcopy(config["pge-api"]["params"])

    response = requests.get(url, headers=headers, params=params)

    response_content = json.loads(response.content)

    # get list of outages based on region
    outage_regions = response_content['outagesRegions']

    for outage_region in outage_regions:
        # parse for matching region
        if site['city'] == outage_region['regionName']:
            for outage in outage_region['outages']:
                # parse for matching longitude and latitude
                # note that PG&E uses (longitude, latitude) vs. Google Map's (latitude, longitude)
                if site['longitude'] == outage['longitude'] and site['latitude'] == outage['latitude']:
                    # convert epoch to formatted datetime
                    if "autoEtor" in outage:
                        if outage["autoEtor"]:
                            outage["autoEtor"] = convert_epoch_to_datetime(int(outage["autoEtor"])).strftime(config["date-time"]["timeFormat"])
                    if "crewEta" in outage:
                        if outage["crewEta"]:
                            outage["crewEta"] = convert_epoch_to_datetime(int(outage["crewEta"])).strftime(config["date-time"]["timeFormat"])
                    if "currentEtor" in outage:
                        if outage["currentEtor"]:
                            outage["currentEtor"] = convert_epoch_to_datetime(int(outage["currentEtor"])).strftime(config["date-time"]["timeFormat"])
                    if "lastUpdateTime" in outage:
                        if outage["lastUpdateTime"]:
                            outage["lastUpdateTime"] = convert_epoch_to_datetime(int(outage["lastUpdateTime"])).strftime(config["date-time"]["timeFormat"])
                    if "outageStartTime" in outage:
                        if outage["outageStartTime"]:
                            outage["outageStartTime"] = convert_epoch_to_datetime(int(outage["outageStartTime"])).strftime(config["date-time"]["timeFormat"])
                    del outage["outageStatus"]
                    outage["PowerStatus"] = "Inactive"
                    return outage
    return {"PowerStatus": "Active"}


#TODO functions for other APIs, get list of specific power providers

#function to redirect which function API to call
def get_site_status(site, provider=None):
    address = ", ".join((site["street"], site["city"], site["state"]))
    payload = {
        "SiteName": site["name"],
        "Address": address,
        "Longitude": site["longitude"],
        "Latitude": site["latitude"]
    }
    if provider:
        if provider.lower() == "pge":
            logger.info("PGE API USED")
            payload.update(get_pge_power_status(site))
            payload["Time"] = datetime.now(pytz.timezone(config["date-time"]["timezone"])).strftime(config["date-time"]["timeFormat"])
            logger.info(json.dumps(payload, indent=4, sort_keys=True))
            return payload
        if provider.lower() == "gis":
            logger.info("GIS API USED")
            payload.update(get_gis_power_status(site))
            payload["Time"] = datetime.now(pytz.timezone(config["date-time"]["timezone"])).strftime(config["date-time"]["timeFormat"])
            logger.info(json.dumps(payload, indent=4, sort_keys=True))
            return payload
    else:
        logger.info("GIS API USED")
        payload.update(get_gis_power_status(site))
        payload["Time"] = datetime.now(pytz.timezone(config["date-time"]["timezone"])).strftime(config["date-time"]["timeFormat"])
        logger.info(json.dumps(payload, indent=4, sort_keys=True))
        return payload
