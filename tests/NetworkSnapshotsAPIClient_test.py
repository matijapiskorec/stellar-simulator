"""
=========================
TestNetworkSnapshotsAPIClient
=========================

Author: Matija Piskorec, Jaime de Vivero Woods, Azizbek Asadov
Last update: Dec 2024

TestNetworkSnapshotsAPIClient message class.
"""

import unittest
from unittest.mock import patch, MagicMock
from src.API.NetworkSnapshotsAPIClient import NetworkSnapshotsAPIClient

class TestNetworkSnapshotsAPIClient(unittest.TestCase):

    @patch("network_snapshots_client.requests.request")
    def test_get_node_snapshots_latest(self, mock_request: MagicMock):
        """
        Test fetching the latest node snapshots without a specific timestamp.
        """
        # Arrange
        expected_response = {"data": "latest_snapshots"}
        mock_request.return_value.status_code = 200
        mock_request.return_value.json.return_value = expected_response

        client = NetworkSnapshotsAPIClient()

        # Act
        response = client.get_node_snapshots()

        # Assert
        mock_request.assert_called_once_with(
            method="GET",
            url=f"{client.base_url}/node-snapshots",
            params=None,
            headers={"accept": "application/json"},
            json=None,
            timeout=10
        )
        self.assertEqual(response, expected_response)

    @patch("network_snapshots_client.requests.request")
    def test_get_node_snapshots_at_specific_time(self, mock_request: MagicMock):
        """
        Test fetching node snapshots at a specific point in time.
        """
        # Arrange
        expected_response = {"data": "snapshots_at_time"}
        mock_request.return_value.status_code = 200
        mock_request.return_value.json.return_value = expected_response
        specific_time = "2024-12-10T17:03:37.858Z"

        client = NetworkSnapshotsAPIClient()

        # Act
        response = client.get_node_snapshots(at=specific_time)

        # Assert
        mock_request.assert_called_once_with(
            method="GET",
            url=f"{client.base_url}/node-snapshots",
            params={"at": specific_time},
            headers={"accept": "application/json"},
            json=None,
            timeout=10
        )
        self.assertEqual(response, expected_response)

    @patch("network_snapshots_client.requests.request")
    def test_get_node_snapshots_api_failure(self, mock_request: MagicMock):
        """
        Test handling of API failure scenarios.
        """
        # Arrange
        mock_request.return_value.status_code = 500
        mock_request.return_value.json.side_effect = Exception("Internal Server Error")

        client = NetworkSnapshotsAPIClient()

        # Act & Assert
        with self.assertRaises(RuntimeError) as context:
            client.get_node_snapshots()

        self.assertIn("API Request failed", str(context.exception))
        mock_request.assert_called_once()
