"""
=========================
SCPPrepare_test
=========================

Author: Matija Piskorec, Jaime de Vivero Woods, Azizbek Asadov
Last update: Nov 2024

SCPPrepare_test message class.
"""

import unittest

from src.Transaction import Transaction
from src.State import State
from src.Value import Value
from src.SCPBallot import SCPBallot
from src.SCPPrepare import SCPPrepare

class SCPPrepare_test(unittest.TestCase):
    def setUp(self):
        transactions = [Transaction(time=1.0)]
        state = State.init
        value = Value(transactions=transactions, state=state)
        self.ballot = SCPBallot(counter=1, value=value)
        self.prepared = SCPBallot(counter=2, value=value)
        self.scp_prepare = SCPPrepare(ballot=self.ballot, prepared=self.prepared, aCounter=1, hCounter=2, cCounter=1)

    def test_scp_prepare_initialization(self):
        self.assertEqual(self.scp_prepare.ballot, self.ballot)
        self.assertEqual(self.scp_prepare.prepared, self.prepared)
        self.assertEqual(self.scp_prepare.aCounter, 1)
        self.assertEqual(self.scp_prepare.hCounter, 2)
        self.assertEqual(self.scp_prepare.cCounter, 1)

    def test_scp_prepare_repr(self):
        self.assertEqual(repr(self.scp_prepare), f"SCPPrepare(ballot={self.ballot}, prepared={self.prepared}, aCounter=1, hCounter=2, cCounter=1)")
