import unittest
from Storage import Storage
from Value import Value
from Node import Node
from Transaction import Transaction
from SCPNominate import SCPNominate

class SCPNominateTest(unittest.TestCase):

    def test_parse_message_state_returns_correctly(self):
        value1 = Value(transactions={Transaction(0), Transaction(0)})
        value2 = Value(transactions={Transaction(0), Transaction(0)})

        message = SCPNominate(voted=[value1], accepted=[value2])

        parsed = message.parse_message_state(message)

        self.assertEqual(parsed[0], value1) # value3 and value1 should be present
        self.assertEqual(parsed[1], value2) #value4 and value2 should be present

    def test_parse_message_state_returns_only_one_correctly(self):
        value1 = Value(transactions={Transaction(0), Transaction(0)})
        value2 = Value(transactions={Transaction(0), Transaction(0)})

        message1 = SCPNominate(voted=[value1, value2], accepted=[])
        message2 = SCPNominate(voted=[], accepted=[value2, value1])

        parsed1 = message1.parse_message_state(message1)
        parsed2 = message2.parse_message_state(message2)


        self.assertEqual(parsed1[0], Value.combine([value1, value2])) # value1 and value2 should be present
        self.assertEqual(parsed1[1], [])  # accepted field should be an empty list
        self.assertEqual(parsed2[0], [])  # voted field should be an empty list
        self.assertEqual(parsed2[1], Value.combine([value2, value1]))  # value2 and value1 should be present

    def test_parse_message_state_returns_empty_list_for_empty_message(self):
        message1 = SCPNominate(voted=[], accepted=[])

        parsed1 = message1.parse_message_state(message1)

        self.assertEqual(parsed1[0], []) # value1 and value2 should be present
        self.assertEqual(parsed1[1], [])  # accepted field should be an empty list

    def test_parse_message_state_returns_voted_and_accepted(self):
        value1 = Value(transactions={Transaction(0), Transaction(0)})
        value2 = Value(transactions={Transaction(0), Transaction(0)})
        value3 = Value(transactions={Transaction(0), Transaction(0)})

        message1 = SCPNominate(voted=[value1, value2], accepted=[value3])

        parsed1 = message1.parse_message_state(message1)

        self.assertEqual(parsed1[0], Value.combine([value1, value2])) # value1 and value2 should be present
        self.assertEqual(parsed1[1], value3)  # accepted field should be an empty list

if __name__ == "__main__":
    unittest.main()