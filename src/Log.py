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

class Log:

    def __init__(self):

        self.verbosityDict = {0: False,
                              1: logging.CRITICAL,
                              2: logging.ERROR,
                              3: logging.WARNING,
                              4: logging.INFO,
                              5: logging.DEBUG}

        self.simulator = logging.getLogger('SIMULATOR')
        self.node = logging.getLogger('NODE')
        self.gillespie = logging.getLogger('GILLESPIE')
        self.event = logging.getLogger('EVENT')
        self.consensus = logging.getLogger('CONSENSUS')
        self.ledger = logging.getLogger('LEDGER')
        self.quorum = logging.getLogger('QUORUM')
        self.network = logging.getLogger('NETWORK')
        self.mempool = logging.getLogger('MEMPOOL')
        self.transaction = logging.getLogger('TRANSACTION')
        self.message = logging.getLogger('MESSAGE')
        self.value = logging.getLogger('VALUE')
        self.storage = logging.getLogger('STORAGE')
        self.test = logging.getLogger('TEST')

        # Check LogRecord attributes:
        # https://docs.python.org/3/library/logging.html#logrecord-attributes
        self.log_format = '%(msecs).2f - %(name)s - %(levelname)s - %(message)s'

        logging.basicConfig(
            format = self.log_format
        )

    def set_level(self, level):
        self.simulator.setLevel(level)
        self.node.setLevel(level)
        self.gillespie.setLevel(level)
        self.node.setLevel(level)
        self.consensus.setLevel(level)
        self.ledger.setLevel(level)
        self.quorum.setLevel(level)
        self.network.setLevel(level)
        self.mempool.setLevel(level)
        self.transaction.setLevel(level)
        self.message.setLevel(level)
        self.value.setLevel(level)
        self.storage.setLevel(level)
        self.test.setLevel(level)
        return

log = Log()
