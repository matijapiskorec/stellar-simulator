"""
=========================
QuorumSetTest
=========================

Author: Matija Piskorec, Jaime de Vivero Woods, Azizbek Asadov
Last update: Nov 2024

QuorumSetTest message class.
"""

import unittest

from src.Value import Value
from src.Node import Node
from src.Transaction import Transaction
from src.SCPBallot import SCPBallot
from src.SCPPrepare import SCPPrepare

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

    def test_get_nodes_with_broadcast_prepare_msgs_returns_correctly(self):
        # If only the calling node has voted, then it should return False
        test_node1 = Node("test_node1")
        test_node2 = Node("2")
        test_node3 = Node("3")
        test_node4 = Node("4")
        test_node5 = Node("5")

        test_value = Value(transactions={Transaction(0), Transaction(0)})
        test_ballot = SCPBallot(counter=1, value=test_value)
        test_message = SCPPrepare(ballot=test_ballot)

        test_node2.ballot_prepare_broadcast_flags.add(test_message)
        test_node3.ballot_prepare_broadcast_flags.add(test_message)
        test_node5.ballot_prepare_broadcast_flags.add(test_message)

        test_quorum = [test_node1, test_node2, test_node3, test_node4, test_node5]

        result = test_node1.quorum_set.get_nodes_with_broadcast_prepare_msgs(test_node1, test_quorum)

        self.assertEqual([test_node2, test_node3, test_node5], result)

    def test_get_nodes_with_broadcast_prepare_msgs_returns_empty_for_none(self):
        # No nodes in the quorum have broadcast prepare messages
        test_node1 = Node("test_node1")
        test_node2 = Node("2")
        test_node3 = Node("3")
        test_node4 = Node("4")
        test_node5 = Node("5")

        test_quorum = [test_node1, test_node2, test_node3, test_node4, test_node5]

        result = test_node1.quorum_set.get_nodes_with_broadcast_prepare_msgs(test_node1, test_quorum)

        # Expect an empty list since no nodes broadcast prepare messages
        self.assertEqual([], result)

    def test_get_nodes_with_broadcast_prepare_msgs_returns_correctly_for_only_itself_and_another(self):
        # The calling node itself has broadcast prepare messages, should not be included in the result
        test_node1 = Node("test_node1")
        test_node2 = Node("2")
        test_node3 = Node("3")
        test_node4 = Node("4")
        test_node5 = Node("5")

        test_value = Value(transactions={Transaction(0), Transaction(0)})
        test_ballot = SCPBallot(counter=1, value=test_value)
        test_message = SCPPrepare(ballot=test_ballot)

        test_node1.ballot_prepare_broadcast_flags.add(test_message) # test_node1 shouldnt be in the result
        test_node2.ballot_prepare_broadcast_flags.add(test_message)

        test_quorum = [test_node1, test_node2, test_node3, test_node4, test_node5]

        result = test_node1.quorum_set.get_nodes_with_broadcast_prepare_msgs(test_node1, test_quorum)

        # test_node1 should be excluded from the result
        self.assertEqual([test_node2], result)


    def test_check_prepare_threshold2(self):
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


    def test_check_prepare_threshold(self):
        # Setup nodes
        test_node1 = Node("test_node1")
        test_node2 = Node("test_node2")
        test_node3 = Node("test_node3")
        test_node4 = Node("test_node4")

        # Setup quorum and threshold
        quorum = [test_node1, test_node2, test_node3, test_node4]
        threshold = 3  # We need at least 3 nodes to sign the ballot

        # Simulate prepare_statement_counter for a specific ballot
        ballot = SCPBallot(counter=0, value=Value(transactions={Transaction(0)}))
        prepare_statement_counter = {
            ballot.value: {
                'voted': {test_node1, test_node2, test_node3},
                'accepted': {test_node4}
            }
        }

        # Check if threshold is met
        result = self.node.quorum_set.check_prepare_threshold(ballot, quorum, threshold, prepare_statement_counter)
        self.assertTrue(result)  # It should return True because 3 out of 4 nodes have voted/accepted


    def test_check_prepare_threshold_returns_False(self):
        # Setup nodes
        test_node1 = Node("test_node1")
        test_node2 = Node("test_node2")
        test_node3 = Node("test_node3")
        test_node4 = Node("test_node4")

        # Setup quorum and threshold
        quorum = [test_node1, test_node2, test_node3, test_node4]
        threshold = 3  # We need at least 3 nodes to sign the ballot

        # Simulate prepare_statement_counter for a specific ballot
        ballot = SCPBallot(counter=0, value=Value(transactions={Transaction(0)}))
        prepare_statement_counter = {
            ballot.value: {
                'voted': {test_node1},
                'accepted': {test_node4}
            }
        }

        # Check if threshold is met
        result = self.node.quorum_set.check_prepare_threshold(ballot, quorum, threshold, prepare_statement_counter)
        self.assertFalse(result)  # It should return True because 3 out of 4 nodes have voted/accepted

    def test_retrieve_all_peers_returns_correctly(self):
        test_node1 = Node("test_node1")
        test_node2 = Node("test_node2")
        test_node3 = Node("test_node3")
        test_node4 = Node("test_node4")

        self.node.quorum_set.nodes = [test_node1, test_node2]
        self.node.quorum_set.inner_sets = [[self.node, test_node3], [self.node, test_node4]]



if __name__ == '__main__':
    unittest.main()

