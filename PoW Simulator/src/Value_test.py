import unittest
from Block import Value
from Transaction import Transaction

class ValueTest(unittest.TestCase):

    def test_combine_empty_list(self):
        combined_value = Value.combine([])
        self.assertEqual(combined_value.transactions, []) # Combining  an empty list should return an empty transactions list

    def test_combine_non_empty_list_unique_transactions(self):
        transactions1 = [Transaction(0), Transaction(0)]
        transactions2 = [Transaction(0), Transaction(0)]
        value1 = Value(transactions=transactions1)
        value2 = Value(transactions=transactions2)

        combined_value = Value.combine([value1, value2])

        self.assertEqual(len(combined_value.transactions), 4)
        self.assertTrue(all(tx in combined_value.transactions for tx in transactions1 + transactions2)) # All transaction should be in the combined result

if __name__ == '__main__':
    unittest.main()
