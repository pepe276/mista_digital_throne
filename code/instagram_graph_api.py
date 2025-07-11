# instagram_graph_api.py
# -*- coding: utf-8 -*-
import os
import logging
import requests
import sys
from dotenv import load_dotenv

# Ensure stdout uses utf-8 encoding
sys.stdout.reconfigure(encoding='utf-8')

logger = logging.getLogger(__name__)

class InstagramGraphAPI:
    """A class to interact with the Instagram Graph API."""

    def __init__(self):
        load_dotenv()
        self.app_id = os.getenv("INSTAGRAM_APP_ID")
        self.app_secret = os.getenv("INSTAGRAM_APP_SECRET")
        self.user_access_token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
        self.base_url = "https://graph.facebook.com/v20.0"

    def _make_request(self, endpoint, params=None):
        """Helper function to make requests to the Graph API."""
        if not self.user_access_token:
            logger.error("Instagram access token not found.")
            return None

        url = f"{self.base_url}/{endpoint}"
        if params is None:
            params = {}
        params["access_token"] = self.user_access_token

        try:
            proxies = {"http": None, "https": None}
            response = requests.get(url, params=params, proxies=proxies)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"An error occurred: {e}")
            if e.response:
                logger.error(f"Response content: {e.response.text}")
            return None

    def debug_token(self):
        """Inspects the current access token to see its metadata and scopes."""
        if not self.user_access_token or not self.app_id or not self.app_secret:
            logger.error("Missing credentials for token debugging.")
            return None
        
        app_access_token = f"{self.app_id}|{self.app_secret}"
        endpoint = "debug_token"
        params = {
            "input_token": self.user_access_token,
            "access_token": app_access_token
        }
        
        # This request does not need the user access token in the params
        url = f"{self.base_url}/{endpoint}"
        try:
            proxies = {"http": None, "https": None}
            response = requests.get(url, params=params, proxies=proxies)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"An error occurred during token debug: {e}")
            if e.response:
                logger.error(f"Response content: {e.response.text}")
            return None

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    api = InstagramGraphAPI()
    token_info = api.debug_token()
    if token_info and token_info.get("data"):
        print("--- Access Token Analysis ---")
        data = token_info["data"]
        print(f"App ID: {data.get('app_id')}")
        print(f"Application: {data.get('application')}")
        print(f"Is Valid: {data.get('is_valid')}")
        print(f"User ID: {data.get('user_id')}")
        print("\n--- GRANTED SCOPES ---")
        for scope in data.get("scopes", []):
            print(f"- {scope}")
        print("---------------------------")
    else:
        print("Could not retrieve token information.")