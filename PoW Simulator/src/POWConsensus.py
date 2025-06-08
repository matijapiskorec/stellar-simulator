"""
=========================
POWConsensus
=========================

Author: Jaime de Vivero Woods
Last update: May 2025

Proof-of-Work consensus class.
"""

from Log import log
from Event import Event

class POWConsensus:

    @classmethod
    def get_events(cls):

        # mine - Node should add a new transaction to its ledger.
        # gossip - Node should send a message to one of its peers.

        """
        Only PoW‐relevant events:
          - mine:            trigger block/tx creation in a node's mempool
          - retrieve_tx:     pick a tx out of a node's mempool
          - broadcast_tx:    send that tx to one of the node's peers
          - receive_tx:      peer receives and validates the tx
        """
        events = [
            Event('create transaction'),
            Event('retrieve transaction'),
            Event('mine'),
            Event('receive block')
        ]

        log.consensus.info("PoWConsensus events: %s", [e.name for e in events])

        return events

    def mine(self, data):
        raise NotImplementedError()

    def retrieve_transaction_from_mempool(self, data):
        raise NotImplementedError()

    def broadcast_transaction(self, data):
        raise NotImplementedError()

    def receive_transaction_from_peer(self, data):
        raise NotImplementedError()
