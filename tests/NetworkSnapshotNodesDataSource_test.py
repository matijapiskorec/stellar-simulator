import unittest
from unittest.mock import patch, mock_open, MagicMock
from datetime import datetime, timedelta
import os
import json
from src.NetworkSnapshotNodesDataSource import NetworkSnapshotNodesDataSource

class TestDataSource(unittest.TestCase):

    @patch("data_source.NetworkSnapshotsAPIClient")
    def setUp(self, MockAPIClient):
        self.mock_api_client = MockAPIClient.return_value
        self.file_path = "test_node_snapshots.json"
        self.data_source = NetworkSnapshotNodesDataSource(self.file_path)
        self.sample_data = [{"node": "sample_node"}]

    @patch("os.path.exists")
    @patch("os.path.getmtime")
    def test_is_file_valid_valid(self, mock_getmtime, mock_exists):
        mock_exists.return_value = True
        mock_getmtime.return_value = (datetime.now() - timedelta(days=3)).timestamp()

        self.assertTrue(self.data_source._is_file_valid())

    @patch("os.path.exists")
    @patch("os.path.getmtime")
    def test_is_file_valid_invalid(self, mock_getmtime, mock_exists):
        mock_exists.return_value = True
        mock_getmtime.return_value = (datetime.now() - timedelta(weeks=2)).timestamp()

        self.assertFalse(self.data_source._is_file_valid())

    @patch("os.path.exists")
    def test_is_file_valid_nonexistent(self, mock_exists):
        mock_exists.return_value = False

        self.assertFalse(self.data_source._is_file_valid())

    @patch("builtins.open", new_callable=mock_open, read_data=json.dumps([{"node": "sample_node"}]))
    def test_load_from_file(self, mock_file):
        data = self.data_source._load_from_file()

        mock_file.assert_called_once_with(self.file_path, "r")
        self.assertEqual(data, [{"node": "sample_node"}])

    @patch("builtins.open", new_callable=mock_open)
    def test_save_to_file(self, mock_file):
        self.data_source._save_to_file(self.sample_data)

        mock_file.assert_called_once_with(self.file_path, "w")
        mock_file().write.assert_called_once_with(json.dumps(self.sample_data, indent=4))

    @patch.object(NetworkSnapshotNodesDataSource, "_is_file_valid")
    @patch.object(NetworkSnapshotNodesDataSource, "_load_from_file")
    def test_get_data_from_file(self, mock_load_from_file, mock_is_file_valid):
        mock_is_file_valid.return_value = True
        mock_load_from_file.return_value = self.sample_data

        data = self.data_source.get_data()

        mock_is_file_valid.assert_called_once()
        mock_load_from_file.assert_called_once()
        self.assertEqual(data, self.sample_data)

    @patch.object(NetworkSnapshotNodesDataSource, "_is_file_valid")
    @patch.object(NetworkSnapshotNodesDataSource, "_save_to_file")
    def test_get_data_from_api(self, mock_save_to_file, mock_is_file_valid):
        mock_is_file_valid.return_value = False
        self.mock_api_client.get_node_snapshots.return_value = self.sample_data

        data = self.data_source.get_data()

        mock_is_file_valid.assert_called_once()
        self.mock_api_client.get_node_snapshots.assert_called_once()
        mock_save_to_file.assert_called_once_with(self.sample_data)
        self.assertEqual(data, self.sample_data)