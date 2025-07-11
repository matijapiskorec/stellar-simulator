import unittest
from SCPBallot import SCPBallot
from SCPExternalize import SCPExternalize
from Transaction import Transaction
from Value import Value
from State import State
from unittest.mock import patch

class SCPExternalizeTest(unittest.TestCase):
    def setUp(self):
        transactions = [Transaction(0)]
        state = State.init
        value = Value(transactions=transactions, state=state)
        self.ballot = SCPBallot(counter=1, value=value)

        self.scp_externalize = SCPExternalize(ballot=self.ballot, hCounter=5)

    def test_scp_externalize_initialization(self):
        self.assertEqual(self.scp_externalize.ballot, self.ballot)
        self.assertEqual(self.scp_externalize.hCounter, 5)

    def test_scp_externalize_default_hCounter(self):
        scp_externalize_default = SCPExternalize(ballot=self.ballot)
        self.assertEqual(scp_externalize_default.hCounter, 0)

    def test_scp_externalize_repr(self):
        self.assertEqual(repr(self.scp_externalize),f"SCPExternalize(ballot={self.ballot}, hCounter=5, time={self.scp_externalize._time})")

if __name__ == "__main__":
    unittest.main()