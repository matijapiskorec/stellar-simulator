"""
================================================
Log
================================================

Author: Matija Piskorec
Last update: August 2023

Logger class.

Logging levels (in order of increasing severity):
https://docs.python.org/3/library/logging.html#levels

Logging levels and verbosity levels (higher includes lower):
1 - CRITICAL
2 - ERROR
3 - WARNING
4 - INFO
5 - DEBUG
"""

import logging
import logging
import csv
from datetime import datetime
from typing import List, Dict

class Log:
    def __init__(self):
        self.verbosityDict = {
            0: False,
            1: logging.CRITICAL,
            2: logging.ERROR,
            3: logging.WARNING,
            4: logging.INFO,
            5: logging.DEBUG
        }

        # Initialize loggers
        self.loggers = {
            'SIMULATOR': logging.getLogger('SIMULATOR'),
            'NODE': logging.getLogger('NODE'),
            'GILLESPIE': logging.getLogger('GILLESPIE'),
            'EVENT': logging.getLogger('EVENT'),
            'CONSENSUS': logging.getLogger('CONSENSUS'),
            'LEDGER': logging.getLogger('LEDGER'),
            'QUORUM': logging.getLogger('QUORUM'),
            'NETWORK': logging.getLogger('NETWORK'),
            'MEMPOOL': logging.getLogger('MEMPOOL'),
            'TRANSACTION': logging.getLogger('TRANSACTION'),
            'MESSAGE': logging.getLogger('MESSAGE'),
            'VALUE': logging.getLogger('VALUE'),
            'STORAGE': logging.getLogger('STORAGE'),
            'TEST': logging.getLogger('TEST')
        }

        # Define log format
        self.log_format = '%(asctime)s - %(msecs).2f - %(name)s - %(levelname)s - %(message)s'
        self.date_format = '%Y-%m-%d %H:%M:%S'

        # Configure logging
        logging.basicConfig(format=self.log_format, datefmt=self.date_format)

        # Log tracking storage
        self.log_storage: List[Dict[str, str]] = []
        self.ledger_log: List[Dict[str, str]] = []

        # Start timestamp for simulation
        self.simulation_start_time = datetime.now()

        # Add a custom handler to capture logs
        self._add_custom_handler()

    def _add_custom_handler(self):
        class InMemoryLogHandler(logging.Handler):
            def __init__(self, log_storage, formatter):
                super().__init__()
                self.log_storage = log_storage
                self.formatter = formatter

            def emit(self, record):
                log_entry = {
                    'timestamp': self.formatter.formatTime(record, datefmt='%Y-%m-%d %H:%M:%S'),
                    'name': record.name,
                    'level': record.levelname,
                    'message': record.msg
                }
                self.log_storage.append(log_entry)

        formatter = logging.Formatter(self.log_format, self.date_format)
        handler = InMemoryLogHandler(self.log_storage, formatter)
        handler.setFormatter(logging.Formatter(self.log_format, self.date_format))

        for logger in self.loggers.values():
            logger.addHandler(handler)

    def set_level(self, verbosity_level):
        level = self.verbosityDict.get(verbosity_level, logging.NOTSET)
        for logger in self.loggers.values():
            logger.setLevel(level)

    def log_finalized_ledger(self, transaction_count: int):
        current_time = datetime.now()
        elapsed_time = (current_time - self.simulation_start_time).total_seconds()
        self.ledger_log.append({
            'timestamp': str(elapsed_time),
            'transactions': str(transaction_count)
        })

    def export_ledger_logs_to_csv(self, file_path: str):
        """
        Used for exporting logs to the csv file
        """
        if not self.ledger_log:
            print("No ledger logs to export.")
            return

        with open(file_path, mode='w', newline='', encoding='utf-8') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=['timestamp', 'transactions'])
            writer.writeheader()
            writer.writerows(self.ledger_log)

        print(f"Ledger logs exported to {file_path}")

    def log_example_messages(self):
        self.loggers['SIMULATOR'].info("Simulator started.")
        self.loggers['LEDGER'].info("Finalized ledger processed.")
        self.loggers['TRANSACTION'].debug("Transaction created.")
        self.loggers['CONSENSUS'].critical("Consensus failure detected.")

log = Log()
