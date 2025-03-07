import json
import time
from typing import Any, Optional, Union
from urllib.parse import parse_qs, urlparse

import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup
from loguru import logger
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

URL = "https://www.doge.gov/savings"


def get_webdriver(
    browser: str,
    debug: bool = False,
    nojs: bool = False,
) -> Union[webdriver.Chrome, webdriver.Firefox]:
    """Initialize a selenium web driver with the specified options."""

    # Google chrome
    if browser == "chrome":
        # Create the options
        options = webdriver.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-gpu")
        if nojs:
            options.add_argument("--disable-javascript")  # Disable JavaScript
        if not debug:
            options.add_argument("--headless")

        service = ChromeService()
        driver = webdriver.Chrome(service=service, options=options)

    # Firefox
    elif browser == "firefox":
        # Create the options
        options = webdriver.FirefoxOptions()
        if nojs:
            options.set_preference("javascript.enabled", False)  # Disable JavaScript
        if not debug:
            options.add_argument("--headless")

        service = FirefoxService()
        driver = webdriver.Firefox(service=service, options=options)
    else:
        raise ValueError("Unknown browser type, should be 'chrome' or 'firefox'")

    return driver


def parse_popup(soup: BeautifulSoup) -> dict[str, Any]:
    """Parse the popup you get when clicking on table row."""

    out = {}

    # Name of the business name
    out["business_name"] = soup.select_one("div.fixed h3").text

    # Structure of pop up differs, some only have total contract and description
    ptags = soup.select("div.fixed p")
    if len(ptags) >= 6:
        out["claimed_savings"] = float(ptags[-5].text.replace("$", "").replace(",", ""))
        out["total_contract"] = float(ptags[-3].text.replace("$", "").replace(",", ""))
        out["description"] = ptags[-1].text
    else:
        out["total_contract"] = float(ptags[-2].text.replace("$", "").replace(",", ""))
        out["description"] = ptags[-1].text
        out["claimed_savings"] = np.nan

    return out


def get_query_params(url):

    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)

    return {
        key: value[0] if len(value) == 1 else value
        for key, value in query_params.items()
    }


def get_usasavings_data(piid):
    """Given a PIID, get the award data from the USA Spending API."""

    # Headers for the search POST
    search_headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "Content-Length": "600",
        "Content-Type": "application/json",
        "Origin": "https://www.usaspending.gov",
        "Priority": "u=3, i",
        "Referer": "https://www.usaspending.gov/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
        "X-Requested-With": "USASpendingFrontend",
    }

    # API endpoint for the SEARCH
    SEARCH_API = "https://api.usaspending.gov/api/v2/search/spending_by_award/"

    # Try multiple award code groups
    award_codes = dict(
        contracts=[
            "A",
            "B",
            "C",
            "D",
        ],
        idvs=[
            "IDV_A",
            "IDV_B",
            "IDV_B_A",
            "IDV_B_B",
            "IDV_B_C",
            "IDV_C",
            "IDV_D",
            "IDV_E",
        ],
    )

    # Try each
    result = None
    for award_code_group in award_codes.values():

        # Make the POST data
        data = json.dumps(
            {
                "filters": {
                    "time_period": [
                        {"start_date": "2007-10-01", "end_date": "2025-09-30"}
                    ],
                    "award_type_codes": award_code_group,
                    "award_ids": [piid],
                },
                "fields": [
                    "Award ID",
                ],
                "limit": 1,
            }
        )

        # Do the search POST
        resp = requests.post(SEARCH_API, headers=search_headers, data=data)
        if resp.status_code != 200:
            raise ValueError(f"Bad status code on search POST {resp.status_code}")

        r = resp.json()
        if len(r["results"]) == 1:
            result = r["results"][0]
            break

    if result is None:
        raise ValueError(f"Couldn't find the award {piid} in the search API")

    # Get the internal ID
    return result["generated_internal_id"]


class WebScraper:
    """Object for scraping the DOGE savings website."""

    def __init__(
        self,
        debug: bool = False,
        browser: str = "firefox",
    ) -> None:

        # Save attributes
        self.browser = browser
        self.debug = debug

        # Initialize the webdriver
        self.init()

    def init(self) -> None:
        """
        Initialize the webdriver.

        This will reset the `driver` attribute.
        """
        # Get the driver
        self.driver = get_webdriver(browser=self.browser, debug=self.debug)

    def cleanup(self) -> None:
        """Clean up the web driver."""
        # Close and delete the driver
        self.driver.close()
        del self.driver

        # Log it
        logger.info("Retrying...")

    def scrape_data(
        self, log_freq: int = 100, max_results: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Scrape the data.

        Parameters
        ----------
        log_freq :
            How often to log messages
        """

        # Navigate to the page
        self.driver.get(URL)

        # Click the "View all contracts" button
        all_buttons = self.driver.find_elements(By.CSS_SELECTOR, "button")
        matches = list(filter(lambda x: x.text == "View All Contracts", all_buttons))
        if len(matches) != 1:
            raise ValueError("Could not find 'View All Contracts' button")
        matches[0].click()

        # Initialize the soup object
        soup = BeautifulSoup(self.driver.page_source, "html.parser")
        table = soup.select("table")[0]

        data = []
        for i, tr in enumerate(table.select("tr")[1:]):  # Skip header row

            # Break if we have enough data (this is for testing purposes)
            if max_results is not None and len(data) >= max_results:
                break

            tds = tr.select("td")
            d = {}  # Store parsed info

            # The agency
            d["agency"] = tds[0].text
            if d["agency"] != "CONSUMER FINANCIAL PROTECTION BUREAU":
                continue

            # Log
            if len(data) % log_freq == 0:
                logger.info(f"Scraping data row #{len(data)+1}")

            # Get the url
            a = tds[3].select_one("a")
            if a:
                d["url"] = a["href"]
            else:
                d["url"] = None

            # Parse the URL and add the query params
            if d["url"]:
                d.update(get_query_params(d["url"]))

            # Find the row in the table that we want to click
            table = self.driver.find_element(By.CSS_SELECTOR, "table")
            button = table.find_elements(By.CSS_SELECTOR, "tr")[i + 1]

            # Scroll the row into view
            self.driver.execute_script(
                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                button,
            )

            # Wait for the scroll to happen
            time.sleep(1)

            # Wait again to ensure we can click
            self.driver.implicitly_wait(10)
            ActionChains(self.driver).move_to_element(button).click(button).perform()

            # Wait for the popup to load
            try:
                wait = WebDriverWait(self.driver, 5)
                wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.fixed h3"))
                )
            except Exception:
                print(f"Issue for row: {i}")
                data.append({})
                continue

            # Parse popup info and save it
            extra_info = parse_popup(
                BeautifulSoup(self.driver.page_source, "html.parser")
            )
            d.update(extra_info)

            # Close the popup by clicking the "Close" button
            button = self.driver.find_element(
                By.CSS_SELECTOR, "div.fixed button:nth-child(2)"
            )
            button.click()

            # Save the data
            data.append(d)

        # Log it
        logger.debug(f"Done scraping {len(data)} rows")

        # Convert to a dataframe
        data = pd.DataFrame(data)

        # Getting USA savings URLs
        logger.info("Getting USA savings URLs")

        internal_ids = []
        for i, piid in enumerate(data["PIID"]):

            if i % log_freq == 0:
                logger.info(f"Getting USA Savings ID for row #{i+1}")

            internal_id = None
            try:
                internal_id = get_usasavings_data(piid)
            except Exception:
                logger.warning(f"Couldn't get internal ID for PIID {piid}")
                pass
            internal_ids.append(internal_id)

        # Save this
        data["internal_id"] = internal_ids
        data["usa_savings_url"] = (
            "https://www.usaspending.gov/award/" + data["internal_id"]
        )

        return data
