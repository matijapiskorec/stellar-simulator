"""
=========================
Mempool
=========================

Author: Matija Piskorec, Jaime de Vivero Woods
Last update: April 2025

Mempool class.

A proxy for the incoming transactions which are taken and validated by the nodes.
"""

from Log import log


class Mempool():

    def __init__(self, transactions=None):
        self.transactions = list(transactions) if transactions is not None else []
        self.log_path = 'simulator_mine_events.txt'

        log.mempool.info('Initialized mempool!')

    def __repr__(self):
        return f"[Mempool  txs={self.transactions}]"

    def add_transaction(self, tx):
        """Add tx to the pool if not already seen."""
        if tx in self.transactions:
            log.mempool.debug("Transaction %s already in mempool", tx)
            return False

        self.transactions.append(tx)
        log.mempool.info("Added transaction %s to mempool", tx)
        return True

    def get_all_transactions(self):
        if len(self.transactions) > 0:
            log.mempool.info('All transactions retrieved from the mempool: %s', self.transactions)
            return self.transactions.copy()  # Return a copy to avoid external mutation
        else:
            log.mempool.info('No transactions in the mempool!')
            return []

    def get_highest_fee_transaction(self):
        """
        Return (without removing) the transaction with the highest fee.
        If the mempool is empty, returns None.
        """
        if not self.transactions:
            log.mempool.info("Mempool empty: no tx to select")
            return None

        # find the tx with max fee
        top_tx = max(self.transactions, key=lambda tx: tx.fee)
        log.mempool.info("Selected highest-fee transaction %s", top_tx)
        return top_tx

