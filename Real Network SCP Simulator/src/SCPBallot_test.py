import unittest
from Transaction import Transaction
from State import State
from Value import Value
from SCPBallot import SCPBallot

class SCPBallot_test(unittest.TestCase):
    def setUp(self):
        transactions1 = [Transaction(time=1.0)]
        transactions2 = [Transaction(time=2.0)]
        state = State.init
        self.value1 = Value(transactions=transactions1, state=state)
        self.value2 = Value(transactions=transactions2, state=state)
        self.ballot1 = SCPBallot(counter=1, value=self.value1)
        self.ballot2 = SCPBallot(counter=2, value=self.value2)

    def test_ballot_initialization(self):
        self.assertEqual(self.ballot1.counter, 1)
        self.assertEqual(self.ballot1.value, self.value1)

    def test_ballot_comparison(self):
        self.assertTrue(self.ballot1 < self.ballot2)
        self.assertFalse(self.ballot2 < self.ballot1)
        self.assertTrue(self.ballot1 < SCPBallot(counter=2, value=self.value1))
        self.assertFalse(self.ballot1 < SCPBallot(counter=1, value=self.value2))

    def test_ballot_repr(self):
        self.assertEqual(repr(self.ballot1), f"SCPBallot(counter=1, value={self.value1})")

if __name__ == "__main__":
    unittest.main()