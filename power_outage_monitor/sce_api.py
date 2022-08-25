import json

from loguru import logger
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config import config

def get_power_outage_sce(address):
    """Scrape outages from https://www.sce.com/outage-center/addresslookup

    Parameters
    ----------
    address : str
        The address to lookup

    Returns
    -------
    payload : dict
        Address searched and outage details

    None
        If address could not be found
    """

    # Using FireFox
    # firefox_options = webdriver.FirefoxOptions()
    # firefox_options.add_argument("--headless")
    # driver = webdriver.Firefox(options=firefox_options)

    # Using Chromium
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless")
    driver = webdriver.Chrome(options=chrome_options)

    url = "https://www.sce.com/outage-center/addresslookup"
    driver.get(url)
    
    max_wait_time = config["sce-api"]["maxWaitTime"]

    try:
        # Find address input element, input address, and press ENTER key
        search_input = WebDriverWait(driver, max_wait_time).until(
                EC.visibility_of_element_located((By.XPATH, "//*[@id='search']/div/div[1]/form/input")))
        search_input.send_keys(address)
        search_input.send_keys(Keys.RETURN)

        # Check address
        address_element = WebDriverWait(driver, max_wait_time).until(
            EC.visibility_of_element_located((By.ID, "address-searched")))
        if not address_element.text:
            logger.error("Could not find address")
            return None

        # initialize return payload
        payload = {}    
        payload["address"] = address_element.text

        # Find total number of outages
        outages_city_count_element = WebDriverWait(driver, max_wait_time).until(
            EC.visibility_of_element_located((By.XPATH, "//*[@id='heading-accordion-39357-1']/div/h3/button/span[2]")))
        payload["outagesInCity"] = int(outages_city_count_element.text[1:2])
        if payload["outagesInCity"] == 0:
            return payload
        
        # initialize outage list
        payload["outages"] = []

        # open drop-down list
        WebDriverWait(driver, max_wait_time).until(
                EC.visibility_of_element_located((By.XPATH, "//*[@id='heading-accordion-39357-1']/div/h3/button"))).click()

        # Find and fill outage details
        for i in range(0, payload["outagesInCity"]):
            payload["outages"].append({})
            payload["outages"][i]["outageType"] = WebDriverWait(driver, max_wait_time).until(
                EC.visibility_of_element_located((By.XPATH, "//*[@id='city-outages']/div[" + str(i + 1) + "]/div[1]/span"))).text
            payload["outages"][i]["lastUpdated"] = WebDriverWait(driver, max_wait_time).until(
                EC.visibility_of_element_located((By.XPATH, "//*[@id='city-outages']/div[" + str(i + 1) + "]/div[1]/div"))).text[len("Last Updated: "):]
            payload["outages"][i]["estimatedRestoreTime"] = WebDriverWait(driver, max_wait_time).until(
                EC.visibility_of_element_located((By.XPATH, "//*[@id='city-outages']/div[" + str(i + 1) + "]/div[2]"))).text[len("Estimated Time of Restoration: "):]
            payload["outages"][i]["reason"] = WebDriverWait(driver, max_wait_time).until(
                EC.visibility_of_element_located((By.XPATH, "//*[@id='city-outages']/div[" + str(i + 1) + "]/div[4]/div[1]"))).text[len("Reason: "):]
            payload["outages"][i]["outageNumber"] = WebDriverWait(driver, max_wait_time).until(
                EC.visibility_of_element_located((By.XPATH, "//*[@id='city-outages']/div[" + str(i + 1) + "]/div[5]/div[2]"))).text[len("Outage #:"):]
            statuses = WebDriverWait(driver, max_wait_time).until(
                EC.visibility_of_element_located((By.XPATH, "//*[@id='city-outages']/div[" + str(i + 1) + "]/div[3]"))).text
            payload["outages"][i]["outageStatus"] = find_step_in_progress(statuses)
        return payload
    finally:
        # close browser
        driver.quit()

def find_step_in_progress(status_str):
    """Parse all statuses for step that is in progress

    Parameters
    ----------
    status_str : str
        Newline separated str of the steps and statuses

    Returns
    -------
    str
        Current step in progress
    """

    status_list = status_str.splitlines()
    # remove "Status:" string
    status_list.pop(0)
    for i in range(1, len(status_list), 2):
        if status_list[i] == "In Progress":
            return status_list[i-1][len("Step #:"):]

def main():
    # Test
    logger.info(json.dumps(get_power_outage_sce("San Dieguito Heritage Museum, 450 Quail Gardens Dr, Encinitas, CA"), indent=4, sort_keys=True))

if __name__ == "__main__":
    main()