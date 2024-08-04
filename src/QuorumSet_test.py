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

    def test_inner_set_blocking_threshold_is_met(self):
        test_node1 = Node("test_node1")
        test_node2 = Node("test_node2")
        test_node3 = Node("test_node3")

        value = Value(transactions={Transaction(0), Transaction(0)})
        test_node1.statement_counter = {value.hash: {'voted': {test_node1.name: 1, test_node2.name : 1}, 'accepted': {test_node3.name: 1}}}
        quorum = [test_node1, test_node2]

        check = self.node.quorum_set.check_inner_set_blocking_threshold(test_node1, value, quorum)
        self.assertEqual(check, 1)

    def test_inner_set_blocking_threshold_returns_is_not_met(self):
        # If only the calling node has voted, then it should return False
        test_node1 = Node("test_node1")

        value = Value(transactions={Transaction(0), Transaction(0)})
        test_node1.statement_counter = {value.hash: {'voted': {test_node1.name: 1}, 'accepted': {}}}
        quorum = [test_node1]

        check = self.node.quorum_set.check_inner_set_blocking_threshold(test_node1, value, quorum)
        self.assertEqual(check, 0)


if __name__ == '__main__':
    unittest.main()
