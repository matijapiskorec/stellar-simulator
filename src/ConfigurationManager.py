"""
=========================
ConfigManager
=========================

Author: Azizbek Asadov
Last update: Jan 2024

APIClient class.
"""

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List

class ConfigManager:
    def __init__(self, config_file: str = None):
        if config_file:
            self.simulation_params = {}
            self.load_from_file(config_file)
            return

        # default params
        self.simulation_params = {
            "mine": {"tau": 5.0, "tau_domain": None},
            "retrieve_transaction_from_mempool": {"tau": 5.0, "tau_domain": None},
            "nominate": {"tau": 5.0, "tau_domain": None},
            "retrieve_message_from_peer": {"tau": 2.0, "tau_domain": None},
            "prepare_ballot": {"tau": 7.0, "tau_domain": None},
            "receive_prepare_message": {"tau": 1.0, "tau_domain": None},
            "prepare_commit": {"tau": 7.0, "tau_domain": None},
            "receive_commit_message": {"tau": 1.0, "tau_domain": None},
            "prepare_externalize_message": {"tau": 3.0, "tau_domain": None},
            "receive_externalize_msg": {"tau": 1.0, "tau_domain": None},
        }

    def get_simulation_params(self) -> Dict[str, Any]:
        return self.simulation_params

    def set_tau(self, key: str, tau_value: float):
        if key in self.simulation_params:
            self.simulation_params[key]["tau"] = tau_value
        else:
            raise KeyError(f"Key '{key}' not found in simulation parameters.")

    def load_from_file(self, config_file: str):
        with open(config_file, 'r') as file:
            data = json.load(file)
            for key, value in data.items():
                if key in self.simulation_params:
                    self.simulation_params[key]["tau"] = value.get("tau", self.simulation_params[key]["tau"])
                    self.simulation_params[key]["tau_domain"] = value.get("tau_domain", self.simulation_params[key]["tau_domain"])
        print(f"Loaded simulation parameters from {config_file}.")

    def save_to_file(self, config_file: str):
        with open(config_file, 'w') as file:
            json.dump(self.simulation_params, file, indent=4)
        print(f"Saved simulation parameters to {config_file}.")