import json
from copy import deepcopy

import requests
from loguru import logger

from config import config

class NoCandidateFound(Exception):
    pass

class LowScore(Exception):
    pass

def get_long_lat(address):
    """Uses ArcGIS's REST API 'findAddressCandidates' to find the longitude and latitude of a given address.
    If API returns multiple results, return the most accurate and acceptable, i.e. above minScore, address.
    (more at: https://developers.arcgis.com/rest/geocode/api-reference/geocoding-find-address-candidates.htm)
    
    Parameters
    ----------
    address : str
        The address to search.

    Returns
    -------
    2-tuple
        (longitude, latitude).

    None
        if address could not be found or score is below acceptable.
    """

    url = "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates"
    headers = deepcopy(config["geocode"]["headers"])
    params = deepcopy(config["geocode"]["params"])

    params["SingleLine"] = address

    response = requests.get(url, headers=headers, params=params)

    jsonResponse = json.loads(response.content)

    if len(jsonResponse["candidates"]) > 1:
        if jsonResponse["candidates"][0]["score"] >= config["geocode"]["minScore"]:
            logger.debug("Address found: " + jsonResponse["candidates"][0]["address"] + " | Score: " + str(jsonResponse["candidates"][0]["score"]))
            point = jsonResponse["candidates"][0]["location"]
            return point["x"], point["y"]
        raise LowScore(f'Cadidate score {jsonResponse["candidates"][0]["score"]} below minimum score {config["geocode"]["minScore"]}. Address may not be specific enough.')
    elif len(jsonResponse["candidates"]) == 0:
        raise NoCandidateFound(f'No results found for address {address}.')
    else:
        logger.debug("Address found: " + jsonResponse["candidates"][0]["address"] + " | Score: " + str(jsonResponse["candidates"][0]["score"]))
        point = jsonResponse["candidates"][0]["location"]
        return point["x"], point["y"]
