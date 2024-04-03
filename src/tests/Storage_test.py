import unittest
from src.storage.Storage import Storage
from src.consensus.Value import Value
from src.network.Node import Node
from src.network.Transaction import Transaction
from src.network.SCPNominate import SCPNominate

class StorageTest(unittest.TestCase):

    def setUp(self):
        self.node = Node("test_node")
        self.storage = Storage(self.node)

    def test_empty_messages(self):
        # Test that empty messages return empty Value objects for voted and accepted
        voted, accepted = self.storage.get_combined_messages()
        self.assertEqual(len(voted.transactions), 0) # Voted field should be empty
        self.assertEqual(len(accepted.transactions), 0) # Accepted field should be empty

    def test_single_message(self):
        # Test combining a single message
        value1 = Value(transactions={Transaction(0), Transaction(0)})
        value2 = Value(transactions={Transaction(0), Transaction(0)})
        message = SCPNominate(voted=[value1], accepted=[value2])

        self.storage.add_messages(message)
        voted, accepted = self.storage.get_combined_messages()

        self.assertEqual(voted, value1) # Voted field should have value 1
        self.assertEqual(accepted, value2) # Accept field should have value 2

    def test_multiple_messages(self):
        # Test combining multiple messages
        value1 = Value(transactions={Transaction(0)})
        value2 = Value(transactions={Transaction(0), Transaction(0)})
        value3 = Value(transactions={Transaction(0), Transaction(0)})
        value4 = Value(transactions={Transaction(0), Transaction(0)})

        message1 = SCPNominate(voted=[value1], accepted=[value2])
        message2 = SCPNominate(voted=[value3], accepted=[value4])
        self.storage.add_messages([message1, message2])

        voted, accepted = self.storage.get_combined_messages()

        self.assertEqual(voted, Value.combine([value3, value1])) # value3 and value1 should be present
        self.assertEqual(accepted, Value.combine([value4, value2])) #value4 and value2 should be present

if __name__ == '__main__':
    unittest.main()
