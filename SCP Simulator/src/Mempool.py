"""
=========================
Mempool
=========================

Author: Matija Piskorec
Last update: August 2023

Mempool class.

A proxy for the incoming transactions which are taken and validated by the nodes.
"""

from Log import log
from Event import Event
from Transaction import Transaction
from SCPNominate import SCPNominate
# import Globals
from Globals import Globals

import numpy as np
import random
import os

class Mempool():

    def __init__(self):
        self.transactions = []
        self.messages = []
        self.log_path = 'simulator_mine_events.txt'

        log.mempool.info('Initialized mempool!')

    def __repr__(self):
        return '[Mempool, transactions = %s, messages = %s]' % (self.transactions,self.messages)


    def log_mine_to_file(self, message):
        with open(self.log_path, 'a') as log_file:
            log_file.write(f"{Globals.simulation_time:.2f} - {message}\n")

    def mine(self):
        transaction_mined = Transaction(time=Globals.simulation_time)
        if transaction_mined not in self.transactions:
            log.mempool.info('Transaction %s mined to the mempool!', transaction_mined)
            self.transactions.append(transaction_mined)
            if not os.path.exists(self.log_path):
                with open(self.log_path, 'w') as log_file:
                    log_file.write("")

            self.log_mine_to_file(f"MEMPOOL - INFO - Transaction {transaction_mined} mined to the mempool!")
            return transaction_mined
        else:
            log.mempool.info('Transaction %s could not be mined to the mempool!', transaction_mined)


    def get_transaction(self):
        if len(self.transactions) > 0:
            transaction = np.random.choice(self.transactions) if len(self.transactions) > 0 else None

            log.mempool.info('Transaction %s retrieved from the mempool!', transaction)
        else:
            transaction = None
            log.mempool.info('No transactions in the mempool!')
        return transaction

    def get_all_transactions(self):
        if len(self.transactions) > 0:
            log.mempool.info('All transactions retrieved from the mempool: %s', self.transactions)
            return self.transactions.copy()  # Return a copy to avoid external mutation
        else:
            log.mempool.info('No transactions in the mempool!')
            return []
