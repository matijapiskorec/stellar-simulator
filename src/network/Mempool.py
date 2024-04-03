"""
=========================
Mempool
=========================

Author: Matija Piskorec
Last update: August 2023

Mempool class.

A proxy for the incoming transactions which are taken and validated by the nodes.
"""

from src.common.Log import log
from Transaction import Transaction
from src.common.Globals import Globals
from src.network.Ledger import Ledger

import numpy as np

class Mempool:

    def __init__(self, max_transactions=100):
        self.ledger = Ledger(max_transactions)
        self.transactions = []
        self.max_transactions = max_transactions

        # Mine some initial transactions
        # for _ in range(5):
        #     self.mine()

        log.mempool.info('Initialized mempool!')

    def __repr__(self):
        return '[Mempool, transactions = %s]' % (len(self.transactions))

    def mine(self):
        if len(self.transactions) < self.max_transactions:
            transaction_mined = Transaction(time=Globals.simulation_time)
            log.mempool.info('Transaction %s mined to the mempool!', transaction_mined)
            self.transactions.append(transaction_mined)
            return transaction_mined
        else:
            log.mempool.info('Mempool is full, cannot mine new transaction!')
            return None

    def get_transaction(self, remove=False):
        """
        Retrieves a transaction from the mempool.

        Args:
            remove (bool, optional): If True, removes the retrieved transaction from the mempool. Defaults to False.

        Returns:
            Transaction object or None if no transactions are available.
        """

        if len(self.transactions) > 0:
            transaction = np.random.choice(self.transactions)
            log.mempool.info('Transaction %s retrieved from the mempool!', transaction)
            if remove:
                self.transactions.remove(transaction)
            return transaction
        else:
            log.mempool.info('No transactions in the mempool!')
            return None

    def broadcast_transaction(self, transaction):
        """
        Broadcasts a transaction to the network.

        This implementation leverages the Ledger class for potential network communication
        and assumes direct communication with connected nodes for mempool updates.

        You might need to adapt it based on your specific network communication protocol
        and serialization mechanisms.
        """

        self.transactions.append(transaction)

        try:
            self.ledger.broadcast(transaction)
            log.network.info('Transaction %s broadcasted to the network using Ledger!', transaction.hash)
        except AttributeError:
            log.network.warning('Ledger does not support broadcasting, falling back to direct communication!')

        for node in self.connected_nodes:  # Assuming connected_nodes attribute in Node class
            node.add_to_mempool(transaction.serialize())  # Serialize transaction before sending

        log.network.info('Transaction %s directly broadcasted to connected nodes!', transaction.hash)

    def mine(self):
        if len(self.transactions) < self.max_transactions:
            transaction_mined = Transaction(time=Globals.simulation_time)
            log.mempool.info('Transaction %s mined to the mempool!', transaction_mined)
            self.transactions.append(transaction_mined)
            return transaction_mined
        else:
            log.mempool.info('Mempool is full, cannot mine new transaction!')
            return None



#
# from src.common.Log import log
# from Transaction import Transaction
# # import Globals
# from Globals import Globals
#
# import numpy as np
#
#
# class Mempool():
#
#     def __init__(self):
#     # def __init__(self,simulation_time=None):
#     # def __init__(self,simulation_time):
#         self.transactions = []
#         self.messages = []
#         # self.simulation_time = simulation_time
#
#         # Mine some transactions to the mempool for faster initialization of simulation!
#         for i in range(5):
#             self.mine()
#
#         log.mempool.info('Initialized mempool!')
#
#     def __repr__(self):
#         return '[Mempool, transactions = %s, messages = %s]' % (self.transactions,self.messages)
#
#     def mine(self):
#
#         # TODO: For now transactions just apper (are mined) in the mempool!
#         # transaction_mined = Transaction()
#         # transaction_mined = Transaction(time=self.simulation_time)
#         transaction_mined = Transaction(time=Globals.simulation_time)
#         log.mempool.info('Transaction %s mined to the mempool!', transaction_mined)
#         self.transactions.append(transaction_mined)
#         return transaction_mined
#
#     def get_transaction(self):
#
#         # TODO: Consider allowing nodes to choose transactions from mempool based on some criteria!
#         if len(self.transactions) > 0:
#
#             # Get a random transaction from the mempool - transaction remains in the mempool!
#             transaction = np.random.choice(self.transactions) if len(self.transactions) > 0 else None
#
#             log.mempool.info('Transaction %s retrieved from the mempool!', transaction)
#         else:
#             # TODO: If there are no transactions in the mempool then None will be returned!
#             transaction = None
#             log.mempool.info('No transactions in the mempool!')
#         return transaction
#
#     # def update_time(self,simulation_time):
#     #     """
#     #     Update time for the mempool so that newly mined transactions would have correct timestamp.
#     #     """
#     #     self.simulation_time = simulation_time
#     #     return
#
#     # # TODO: Remove as we are not storing messages in the mempool anymore!
#     # def add_message(self,message):
#     #     # TODO: Now we can only add SCPNominate messages to the mempool!
#     #     assert isinstance(message, SCPNominate), 'Message %s is not an instance of SCPNominate!' % message
#     #     self.messages.append(message)
#     #     log.mempool.info('Added message %s to the mempool!', message)
#     #     return
#
#     # def get_message(self):
#
#     #     if len(self.messages) > 0:
#
#     #         # Get a random message from the mempool - message remains in the mempool!
#     #         message = np.random.choice(self.messages) if len(self.messages) > 0 else None
#
#     #         log.mempool.info('Message %s retrieved from the mempool!', message)
#     #     else:
#     #         # TODO: If there are no messages in the mempool then None will be returned!
#     #         message = None
#     #         log.mempool.info('No messages in the mempool!')
#     #     return message

