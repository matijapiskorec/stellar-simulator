"""
=========================
NetworkSnapshotNodesDataSource
=========================

Author: Matija Piskorec, Jaime de Vivero Woods, Azizbek Asadov
Last update: December 2024

NetworkSnapshotNodesDataSource class.
"""

import os
import json
from datetime import datetime, timedelta
from typing import Any, Dict
from src.API.NetworkSnapshotsAPIClient import NetworkSnapshotsAPIClient

class NetworkSnapshotNodesDataSource:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.api_client = NetworkSnapshotsAPIClient()
        self.cache_valid_duration = timedelta(weeks=1)  # Cache is valid for 1 week

    def _is_file_valid(self) -> bool:
        if not os.path.exists(self.file_path):
            return False

        file_mod_time = datetime.fromtimestamp(os.path.getmtime(self.file_path))
        return datetime.now() - file_mod_time <= self.cache_valid_duration

    def _load_from_file(self) -> Any:
        with open(self.file_path, "r") as file:
            return json.load(file)

    def _save_to_file(self, data: Any):
        with open(self.file_path, "w") as file:
            json.dump(data, file, indent=4)

    def get_data(self) -> Any:
        if self._is_file_valid():
            print("Loading data from cache.")
            return self._load_from_file()
        else:
            print("Fetching data from API.")
            data = self.api_client.get_node_snapshots()
            self._save_to_file(data)
            return data

## TODO: replace prints with logger to log current actions

