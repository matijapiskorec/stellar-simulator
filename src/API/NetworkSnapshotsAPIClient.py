from typing import Any, Optional
from src.API.APIClient import STELLARBEAT_API_URL
from src.Log import Log
from src.API import APIClient

class NetworkSnapshotsAPIClient(APIClient):
    def __init__(self):
        super().__init__(STELLARBEAT_API_URL)

    def get_node_snapshots(self, at: Optional[str] = None) -> Any:
        """
        Fetches node snapshots from Stellarbeat API, optionally at a specific point in time.
        :param at: Optional timestamp (ISO 8601 format) to fetch snapshots at a specific point in time.
        :return: Parsed response from the API.
        """
        endpoint = "node-snapshots"
        params = {"at": at} if at else None
        headers = {"accept": "application/json"}

        return self.fetch(endpoint=endpoint, params=params, headers=headers)
