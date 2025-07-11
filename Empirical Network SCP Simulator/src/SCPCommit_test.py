import unittest
from Value import Value
from SCPBallot import SCPBallot
from SCPCommit import SCPCommit
from Transaction import Transaction
from State import State


class SCPCommitTest(unittest.TestCase):
    def setUp(self):
        transactions = [Transaction(0)]
        state = State.init
        value = Value(transactions=transactions, state=state)
        self.ballot = SCPBallot(counter=1, value=value)
        self.scp_commit = SCPCommit(ballot=self.ballot, preparedCounter=1, hCounter=2, cCounter=3)

    def test_scp_commit_initialization(self):
        self.assertEqual(self.scp_commit.ballot, self.ballot)
        self.assertEqual(self.scp_commit.preparedCounter, 1)
        self.assertEqual(self.scp_commit.hCounter, 2)
        self.assertEqual(self.scp_commit.cCounter, 3)

    def test_scp_commit_repr(self):
        self.assertEqual(repr(self.scp_commit),f"SCPCommit(ballot={self.ballot}, preparedCounter=1, hCounter=2, cCounter=3)")
