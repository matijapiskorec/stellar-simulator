import unittest
from Value import Value
from Node import Node
from Transaction import Transaction

class QuorumSetTest(unittest.TestCase):
    def setUp(self):
        self.node = Node("test_node")

    def test_check_threshold(self):
        test_node1 = Node("test_node1")
        test_node2 = Node("test_node2")
        test_node3 = Node("test_node3")
        test_node4 = Node("test_node4")

        value = Value(transactions={Transaction(0), Transaction(0)})
        threshold = 4
        statement_counter = {value.hash: {'voted': {test_node1.name: 1, test_node2.name : 1, test_node3.name: 1}, 'accepted': {test_node4.name : 1}}}

        quorum = [test_node1, test_node2, test_node3, test_node4]

        check = self.node.quorum_set.check_threshold(value, quorum, threshold, statement_counter)
        self.assertTrue(check)


if __name__ == '__main__':
    unittest.main()
