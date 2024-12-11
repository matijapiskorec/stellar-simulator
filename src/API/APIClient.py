"""
=========================
API Client
=========================

Author: Azizbek Asadov
Last update: December 2024

APIClient class.
"""

import requests
from src.Log import Log
import json
from typing import Optional, Dict, Any

# GLOBAL URL FOR API FETCHING
STELLARBEAT_API_URL = "https://api.stellarbeat.io/v1/network-node-snapshots"

class APIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url

    def fetch(
            self,
            endpoint: str = "",
            method: str = "GET",
            params: Optional[Dict[str, Any]] = None,
            headers: Optional[Dict[str, str]] = None,
            data: Optional[Dict[str, Any]] = None,
            timeout: int = 10
    ) -> Any:
        """
        Fetch data from the API.
        :param endpoint: API endpoint (appended to base URL).
        :param method: HTTP method (e.g., GET, POST).
        :param params: Query parameters.
        :param headers: Request headers.
        :param data: Request body for POST/PUT requests.
        :param timeout: Timeout for the request in seconds.
        :return: Parsed response data or raises an exception on failure.
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        try:
            response = requests.request(
                method=method.upper(),
                url=url,
                params=params,
                headers=headers,
                json=data,
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json()  # Assumes JSON response
        except requests.exceptions.RequestException as e:
            # TODO: add logger here
            raise RuntimeError(f"API Request failed: {e}")