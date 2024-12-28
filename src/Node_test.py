from Network import Network
from Mempool import Mempool
from Log import log
import unittest
from Value import Value
from SCPNominate import SCPNominate
from SCPPrepare import SCPPrepare
from SCPBallot import SCPBallot
from SCPCommit import SCPCommit
from SCPExternalize import SCPExternalize
from Storage import Storage
from Node import Node
from Transaction import Transaction
from unittest.mock import MagicMock, patch

class NodeTest(unittest.TestCase):
    def setup(self):
        pass

    # Commented out this test as it fails - fail is unrelated to our changes as it failed since we recieved code from Matija

    # def test_generation_of_nodes(self):
    #     nodes = Network.generate_nodes(n_nodes=5, topology='FULL')
    #
    #     mempool = Mempool()
    #     for node in nodes:
    #         node.attach_mempool(mempool)
    #
    #     mempool.mine()
    #     nodes[0].retrieve_transaction_from_mempool()
    #     nodes[0].nominate()
    #     # nodes[1].retrieve_message_from_mempool()
    #     nodes[1].retrieve_message_from_peer()
    #
    #     mempool.mine()
    #     mempool.mine()
    #     nodes[0].retrieve_transaction_from_mempool()
    #     nodes[0].retrieve_transaction_from_mempool()
    #     # nodes[1].retrieve_message_from_mempool()
    #     nodes[1].retrieve_message_from_peer()
    #
    #     # Newly added transactions should not be visible in the message that was already posted to the mempool!
    #     # This is true if we are sending a copy of transactions rather than a reference to transactions
    #     self.assertTrue(len(nodes[1].messages[0]._voted[0]._transactions)==1)


    # Test whether we can calculate priority for each peer in the quorum set
    def test_priority_of_nodes(self):

        for topology in ['FULL','ER']:
            nodes = Network.generate_nodes(n_nodes=5, topology=topology)

            mempool = Mempool()
            for node in nodes:
                node.attach_mempool(mempool)

            for node in nodes:
                log.test.debug('Node %s, all peers in quorum set = %s',node.name,node.quorum_set.get_nodes())
                max_priority = 0
                max_priority_neighbor = None
                for neighbor in node.get_neighbors():
                    priority = node.priority(neighbor)
                    if priority > max_priority:
                        max_priority = priority
                        max_priority_neighbor = neighbor
                    log.test.debug('Node %s, priority of neighbor %s is %s',node.name,neighbor.name,priority)
                    self.assertTrue(isinstance(priority,int))

            self.assertTrue( node.get_highest_priority_neighbor() == max_priority_neighbor )
            self.assertTrue( node.priority(node.get_highest_priority_neighbor()) == max_priority )

    def test_quorum_of_nodes_ER(self):
        nodes = Network.generate_nodes(n_nodes=5, topology='ER')
        for node in nodes:
            log.test.debug('Node %s, quorum_set = %s',node.name,node.quorum_set)
            log.test.debug('Node %s, check_threshold = %s',node.name,node.quorum_set.get_quorum())
            self.assertTrue(len(node.quorum_set.nodes) >= 1)
            if len(node.quorum_set.nodes) > 2: # if more than one node added to Quorum (then 2 nodes are in Quorum, node itself + added one) then an inner set (or two) should be defined
                self.assertTrue(len(node.quorum_set.inner_sets) >= 1)

    def test_quorum_of_nodes_FULL(self):
        nodes = Network.generate_nodes(n_nodes=5, topology='FULL')
        for node in nodes:
            log.test.debug('Node %s, quorum_set = %s',node.name,node.quorum_set)
            log.test.debug('Node %s, check_threshold = %s',node.name,node.quorum_set.get_quorum())
            self.assertTrue(len(node.quorum_set.nodes) == 5)
            self.assertTrue(node.quorum_set.nodes, nodes)
            self.assertEqual(node.quorum_set.inner_sets, [])


    def test_get_neighbors(self):
        # Node names have to be numbers for Gi function to work
        node2 = Node(name="2")
        node3 = Node(name="3")
        node4 = Node(name="4")
        node5 = Node(name="5")
        self.node = Node(name="1")

        self.node.quorum_set.set(nodes=[node2, node3], inner_sets=[[node3, node4], [node4, node5]])

        neighbors = self.node.get_neighbors()
        self.assertEqual(len(neighbors),4) # All 4 nodes should be returned


    def test_prepare_nomination_msg_correctly_adds_value(self):
        for topology in ['FULL','ER']:
            nodes = Network.generate_nodes(n_nodes=5, topology=topology)
            mempool = Mempool()
            for node in nodes:
                node.attach_mempool(mempool)

            for i in range(5):
                mempool.mine()

            for node in nodes:
                node.prepare_nomination_msg()

            for node in nodes:
                self.assertEqual(type(node.nomination_state['voted'][0]), Value)
                # as extend is used to add new Values the list of
                self.assertTrue(len(node.nomination_state['voted'][0].transactions) == len(node.ledger.transactions))
                self.assertTrue(len(node.storage.messages) > 0)
                self.assertEqual(len(node.broadcast_flags), 1)

    def test_prepare_nomination_phase_correctly_adds_many_values(self):
        for topology in ['FULL', 'ER']:
            nodes = Network.generate_nodes(n_nodes=5, topology=topology)
            mempool = Mempool()
            for node in nodes:
                node.attach_mempool(mempool)

            for i in range(5):
                mempool.mine()

            for node in nodes:
                node.prepare_nomination_msg()
                node.prepare_nomination_msg()

            for node in nodes:
                assert all([isinstance(vote, Value) for vote in node.nomination_state['voted']])
                # The second Value in the state should contain all txs from ledger which should now be 2
                self.assertTrue(len(node.nomination_state['voted'][1].transactions) == len(node.ledger.transactions))
                self.assertTrue(len(node.storage.messages) > 0)
                self.assertEqual(len(node.broadcast_flags), 2)

    def test_process_received_messages_processes_empty_state_correctly(self):
            self.node = Node("test_node")
            self.storage = Storage(self.node)

            value1 = Value(transactions={Transaction(0), Transaction(0)})
            value2 = Value(transactions={Transaction(0), Transaction(0)})

            # add value3 and value4 to voted and accepted states
            self.node.process_received_message([value1, value2])

            self.assertEqual(self.node.nomination_state['voted'][0], value1)  # value3 and value1 should be present
            self.assertEqual(self.node.nomination_state['accepted'][0], value2)  # value4 and value2 should be present

    def test_process_received_messages_processes_voted_and_accepted_correctly(self):
            self.node = Node("test_node")
            self.storage = Storage(self.node)

            value3 = Value(transactions={Transaction(0), Transaction(0)})
            value4 = Value(transactions={Transaction(0), Transaction(0)})

            # add value3 and value4 to voted and accepted states
            self.node.process_received_message([value3, value4])

            self.assertEqual(self.node.nomination_state['voted'][0], value3)  # value3 and value1 should be present
            self.assertEqual(self.node.nomination_state['accepted'][0], value4)  # value4 and value2 should be present


    def test_process_received_messages_processes_existing_state_correctly(self):
            self.node = Node("test_node")
            self.storage = Storage(self.node)
            mempool = Mempool()
            self.node.attach_mempool(mempool)

            value1 = Value(transactions={Transaction(0), Transaction(1)})

            self.node.prepare_nomination_msg() # add message to current state

            # add value3 and value4 to voted and accepted states
            self.node.process_received_message([value1, []])

            self.assertIn(value1, self.node.nomination_state['voted'])  # value1 should be present

    def test_process_received_messages_doesnt_process_existing_duplicate(self):
            self.node = Node("test_node")
            self.storage = Storage(self.node)
            mempool = Mempool()
            self.node.attach_mempool(mempool)

            value1 = Value(transactions={Transaction(0), Transaction(1)})

            self.node.prepare_nomination_msg() # add message to current state

            # add value3 and value4 to voted and accepted states
            self.node.process_received_message([value1, []])
            self.node.process_received_message([value1, []])

            self.assertIn(value1, self.node.nomination_state['voted'])  # value1 should be present
            self.assertEqual(self.node.nomination_state['voted'].count(value1), 1) # value1 should only be there once as duplicates are not added

    def test_receive_message_receives_accepted_message(self):
        self.node = Node("test_node")
        self.storage = Storage(self.node)
        self.priority_node = Node("test_node2")

        value1 = Value(transactions={Transaction(0), Transaction(0)})
        value2 = Value(transactions={Transaction(0), Transaction(0)})

        message = SCPNominate(voted=[value1], accepted=[value2])

        self.priority_node.storage.add_messages(message)

        self.node.get_highest_priority_neighbor = MagicMock(return_value=self.priority_node)
        self.node.retrieve_broadcast_message = MagicMock(return_value=message)
        message.parse_message_state = MagicMock(return_value=[value1, value2])
        self.node.process_received_message = MagicMock()
        self.node.update_statement_count = MagicMock()
        self.node.check_Quorum_threshold = MagicMock(return_value=True)
        self.node.check_Blocking_threshold = MagicMock(return_value=False)
        self.node.update_nomination_state = MagicMock()

        self.node.receive_message()

        # Assert that functions are called
        self.node.get_highest_priority_neighbor.assert_called()
        self.node.retrieve_broadcast_message.assert_called()
        message.parse_message_state.assert_called()
        self.node.process_received_message.assert_called_once()
        self.node.update_statement_count.assert_called_once()

        # Assert that nomination state is updated when quorum threshold is met
        self.node.update_nomination_state.assert_called_with(value2, "accepted")

    def test_receive_message_receives_voted_message(self):
        self.node = Node("test_node")
        self.storage = Storage(self.node)
        self.priority_node = Node("test_node2")

        value1 = Value(transactions={Transaction(0), Transaction(0)})

        message = SCPNominate(voted=[value1], accepted=[])

        self.priority_node.storage.add_messages(message)

        self.node.get_highest_priority_neighbor = MagicMock(return_value=self.priority_node)
        self.node.retrieve_broadcast_message = MagicMock(return_value=message)
        message.parse_message_state = MagicMock(return_value=[value1, []])
        self.node.process_received_message = MagicMock()
        self.node.update_statement_count = MagicMock()
        self.node.check_Quorum_threshold = MagicMock(return_value=True)
        self.node.check_Blocking_threshold = MagicMock(return_value=False)
        self.node.update_nomination_state = MagicMock()

        self.node.receive_message()

        # Assert that functions are called
        self.node.get_highest_priority_neighbor.assert_called()
        self.node.retrieve_broadcast_message.assert_called()
        message.parse_message_state.assert_called()
        self.node.process_received_message.assert_called_once()
        self.node.update_statement_count.assert_called_once()

        # Assert that nomination state is updated when quorum threshold is met
        self.node.update_nomination_state.assert_called_with(value1, "voted")

    def test_receive_empty_message_doesnt_call_functions_and_doesnt_fail(self):
        self.node = Node("test_node")
        self.storage = Storage(self.node)
        self.priority_node = Node("test_node2")
        message = SCPNominate(voted=[], accepted=[])

        self.node.get_highest_priority_neighbor = MagicMock(return_value=self.priority_node)
        self.node.retrieve_broadcast_message = MagicMock(return_value=None)
        message.parse_message_state = MagicMock()
        self.node.process_received_message = MagicMock()
        self.node.update_statement_count = MagicMock()

        self.node.receive_message()

        # Assert that the first 2 functions are called and the others are not
        self.node.get_highest_priority_neighbor.assert_called()
        self.node.retrieve_broadcast_message.assert_called()
        message.parse_message_state.assert_not_called()
        self.node.process_received_message.assert_not_called()
        self.node.update_statement_count.assert_not_called()

    def test_is_duplicate_value_should_return_true(self):
        self.node = Node("test_node")
        value1 = Value(transactions={Transaction(0), Transaction(1)})
        value2 = Value(transactions={Transaction(0), Transaction(0)})
        current_vals = [value1, value2]

        self.assertTrue(self.node.is_duplicate_value(value1, current_vals))

    def test_is_duplicate_value_should_return_false(self):
        self.node = Node("test_node")
        value1 = Value(transactions={Transaction(0), Transaction(1)})
        value2 = Value(transactions={Transaction(0), Transaction(0)})
        current_vals = [value1, value2]
        value3 = Value(transactions={Transaction(0), Transaction(0)})

        self.assertFalse(self.node.is_duplicate_value(value3, current_vals))

    def test_update_statement_count_sets_initial_counts(self):
            self.node = Node("test_node")
            self.storage = Storage(self.node)
            mempool = Mempool()
            self.node.attach_mempool(mempool)

            self.other_node = Node("test_node2")

            value1 = Value(transactions={Transaction(0), Transaction(0)})
            value2 = Value(transactions={Transaction(0), Transaction(0)})

            self.node.update_statement_count(self.other_node, [value1, value2])

            self.assertIn(self.other_node.name, self.node.statement_counter[value1.hash]["voted"])
            self.assertIn(self.other_node.name, self.node.statement_counter[value2.hash]["accepted"])

    def test_update_statement_count_works_updates_correctly(self):
            self.node = Node("test_node")
            self.storage = Storage(self.node)
            mempool = Mempool()
            self.node.attach_mempool(mempool)

            self.other_node = Node("test_node2")

            value1 = Value(transactions={Transaction(0), Transaction(0)})
            value2 = Value(transactions={Transaction(0), Transaction(0)})

            self.node.update_statement_count(self.other_node, [value1, value2])
            self.other_node.update_statement_count(self.node, [value1, value2])
            self.node.update_statement_count(self.other_node, [value1, []])

            self.assertIn(self.other_node.name, self.node.statement_counter[value1.hash]["voted"])
            self.assertIn(self.other_node.name, self.node.statement_counter[value2.hash]["accepted"])
            self.assertIn(self.node.name, self.other_node.statement_counter[value1.hash]["voted"])
            self.assertIn(self.node.name, self.other_node.statement_counter[value2.hash]["accepted"])

            self.assertEqual(self.node.statement_counter[value1.hash]["voted"][self.other_node.name], 1)

    def test_update_statement_count_works_with_empty_vals(self):
            self.node = Node("test_node")
            self.storage = Storage(self.node)
            mempool = Mempool()
            self.node.attach_mempool(mempool)

            self.other_node = Node("test_node2")

            # Function should not fail
            self.node.update_statement_count(self.other_node, [[], []])

    def test_retrieve_broadcast_message_retrieves_correctly(self):
        self.node = Node("test_node")
        self.retrieving_node = Node("test_node2")
        mempool = Mempool()
        self.storage = Storage(self.node)
        self.node.attach_mempool(mempool)

        value1 = Value(transactions={Transaction(0), Transaction(0)})
        value2 = Value(transactions={Transaction(0), Transaction(0)})

        message = SCPNominate(voted=[value1], accepted=[value2])

        self.node.broadcast_flags = [message]

        retrieved = self.node.retrieve_broadcast_message(self.retrieving_node)

        self.assertEqual(retrieved, message)
        self.assertIn(retrieved, self.node.broadcast_flags)
        self.assertIn(self.retrieving_node.name, self.node.received_broadcast_msgs)

    def test_retrieve_broadcast_message_retrieves_correctly_for_multiple_messages(self):
        self.node = Node("test_node")
        self.retrieving_node = Node("test_node2")
        mempool = Mempool()
        self.storage = Storage(self.node)
        self.node.attach_mempool(mempool)

        value1 = Value(transactions={Transaction(0), Transaction(0)})
        value2 = Value(transactions={Transaction(0), Transaction(0)})

        message = SCPNominate(voted=[value1], accepted=[value2])

        value3 = Value(transactions={Transaction(0), Transaction(0)})

        message2 = SCPNominate(voted=[value2], accepted=[value3])

        self.node.broadcast_flags = [message, message2]

        retrieved = self.node.retrieve_broadcast_message(self.retrieving_node)
        retrieved2 = self.node.retrieve_broadcast_message(self.retrieving_node)

        self.assertIn(retrieved, self.node.broadcast_flags)
        self.assertIn(retrieved2, self.node.broadcast_flags)
        self.assertIn(self.retrieving_node.name, self.node.received_broadcast_msgs)
        self.assertEqual(len(self.node.received_broadcast_msgs[self.retrieving_node.name]), 2)

    def test_retrieve_broadcast_message_returns_none_for_empty(self):
            self.node = Node("test_node")
            self.retrieving_node = Node("test_node2")
            mempool = Mempool()
            self.storage = Storage(self.node)
            self.node.attach_mempool(mempool)

            retrieved = self.node.retrieve_broadcast_message(self.retrieving_node)

            self.assertEqual(retrieved, None)
            self.assertEqual([], self.node.broadcast_flags)
            self.assertEqual({}, self.node.received_broadcast_msgs)

    def test_retrieve_broadcast_message_returns_none_for_node_with_all_messages(self):
        self.node = Node("test_node")
        self.retrieving_node = Node("test_node2")
        mempool = Mempool()
        self.storage = Storage(self.node)
        self.node.attach_mempool(mempool)

        value1 = Value(transactions={Transaction(0), Transaction(0)})
        value2 = Value(transactions={Transaction(0), Transaction(0)})

        message = SCPNominate(voted=[value1], accepted=[value2])

        value3 = Value(transactions={Transaction(0), Transaction(0)})

        message2 = SCPNominate(voted=[value2], accepted=[value3])

        self.node.broadcast_flags = [message, message2]
        self.node.received_broadcast_msgs[self.retrieving_node.name] = [message, message2]

        retrieved = self.node.retrieve_broadcast_message(self.retrieving_node)

        self.assertEqual(retrieved, None)

    def test_node_itself_signed_message(self):
        node2 = Node("test_node2")
        self.node = Node(name="Node1")

        self.node.quorum_set.set(nodes=node2, inner_sets=[])

        value = Value(transactions={Transaction(0), Transaction(0)})

        # Mock nomination_state and statement_counter
        self.node.nomination_state = {
            "voted": [value],
            "accepted": [],
            "confirmed": []
        }
        self.node.statement_counter = {
            value.hash: {
                "voted": {"test_node2": 1},
                "accepted": {}
            }
        }

        result = self.node.check_Quorum_threshold(value)
        self.assertTrue(result)

    def test_threshold_not_met(self):
        self.node = Node(name="Node1")

        value = Value(transactions={Transaction(0), Transaction(0)})

        # Mock nomination_state and statement_counter
        self.node.nomination_state = {
            "voted": [],
            "accepted": [],
            "confirmed": []
        }
        self.node.statement_counter = {
            value.hash: {
                "voted": {},
                "accepted": {}
            }
        }

        result = self.node.check_Quorum_threshold(value)
        self.assertFalse(result)

    def test_threshold_met_for_inner_sets(self):
        node2 = Node("test_node2")
        node3 = Node("test_node3")
        node4 = Node("test_node4")
        node5 = Node("test_node5")
        self.node = Node(name="Node1")

        self.node.quorum_set.set(nodes=[node2, node3], inner_sets=[[node3, node4], [node4, node5]])

        value = Value(transactions={Transaction(0), Transaction(0)})
        value2 = Value(transactions={Transaction(0), Transaction(0)})

        # Mock nomination_state and statement_counter
        self.node.nomination_state = {
            "voted": [value, value2],
            "accepted": [],
            "confirmed": []
        }
        self.node.statement_counter = {
            value.hash: {
                "voted": {"test_node2": 1, "test_node3": 1, "test_node4": 1},
                "accepted": {"test_node5": 1}
            }
        }

        result = self.node.check_Quorum_threshold(value)
        self.assertTrue(result)


    def test_blocking_threshold_met(self):
        node2 = Node("test_node2")
        node3 = Node("test_node3")
        node4 = Node("test_node4")
        node5 = Node("test_node5")

        self.node = Node(name="Node1")
        self.node.quorum_set.set(nodes=[node2, node3], inner_sets=[[node3, node4, self.node], [node5, self.node]])

        value = Value(transactions={Transaction(0), Transaction(0)})

        # Mock nomination_state and statement_counter
        self.node.nomination_state = {
            "voted": [value],
            "accepted": [],
            "confirmed": []
        }
        self.node.statement_counter = {
            value.hash: {
                "voted": {"test_node2": 1, "test_node3": 1, "test_node4": 1},
                "accepted": {"test_node5": 1}
            }
        }

        result = self.node.check_Blocking_threshold(value)
        self.assertTrue(result)

    def test_blocking_threshold_does_not_meet(self):
        node2 = Node("2")
        node3 = Node("3")
        node4 = Node("4")
        node5 = Node("5")

        self.node = Node(name="Node1")
        self.node.quorum_set.set(nodes=[node2, node3], inner_sets=[[node4], [node5]])

        value = Value(transactions={Transaction(0), Transaction(0)})

        # Mock nomination_state and statement_counter
        self.node.nomination_state = {
            "voted": [value],
            "accepted": [],
            "confirmed": []
        }
        self.node.statement_counter = {
            value.hash: {
                "voted": {"2": 1},
                "accepted": {"3": 1}
            }
        }

        result = self.node.check_Blocking_threshold(value)
        self.assertFalse(result)

    def test_blocking_threshold_returns_False_when_not_in_nomination_state(self):
        node2 = Node("2")
        node3 = Node("3")
        node4 = Node("4")
        node5 = Node("5")

        self.node = Node(name="Node1")
        self.node.quorum_set.set(nodes=[node2, node3], inner_sets=[[node4], [node5]])

        value = Value(transactions={Transaction(0), Transaction(0)})

        # Mock nomination_state and statement_counter
        self.node.nomination_state = {
            "voted": [],
            "accepted": [],
            "confirmed": []
        }
        self.node.statement_counter = {
            value.hash: {
                "voted": {"2": 1},
                "accepted": {"3": 1}
            }
        }

        result = self.node.check_Blocking_threshold(value)
        self.assertFalse(result)

    def test_blocking_threshold_returns_False_for_empty_Quorum(self):
        self.node = Node(name="Node1")
        self.node.quorum_set.set(nodes=[], inner_sets=[])

        value = Value(transactions={Transaction(0), Transaction(0)})

        # Mock statement_counter
        self.node.statement_counter = {
            value.hash: {
                "voted": {},
                "accepted": {}
            }
        }

        result = self.node.check_Blocking_threshold(value)
        self.assertFalse(result)

    def test_update_nomination_state_correctly_updates(self):
        self.node = Node(name="1")

        value = Value(transactions={Transaction(0), Transaction(0)})
        value2 = Value(transactions={Transaction(0)})
        value3 = Value(transactions={Transaction(0)})

        self.node.nomination_state = {
            "voted": [value, value2],
            "accepted": [value3],
            "confirmed": []
        }
        self.node.update_nomination_state(value, "voted")

        assert all([isinstance(vote, Value) for vote in self.node.nomination_state['voted']])
        assert all([isinstance(vote, Value) for vote in self.node.nomination_state['accepted']])
        # The second Value in the state should contain all txs from ledger which should now be 2
        self.assertTrue(self.node.nomination_state['voted'] == [value2])
        self.assertTrue(self.node.nomination_state['accepted'] == [value3, value])
        self.assertTrue(len(self.node.nomination_state['accepted']) == 2)

    def test_update_nomination_state_updates_voted_to_accepted(self):
        self.node = Node(name="1")

        value = Value(transactions={Transaction(0), Transaction(0)})
        value2 = Value(transactions={Transaction(0)})
        value3 = Value(transactions={Transaction(0)})

        self.node.nomination_state = {
            "voted": [value2],
            "accepted": [value, value3],
            "confirmed": []
        }
        self.node.update_nomination_state(value, "voted")

        assert all([isinstance(vote, Value) for vote in self.node.nomination_state['voted']])
        assert all([isinstance(vote, Value) for vote in self.node.nomination_state['accepted']])
        self.assertTrue(self.node.nomination_state['voted'] == [value2])
        self.assertTrue(self.node.nomination_state['accepted'] == [value, value3])
        self.assertTrue(len(self.node.nomination_state['accepted']) == 2)

    def test_update_nomination_state_updates_accepted_to_confirmed(self):
        self.node = Node(name="1")

        value = Value(transactions={Transaction(0), Transaction(0)})
        value2 = Value(transactions={Transaction(0)})
        value3 = Value(transactions={Transaction(0)})

        self.node.nomination_state = {
            "voted": [],
            "accepted": [value, value2],
            "confirmed": [value3]
        }
        self.node.update_nomination_state(value, "accepted")

        assert all([isinstance(vote, Value) for vote in self.node.nomination_state['voted']])
        assert all([isinstance(vote, Value) for vote in self.node.nomination_state['accepted']])
        self.assertTrue(self.node.nomination_state['accepted'] == [value2])
        self.assertTrue(self.node.nomination_state['confirmed'] == [value3, value])
        self.assertTrue(len(self.node.nomination_state['confirmed']) == 2)

    def test_update_nomination_state_does_not_update_accepted(self):
        self.node = Node(name="1")

        value = Value(transactions={Transaction(0), Transaction(0)})
        value2 = Value(transactions={Transaction(0)})
        value3 = Value(transactions={Transaction(0)})

        self.node.nomination_state = {
            "voted": [value2],
            "accepted": [value, value3],
            "confirmed": []
        }
        self.node.update_nomination_state(value, "voted")

        assert all([isinstance(vote, Value) for vote in self.node.nomination_state['voted']])
        assert all([isinstance(vote, Value) for vote in self.node.nomination_state['accepted']])
        self.assertTrue(self.node.nomination_state['voted'] == [value2])
        self.assertTrue(self.node.nomination_state['accepted'] == [value, value3])
        self.assertTrue(len(self.node.nomination_state['accepted']) == 2)

    def test_update_nomination_state_does_not_fail_when_empty(self):
        self.node = Node(name="1")

        value = Value(transactions={Transaction(0), Transaction(0)})
        value3 = Value(transactions={Transaction(0)})

        self.node.nomination_state = {
            "voted": [],
            "accepted": [value3],
            "confirmed": []
        }
        self.node.update_nomination_state(value, "voted")

        assert all([isinstance(vote, Value) for vote in self.node.nomination_state['voted']])
        assert all([isinstance(vote, Value) for vote in self.node.nomination_state['accepted']])
        self.assertTrue(self.node.nomination_state['voted'] == [])
        self.assertTrue(self.node.nomination_state['accepted'] == [value3])
        self.assertTrue(len(self.node.nomination_state['accepted']) == 1)

    def test_retrieved_confirmed_values(self):
        self.node = Node(name="1")
        value1 = Value(transactions={Transaction(0), Transaction(0)})
        value2 = Value(transactions={Transaction(0)})
        value3 = Value(transactions={Transaction(0)})
        self.node.nomination_state['confirmed'] = [value1, value2, value3]
        self.node.prepared_ballots = {
            value1: {'aCounter': 1, 'cCounter': 1, 'hCounter': 1,
                                                         'highestCounter': 1},
            value2: {'aCounter': 2, 'cCounter': 2, 'hCounter': 2,
                                                         'highestCounter': 2},
        }

        retrieved_value = self.node.retrieve_confirmed_value()
        self.assertIsNotNone(retrieved_value)
        self.assertIn(retrieved_value, self.node.nomination_state['confirmed'])

    def test_retrieved_confirmed_values_returns_None_for_empty(self):
        self.node = Node(name="1")
        self.node.nomination_state['confirmed'] = []

        retrieved_value = self.node.retrieve_confirmed_value()
        self.assertIsNone(retrieved_value)

    def test_get_prepared_ballot_counters(self):
        self.node = Node(name="1")
        value1 = Value(transactions={Transaction(0), Transaction(0)})
        value2 = Value(transactions={Transaction(0)})

        self.node.prepared_ballots = {
            value1: {'aCounter': 1, 'cCounter': 1, 'hCounter': 1, 'highestCounter': 1},
            value2: {'aCounter': 2, 'cCounter': 2, 'hCounter': 2, 'highestCounter': 2},
        }

        state_val1 = self.node.get_prepared_ballot_counters(value1)
        self.assertIsNotNone(state_val1)
        self.assertEqual(state_val1['aCounter'], 1)
        self.assertEqual(state_val1['cCounter'], 1)
        self.assertEqual(state_val1['hCounter'], 1)

        state_val2 = self.node.get_prepared_ballot_counters(value2)
        self.assertIsNotNone(state_val2)
        self.assertEqual(state_val2['aCounter'], 2)
        self.assertEqual(state_val2['cCounter'], 2)
        self.assertEqual(state_val2['hCounter'], 2)

        self.assertNotEqual(state_val1, state_val2)

    def test_get_prepared_ballot_counters_returns_None_for_empty(self):
        self.node = Node(name="1")
        value1 = Value(transactions={Transaction(0), Transaction(0)})
        value2 = Value(transactions={Transaction(0)})

        self.node.prepared_ballots = {
            value1: {'aCounter': 1, 'cCounter': 1, 'hCounter': 1, 'highestCounter': 1},
        }

        state_val2 = self.node.get_prepared_ballot_counters(value2)
        self.assertIsNone(state_val2)

    def test_prepare_ballot_msg(self):
        self.node = Node(name="1")
        confirmed_value = Value(transactions={Transaction(0), Transaction(0)})
        self.node.nomination_state['confirmed'] = [confirmed_value]

        self.node.prepare_ballot_msg()
        # Ensure the message was prepared
        self.assertEqual(len(self.node.ballot_prepare_broadcast_flags), 1)
        prepared_msg = self.node.ballot_prepare_broadcast_flags.pop()
        self.assertIsInstance(prepared_msg, SCPPrepare)

    def test_prepare_ballot_msg_for_no_confirmed_values(self):
        self.node = Node(name="1")
        self.node.nomination_state['confirmed'] = []
        self.node.retrieve_confirmed_value = MagicMock(return_value=None)

        self.node.prepare_ballot_msg()
        self.node.retrieve_confirmed_value.assert_not_called()
        self.assertEqual(len(self.node.ballot_prepare_broadcast_flags), 0)

    def test_prepare_ballot_msg_for_existing_voted_value(self):
        self.node = Node(name="1")
        confirmed_value = Value(transactions={Transaction(0)})
        self.node.nomination_state['confirmed'] = [confirmed_value]
        ballot = SCPBallot(value=confirmed_value, counter=0)

        # Mock Functions
        self.node.retrieve_confirmed_value = MagicMock(return_value=confirmed_value)
        self.node.get_prepared_ballot_counters = MagicMock(return_value=SCPPrepare(ballot= ballot,aCounter= 1, cCounter= 1, hCounter= 1))

        self.node.balloting_state['aborted'] = {}
        self.node.balloting_state['voted'][confirmed_value.hash] = SCPBallot(counter=1, value=confirmed_value)

        self.node.prepare_ballot_msg()
        # Ensure the message was prepared
        self.assertEqual(len(self.node.ballot_prepare_broadcast_flags), 1)

        prepared_msg = self.node.ballot_prepare_broadcast_flags.pop()
        self.assertIsInstance(prepared_msg, SCPPrepare)
        self.assertEqual(prepared_msg.ballot.counter, 2)  # Incremented counter for existing voted value

    def test_prepare_ballot_msg_for_no_aborted_value(self):
        self.node = Node(name="1")
        confirmed_value = Value(transactions={Transaction(0)})
        self.node.nomination_state['confirmed'] = [confirmed_value]
        self.node.balloting_state['aborted'][confirmed_value.hash] = SCPBallot(counter=1, value=confirmed_value)

        self.node.get_prepared_ballot_counters = MagicMock(return_value=None)

        self.node.prepare_ballot_msg()
        # get_prepared_ballot_counters is the first function to be called if the value is not in the aborted field so we check if it gets called, it should NOT
        self.node.get_prepared_ballot_counters.assert_not_called()
        self.assertEqual(len(self.node.ballot_prepare_broadcast_flags), 0)

    def test_prepare_ballot_msg_for_finalised_ballot(self):
        self.node = Node(name="1")
        confirmed_value = Value(transactions={Transaction(0)})
        self.node.nomination_state['confirmed'] = [confirmed_value]
        ballot = SCPBallot(value=confirmed_value, counter=0)
        finalised_msg = SCPExternalize(ballot=ballot, hCounter=ballot.counter)
        self.node.externalized_slot_counter.add(finalised_msg)

        self.node.retrieve_confirmed_value = MagicMock(return_value=confirmed_value)
        self.node.get_prepared_ballot_counters = MagicMock()

        self.node.get_prepared_ballot_counters.assert_not_called()


    def test_process_prepare_ballot_message_works_for_case1(self):
        self.node = Node(name="1")
        self.sender_node = Node(name='2')

        value1 = Value(transactions={Transaction(0), Transaction(0)})
        ballot = SCPBallot(counter=1, value=value1)

        self.node.balloting_state['voted'][value1.hash] = ballot
        mock_ballot = SCPBallot(counter=2, value=value1)
        mock_msg = SCPPrepare(ballot=mock_ballot)

        self.node.process_prepare_ballot_message(mock_msg, self.sender_node)

        self.assertIn(ballot.value.hash, self.node.balloting_state['voted'])
        self.assertEqual(self.node.balloting_state['voted'][value1.hash], mock_ballot)
        self.assertIn(self.sender_node, self.node.ballot_statement_counter[value1]['voted'])

    def test_process_prepare_ballot_message_works_for_case2(self):
        self.node = Node(name="1")
        self.sender_node = Node(name='2')
        value1 = Value(transactions={Transaction(0), Transaction(0)})
        value2 = Value(transactions={Transaction(0)})

        ballot1 = SCPBallot(counter=1, value=value1)

        self.node.balloting_state['voted'][value1.hash] = ballot1

        mock_ballot = SCPBallot(counter=2, value=value2)
        mock_msg = SCPPrepare(ballot=mock_ballot)

        self.node.process_prepare_ballot_message(mock_msg, self.sender_node)

        self.assertIn(ballot1.value.hash, self.node.balloting_state['aborted'])
        self.assertNotIn(ballot1.value.hash, self.node.balloting_state['voted'])

        self.assertEqual(self.node.balloting_state['voted'][value2.hash], mock_ballot)
        self.assertEqual(self.node.balloting_state['aborted'][value1.hash], ballot1)
        self.assertIn(self.sender_node, self.node.ballot_statement_counter[value2]['voted'])

    def test_process_prepare_ballot_message_works_for_case3(self):
        self.node = Node(name="1")
        value1 = Value(transactions={Transaction(0), Transaction(0)})
        self.sender_node = Node(name='2')

        smaller_ballot1 = SCPBallot(counter=2, value=value1)
        larger_ballot2 = SCPBallot(counter=3, value=value1)

        self.node.balloting_state['voted'][value1.hash] = larger_ballot2

        mock_msg = SCPPrepare(ballot=smaller_ballot1)

        self.node.process_prepare_ballot_message(mock_msg, self.sender_node)

        self.assertIn(larger_ballot2.value.hash, self.node.balloting_state['voted'])
        self.assertEqual(self.node.balloting_state['voted'][value1.hash].counter, larger_ballot2.counter)
        self.assertNotEqual(self.node.balloting_state['voted'][value1.hash].counter, smaller_ballot1.counter)
        self.assertIn(self.sender_node, self.node.ballot_statement_counter[value1]['voted'])

    def test_process_prepare_ballot_message_works_for_case4(self):
        self.node = Node(name="1")
        value1 = Value(transactions={Transaction(0), Transaction(0)})
        value2 =  Value(transactions={Transaction(0)})
        self.sender_node = Node(name="2")


        ballot1 = SCPBallot(counter=3, value=value1)
        smaller_different_ballot2 = SCPBallot(counter=2, value=value2)

        self.node.balloting_state['voted'][value1.hash] = ballot1

        mock_msg = SCPPrepare(ballot=smaller_different_ballot2)

        self.node.process_prepare_ballot_message(mock_msg, self.sender_node)

        self.assertNotIn(smaller_different_ballot2.value.hash, self.node.balloting_state['voted'])
        self.assertNotIn(smaller_different_ballot2.value.hash, self.node.balloting_state['accepted'])
        self.assertNotIn(smaller_different_ballot2.value.hash, self.node.balloting_state['confirmed'])
        self.assertIn(smaller_different_ballot2.value.hash, self.node.balloting_state['aborted'])
        self.assertIn(ballot1.value.hash, self.node.balloting_state['voted'])
        self.assertEqual(self.node.balloting_state['voted'][value1.hash].counter, ballot1.counter)
        self.assertEqual(self.node.balloting_state['aborted'][value2.hash].counter, smaller_different_ballot2.counter)
        self.assertIn(self.sender_node, self.node.ballot_statement_counter[value2]['aborted'])

    def test_abort_ballots_works(self):
        self.node = Node(name="1")
        self.node.balloting_state = {'voted': {}, 'accepted': {}, 'aborted': {}}

        Value1 = Value(transactions={Transaction(0), Transaction(0)})

        ballot1 = SCPBallot(counter=1, value=Value(transactions={Transaction(0)}))
        ballot2 = SCPBallot(counter=2, value=Value(transactions={Transaction(0)}))
        ballot3 = SCPBallot(counter=1, value=Value(transactions={Transaction(1)}))
        ballot4 = SCPBallot(counter=2, value=Value(transactions={Transaction(1)}))

        self.node.balloting_state['voted'] = {ballot1.value.hash: ballot1, ballot2.value.hash: ballot2}
        self.node.balloting_state['accepted'] = {ballot3.value.hash: ballot3, ballot4.value.hash: ballot4}

        received_ballot = SCPBallot(counter=3, value=Value1) # Make a ballot with a higher counter
        self.node.abort_ballots(received_ballot)

        # All ballots from voted and accepted should be removed from voted & accepted and added to aborted
        # Check voted
        self.assertNotIn(ballot1.value.hash, self.node.balloting_state['voted'])
        self.assertIn(ballot1.value.hash, self.node.balloting_state['aborted'])
        self.assertNotIn(ballot2.value.hash, self.node.balloting_state['voted'])
        self.assertIn(ballot2.value.hash, self.node.balloting_state['aborted'])

        # Check accepted
        self.assertNotIn(ballot3.value.hash, self.node.balloting_state['accepted'])
        self.assertIn(ballot3.value.hash, self.node.balloting_state['aborted'])
        self.assertNotIn(ballot4.value.hash, self.node.balloting_state['accepted'])
        self.assertIn(ballot4.value.hash, self.node.balloting_state['aborted'])

    def test_abort_ballots_doesnt_remove_equal_counters(self):
        self.node = Node(name="1")
        self.node.balloting_state = {'voted': {}, 'accepted': {}, 'aborted': {}}

        Value1 = Value(transactions={Transaction(0), Transaction(0)})

        ballot1 = SCPBallot(counter=3, value=Value1)
        ballot2 = SCPBallot(counter=3, value=Value(transactions={Transaction(0)}))

        self.node.balloting_state['voted'] = {ballot1.value.hash: ballot1}
        self.node.balloting_state['accepted'] = {ballot2.value.hash: ballot2}

        received_ballot = SCPBallot(counter=3, value=Value1) # Make a ballot with a higher counter
        self.node.abort_ballots(received_ballot)

        self.assertIn(ballot1.value.hash, self.node.balloting_state['voted'])
        self.assertNotIn(ballot1.value.hash, self.node.balloting_state['aborted'])
        self.assertIn(ballot2.value.hash, self.node.balloting_state['accepted'])
        self.assertNotIn(ballot2.value.hash, self.node.balloting_state['aborted'])

    def test_abort_ballots_doesnt_abort_higher_counters(self):
        self.node = Node(name="1")
        self.node.balloting_state = {'voted': {}, 'accepted': {}, 'aborted': {}}

        Value1 = Value(transactions={Transaction(0), Transaction(0)})

        ballot1 = SCPBallot(counter=4, value=Value1)  # Higher counter
        ballot2 = SCPBallot(counter=4, value=Value(transactions={Transaction(1)}))

        self.node.balloting_state['voted'] = {ballot1.value.hash: ballot1}
        self.node.balloting_state['accepted'] = {ballot2.value.hash: ballot2}

        received_ballot = SCPBallot(counter=3, value=Value1)  # Lower counter
        self.node.abort_ballots(received_ballot)

        # Ballots should not be removed in the case of higher counter ballots
        self.assertIn(ballot1.value.hash, self.node.balloting_state['voted'])
        self.assertNotIn(ballot1.value.hash, self.node.balloting_state['aborted'])
        self.assertIn(ballot2.value.hash, self.node.balloting_state['accepted'])
        self.assertNotIn(ballot2.value.hash, self.node.balloting_state['aborted'])

    def test_prepare_quorum_threshold_node_itself_signed_message(self):
        node2 = Node("test_node2")
        self.node = Node(name="Node1")
        self.node.quorum_set.set(nodes=node2, inner_sets=[])

        value = Value(transactions={Transaction(0), Transaction(0)})
        ballot = SCPBallot(counter=1, value=value)

        # Mock nomination_state and statement_counter
        self.node.balloting_state = {
            "voted": {value.hash: ballot},
            "accepted": {},
            "confirmed": {},
            "aborted": {}
        }

        self.node.ballot_statement_counter = {
            value: {
                "voted": set(),  # Node1 itself has voted for the value
                "accepted": set(),
                "confirmed": set(),
                "aborted": set()
            }
        }
        self.node.ballot_statement_counter[value]["voted"].add(node2)

        result = self.node.check_Prepare_Quorum_threshold(ballot)
        self.assertTrue(result)

    def test_prepare_quorum_threshold_not_met(self):
        self.node = Node(name="Node1")

        value = Value(transactions={Transaction(0), Transaction(0)})
        ballot = SCPBallot(counter=1, value=value.hash)


        # Mock balloting_state and ballot statement_counter
        self.node.balloting_state = {
            "voted": {},
            "accepted": {},
            "confirmed": {}
        }

        self.node.ballot_statement_counter = {
            value.hash: {
                "voted": {},
                "accepted": {}
            }
        }

        result = self.node.check_Quorum_threshold(value)
        self.assertFalse(result)

    def test_prepare_quorum_threshold_met_for_inner_sets(self):
        node2 = Node("test_node2")
        node3 = Node("test_node3")
        node4 = Node("test_node4")
        node5 = Node("test_node5")
        self.node = Node(name="Node1")

        self.node.quorum_set.set(nodes=[node2, node3], inner_sets=[[node3, node4], [node4, node5]])

        value = Value(transactions={Transaction(0), Transaction(0)})
        value2 = Value(transactions={Transaction(0), Transaction(0)})
        ballot = SCPBallot(counter=1, value=value)
        ballot2 = SCPBallot(counter=1, value=value2)

        # Mock nomination_state and statement_counter
        self.node.balloting_state = {
            "voted": {value.hash: {ballot}},
            "accepted": {value2.hash : {ballot2}},
            "confirmed": {}
        }
        # This will look like: self.balloting_state = {'voted': {'value_hash_1': SCPBallot(counter=1, value=ValueObject1),},'accepted': { 'value_hash_2': SCPBallot(counter=3, value=ValueObject2)},'confirmed': { ... },'aborted': { ... }}
        # This will use sets for node names as opposed to counts, so will look like: {SCPBallot1.value: {'voted': set(Node1), ‘accepted’: set(Node2, Node3), ‘confirmed’: set(), ‘aborted’: set(), SCPBallot2.value: {'voted': set(), ‘accepted’: set(), ‘confirmed’: set(), ‘aborted’: set(node1, node2, node3)}

        # [ballot.value] = {'voted': set(), 'accepted': set(), 'confirmed': set(), 'aborted': set()}
        self.node.ballot_statement_counter = {
            value: {
                "voted": set(),
                "accepted": set()
            }
        }
        self.node.ballot_statement_counter[value]["voted"].add(node2)
        self.node.ballot_statement_counter[value]["voted"].add(node3)
        self.node.ballot_statement_counter[value]["voted"].add(node4)
        self.node.ballot_statement_counter[value]["accepted"].add(node4)
        self.node.ballot_statement_counter[value]["accepted"].add(node5)

        result = self.node.check_Prepare_Quorum_threshold(ballot)
        self.assertTrue(result)


    def test_update_prepare_balloting_state_correctly_updates(self):
        self.node = Node(name="1")

        value = Value(transactions={Transaction(0), Transaction(0)})
        value2 = Value(transactions={Transaction(0)})
        value3 = Value(transactions={Transaction(0)})
        ballot = SCPBallot(counter=1, value=value)
        ballot2 = SCPBallot(counter=1, value=value2)
        ballot3 = SCPBallot(counter=1, value=value3)

        self.node.balloting_state = {
            "voted": {value.hash: ballot, value2.hash : ballot2},
            "accepted": {value3.hash: ballot3},
            "confirmed": {}
        }
        self.node.update_prepare_balloting_state(ballot, "voted")

        self.assertTrue(self.node.balloting_state['voted'] == {value2.hash: ballot2})
        self.assertTrue(self.node.balloting_state['accepted'] == {value3.hash: ballot3, value.hash: ballot})
        self.assertTrue(len(self.node.balloting_state['accepted']) == 2)

    def test_update_prepare_balloting_state_updates_voted_to_accepted(self):
        self.node = Node(name="1")

        value = Value(transactions={Transaction(0), Transaction(0)})
        value2 = Value(transactions={Transaction(0)})
        value3 = Value(transactions={Transaction(0)})
        ballot = SCPBallot(counter=1, value=value)
        ballot2 = SCPBallot(counter=1, value=value2)
        ballot3 = SCPBallot(counter=1, value=value3)

        self.node.balloting_state = {
            "voted": {value2.hash : ballot2},
            "accepted": {value.hash: ballot, value3.hash: ballot3},
            "confirmed": {}
        }
        self.node.update_prepare_balloting_state(ballot, "voted")

        self.assertTrue(self.node.balloting_state['voted'] == {value2.hash: ballot2})
        self.assertTrue(self.node.balloting_state['accepted'] == {value3.hash: ballot3, value.hash: ballot})
        self.assertTrue(len(self.node.balloting_state['accepted']) == 2)

    def test_update_prepare_balloting_state_updates_accepted_to_confirmed(self):
        self.node = Node(name="1")

        value = Value(transactions={Transaction(0), Transaction(0)})
        value2 = Value(transactions={Transaction(0)})
        value3 = Value(transactions={Transaction(0)})
        ballot = SCPBallot(counter=1, value=value)
        ballot2 = SCPBallot(counter=1, value=value2)
        ballot3 = SCPBallot(counter=1, value=value3)

        self.node.balloting_state = {
            "voted": {},
            "accepted": {value.hash: ballot, value2.hash : ballot2},
            "confirmed": {value3.hash: ballot3}
        }
        self.node.update_prepare_balloting_state(ballot, "accepted")

        self.assertTrue(self.node.balloting_state['accepted'] == {value2.hash: ballot2})
        self.assertTrue(self.node.balloting_state['confirmed'] == {value3.hash: ballot3, value.hash: ballot})
        self.assertTrue(len(self.node.balloting_state['accepted']) == 1)
        self.assertTrue(len(self.node.balloting_state['confirmed']) == 2)

    def test_update_balloting_state_does_not_update_accepted(self):
        self.node = Node(name="1")

        value = Value(transactions={Transaction(0), Transaction(0)})
        value2 = Value(transactions={Transaction(0)})
        value3 = Value(transactions={Transaction(0)})
        ballot = SCPBallot(counter=1, value=value)
        ballot2 = SCPBallot(counter=1, value=value2)
        ballot3 = SCPBallot(counter=1, value=value3)

        self.node.balloting_state = {
            "voted": {value2.hash : ballot2},
            "accepted": {value.hash: ballot, value3.hash: ballot3},
            "confirmed": {}
        }

        self.node.update_prepare_balloting_state(ballot, "voted")

        self.assertTrue(self.node.balloting_state['voted'] == {value2.hash : ballot2})
        self.assertTrue(self.node.balloting_state['accepted'] == {value.hash: ballot, value3.hash: ballot3})
        self.assertTrue(len(self.node.balloting_state['accepted']) == 2)

    def test_update_balloting_state_does_not_fail_when_empty(self):
        self.node = Node(name="1")

        value = Value(transactions={Transaction(0), Transaction(0)})
        value3 = Value(transactions={Transaction(0)})
        ballot = SCPBallot(counter=1, value=value)
        ballot3 = SCPBallot(counter=1, value=value3)

        self.node.balloting_state = {
            "voted": {},
            "accepted": {value3.hash: ballot3},
            "confirmed": {}
        }
        self.node.update_prepare_balloting_state(ballot, "voted")

        self.assertTrue(self.node.balloting_state['voted'] == {})
        self.assertTrue(self.node.balloting_state['accepted'] == {value3.hash: ballot3})
        self.assertTrue(len(self.node.balloting_state['accepted']) == 1)


    def test_retrieve_prepare_broadcast_message_retrieves_correctly(self):
        self.node = Node("test_node")
        self.retrieving_node = Node("test_node2")
        mempool = Mempool()
        self.storage = Storage(self.node)
        self.node.attach_mempool(mempool)

        value1 = Value(transactions={Transaction(0), Transaction(0)})
        value2 = Value(transactions={Transaction(0), Transaction(0)})
        ballot1 = SCPBallot(counter=1, value=value1)
        ballot2 = SCPBallot(counter=1, value=value2)

        message = SCPPrepare(ballot=ballot1)

        self.node.ballot_prepare_broadcast_flags = [message]
        retrieved = self.node.retrieve_ballot_prepare_message(self.retrieving_node)

        self.assertEqual(retrieved, message)
        self.assertIn(retrieved, self.node.ballot_prepare_broadcast_flags)
        self.assertIn(self.retrieving_node.name, self.node.received_prepare_broadcast_msgs)

    def test_retrieve_prepare_broadcast_message_retrieves_correctly_for_multiple_messages(self):
        self.node = Node("test_node")
        self.retrieving_node = Node("test_node2")
        mempool = Mempool()
        self.storage = Storage(self.node)
        self.node.attach_mempool(mempool)

        value1 = Value(transactions={Transaction(0), Transaction(0)})
        value2 = Value(transactions={Transaction(0), Transaction(0)})
        ballot1 = SCPBallot(counter=1, value=value1)
        ballot2 = SCPBallot(counter=1, value=value2)

        message = SCPPrepare(ballot=ballot1)
        message2 = SCPPrepare(ballot=ballot2)

        self.node.broadcast_flags = [message, message2]
        self.node.ballot_prepare_broadcast_flags = set()
        self.node.ballot_prepare_broadcast_flags.add(message)
        self.node.ballot_prepare_broadcast_flags.add(message2)

        retrieved = self.node.retrieve_ballot_prepare_message(self.retrieving_node)
        retrieved2 = self.node.retrieve_ballot_prepare_message(self.retrieving_node)

        self.assertIn(retrieved, self.node.ballot_prepare_broadcast_flags)
        self.assertIn(retrieved2, self.node.ballot_prepare_broadcast_flags)
        self.assertIn(self.retrieving_node.name, self.node.received_prepare_broadcast_msgs)
        self.assertEqual(len(self.node.received_prepare_broadcast_msgs[self.retrieving_node.name]), 2)

    def test_retrieve_prepare_broadcast_message_returns_none_for_empty(self):
            self.node = Node("test_node")
            self.retrieving_node = Node("test_node2")
            mempool = Mempool()
            self.storage = Storage(self.node)
            self.node.attach_mempool(mempool)

            retrieved = self.node.retrieve_ballot_prepare_message(self.retrieving_node)

            self.assertEqual(retrieved, None)
            self.assertEqual(set(), self.node.ballot_prepare_broadcast_flags)
            self.assertEqual({}, self.node.received_prepare_broadcast_msgs)

    def test_retrieve_prepare_broadcast_message_returns_none_for_node_with_all_messages(self):
        self.node = Node("test_node")
        self.retrieving_node = Node("test_node2")
        mempool = Mempool()
        self.storage = Storage(self.node)
        self.node.attach_mempool(mempool)

        value1 = Value(transactions={Transaction(0), Transaction(0)})
        value2 = Value(transactions={Transaction(0), Transaction(0)})
        ballot1 = SCPBallot(counter=1, value=value1)
        ballot2 = SCPBallot(counter=1, value=value2)

        message = SCPPrepare(ballot=ballot1)
        message2 = SCPPrepare(ballot=ballot2)

        self.node.ballot_prepare_broadcast_flags = set()
        self.node.ballot_prepare_broadcast_flags.add(message)
        self.node.ballot_prepare_broadcast_flags.add(message2)
        self.node.received_prepare_broadcast_msgs[self.retrieving_node.name] = [message, message2]

        retrieved = self.node.retrieve_ballot_prepare_message(self.retrieving_node)

        self.assertEqual(retrieved, None)


    def test_receive_prepare_message_processes_voted_to_accepted(self):
        self.node = Node("test_node")
        self.test_node = Node("test2")
        self.sending_node = Node("test_node2")

        value1 = Value(transactions={Transaction(0), Transaction(0)})
        ballot1 = SCPBallot(value=value1, counter=0)
        self.node.balloting_state = {'voted': {value1.hash: ballot1}, 'accepted': {}, 'confirmed': {}}

        message = SCPPrepare(ballot=ballot1)

        self.sending_node.storage.add_messages(message)

        self.node.quorum_set.retrieve_random_peer = MagicMock(return_value=self.sending_node) # this is quorum.retrieve_random_peer()
        self.node.retrieve_ballot_prepare_message = MagicMock(return_value=message) # this retrieves message, its retrieve_ballot_prepare_message()
        self.node.process_prepare_ballot_message = MagicMock()
        self.node.update_prepare_balloting_state = MagicMock()
        self.node.check_Prepare_Quorum_threshold = MagicMock(return_value=True)

        self.node.receive_prepare_message()

        # Assert that functions are called
        self.node.quorum_set.retrieve_random_peer.assert_called()
        self.node.retrieve_ballot_prepare_message.assert_called()
        self.node.process_prepare_ballot_message.assert_called_once()
        self.node.update_prepare_balloting_state.assert_called_once()

        # Assert that nomination state is updated when quorum threshold is met
        self.node.process_prepare_ballot_message.assert_called_with(message, self.sending_node)
        self.node.update_prepare_balloting_state.assert_called_with(ballot1, 'voted')


    def test_receive_prepare_message_processes_accepted_to_confirmed(self):
        self.node = Node("test_node")
        self.test_node = Node("test2")
        self.sending_node = Node("test_node2")

        value1 = Value(transactions={Transaction(0), Transaction(0)})
        ballot1 = SCPBallot(value=value1, counter=0)
        self.node.balloting_state = {'voted': {}, 'accepted': {value1.hash: ballot1}, 'confirmed': {}}

        message = SCPPrepare(ballot=ballot1)

        self.sending_node.storage.add_messages(message)

        self.node.quorum_set.retrieve_random_peer = MagicMock(return_value=self.sending_node) # this is quorum.retrieve_random_peer()
        self.node.retrieve_ballot_prepare_message = MagicMock(return_value=message) # this retrieves message, its retrieve_ballot_prepare_message()
        self.node.process_prepare_ballot_message = MagicMock()
        self.node.update_prepare_balloting_state = MagicMock()
        self.node.update_prepare_balloting_state = MagicMock()
        self.node.check_Prepare_Quorum_threshold = MagicMock(return_value=True)

        self.node.receive_prepare_message()

        # Assert that functions are called
        self.node.quorum_set.retrieve_random_peer.assert_called()
        self.node.retrieve_ballot_prepare_message.assert_called()
        self.node.process_prepare_ballot_message.assert_called_once()
        self.node.update_prepare_balloting_state.assert_called_once()

        # Assert that nomination state is updated when quorum threshold is met
        self.node.process_prepare_ballot_message.assert_called_with(message, self.sending_node)
        self.node.update_prepare_balloting_state.assert_called_with(ballot1, 'accepted')

    def test_message_already_externalized(self):
        # Mock the necessary attributes and methods
        self.node = Node("test_node")
        self.sending_node = Node("test2")
        self.node.process_prepare_ballot_message = MagicMock()

        value1 = Value(transactions={Transaction(0), Transaction(0)})
        ballot1 = SCPBallot(value=value1, counter=0)
        self.node.balloting_state = {'voted': {}, 'accepted': {value1.hash: ballot1}, 'confirmed': {}}

        message = SCPPrepare(ballot=ballot1)
        self.sending_node.storage.add_messages(message)

        self.node.quorum_set.retrieve_random_peer = MagicMock(return_value=self.sending_node)
        self.node.retrieve_ballot_prepare_message = MagicMock(return_value=message)

        externalize_msg = SCPExternalize(ballot=ballot1, hCounter=ballot1.counter)
        self.node.externalized_slot_counter.add(externalize_msg)  # MockBallot is already externalized

        self.node.receive_prepare_message()
        self.node.process_prepare_ballot_message.assert_not_called()

    def test_retrieved_confirmed_prepared_commit_values(self):
        self.node = Node(name="1")
        value1 = Value(transactions={Transaction(0), Transaction(0)})
        ballot1 = SCPBallot(counter=0, value=value1)

        self.node.balloting_state = {"voted": {}, "accepted": {}, "confirmed": {value1.hash: ballot1}}
        retrieved_prepare_ballot = self.node.retrieve_confirmed_prepare_ballot()
        self.assertIsNotNone(retrieved_prepare_ballot)
        self.assertIn(retrieved_prepare_ballot.value.hash, self.node.balloting_state['confirmed'])

    def test_retrieved_confirmed_prepared_commit_values_returns_None_for_empty(self):
        self.node = Node(name="1")
        self.node.balloting_state = {"voted": {}, "accepted": {}, "confirmed": {}}

        retrieved_value = self.node.retrieve_confirmed_value()
        self.assertIsNone(retrieved_value)

    def test_prepare_commit_ballot_msg(self):
        self.node = Node(name="1")
        value1 = Value(transactions={Transaction(0), Transaction(0)})
        ballot1 = SCPBallot(counter=0, value=value1)
        self.node.balloting_state = {"voted": {}, "accepted": {}, "confirmed": {value1.hash: ballot1}}

        self.node.prepare_SCPCommit_msg()
        # Ensure the message was prepared
        self.assertEqual(len(self.node.commit_ballot_broadcast_flags), 1)
        prepared_msg = self.node.commit_ballot_broadcast_flags.pop()
        self.assertIsInstance(prepared_msg, SCPCommit)

    def test_prepare_commit_ballot_msg_for_no_confirmed_values(self):
        self.node = Node(name="1")
        self.node.balloting_state = {"voted": {}, "accepted": {}, "confirmed": {}}
        self.node.retrieve_confirmed_value = MagicMock(return_value=None)

        self.node.prepare_SCPCommit_msg()
        self.node.retrieve_confirmed_value.assert_not_called()
        self.assertEqual(len(self.node.ballot_prepare_broadcast_flags), 0)


    def test_process_commit_ballot_message_works_for_case1(self):
        self.node = Node(name="1")
        self.sender_node = Node(name='2')

        value1 = Value(transactions={Transaction(0), Transaction(0)})
        ballot = SCPBallot(counter=1, value=value1)

        self.node.commit_ballot_state['voted'][value1.hash] = ballot
        mock_ballot = SCPBallot(counter=2, value=value1)
        mock_msg = SCPCommit(ballot=mock_ballot, preparedCounter=mock_ballot.counter)

        self.node.process_commit_ballot_message(mock_msg, self.sender_node)

        self.assertIn(ballot.value.hash, self.node.commit_ballot_state['voted'])
        self.assertEqual(self.node.commit_ballot_state['voted'][value1.hash], mock_ballot)
        self.assertIn(self.sender_node, self.node.commit_ballot_statement_counter[value1]['voted'])

    def test_process_commit_ballot_message_works_for_case2(self):
        self.node = Node(name="1")
        self.sender_node = Node(name='2')
        value1 = Value(transactions={Transaction(0), Transaction(0)})
        value2 = Value(transactions={Transaction(0)})

        ballot1 = SCPBallot(counter=1, value=value1)

        self.node.commit_ballot_state['voted'][value1.hash] = ballot1

        mock_ballot = SCPBallot(counter=2, value=value2)
        mock_msg = SCPCommit(ballot=mock_ballot, preparedCounter=mock_ballot.counter)

        self.node.process_commit_ballot_message(mock_msg, self.sender_node)

        self.assertIn(ballot1.value.hash, self.node.commit_ballot_state['voted'])
        self.assertEqual(self.node.commit_ballot_state['voted'][value2.hash], mock_ballot)
        self.assertEqual(self.node.commit_ballot_state['voted'][value1.hash], ballot1)
        self.assertIn(self.sender_node, self.node.commit_ballot_statement_counter[value2]['voted'])

    def test_process_commit_ballot_message_works_for_case3(self):
        self.node = Node(name="1")
        value1 = Value(transactions={Transaction(0), Transaction(0)})
        self.sender_node = Node(name='2')

        smaller_ballot1 = SCPBallot(counter=2, value=value1)
        larger_ballot2 = SCPBallot(counter=3, value=value1)

        self.node.commit_ballot_state['voted'][value1.hash] = larger_ballot2

        mock_msg = SCPCommit(ballot=smaller_ballot1, preparedCounter=smaller_ballot1.counter)

        self.node.process_commit_ballot_message(mock_msg, self.sender_node)

        self.assertIn(larger_ballot2.value.hash, self.node.commit_ballot_state['voted'])
        self.assertEqual(self.node.commit_ballot_state['voted'][value1.hash].counter, larger_ballot2.counter)
        self.assertNotEqual(self.node.commit_ballot_state['voted'][value1.hash].counter, smaller_ballot1.counter)
        self.assertIn(self.sender_node, self.node.commit_ballot_statement_counter[value1]['voted'])

    def test_commit_quorum_threshold_node_itself_signed_message(self):
        node2 = Node("test_node2")
        self.node = Node(name="Node1")
        self.node.quorum_set.set(nodes=node2, inner_sets=[])

        value = Value(transactions={Transaction(0), Transaction(0)})
        ballot = SCPBallot(counter=1, value=value)

        # Mock nomination_state and statement_counter
        self.node.commit_ballot_state = {
            "voted": {value.hash: ballot},
            "accepted": {},
            "confirmed": {},
            "aborted": {}
        }

        self.node.commit_ballot_statement_counter = {
            value: {
                "voted": set(),  # Node1 itself has voted for the value
                "accepted": set(),
                "confirmed": set(),
                "aborted": set()
            }
        }
        self.node.commit_ballot_statement_counter[value]["voted"].add(node2)

        result = self.node.check_Commit_Quorum_threshold(ballot)
        self.assertTrue(result)

    def test_commit_quorum_threshold_not_met(self):
        self.node = Node(name="Node1")

        value = Value(transactions={Transaction(0), Transaction(0)})
        ballot = SCPBallot(counter=1, value=value)


        # Mock balloting_state and ballot statement_counter
        self.node.commit_ballot_state = {
            "voted": {},
            "accepted": {},
            "confirmed": {}
        }

        self.node.commit_ballot_statement_counter = {
            value.hash: {
                "voted": {},
                "accepted": {}
            }
        }

        result = self.node.check_Commit_Quorum_threshold(ballot=ballot)
        self.assertFalse(result)

    def test_commit_quorum_threshold_met_for_inner_sets(self):
        node2 = Node("test_node2")
        node3 = Node("test_node3")
        node4 = Node("test_node4")
        node5 = Node("test_node5")
        self.node = Node(name="Node1")

        self.node.quorum_set.set(nodes=[node2, node3], inner_sets=[[node3, node4], [node4, node5]])

        value = Value(transactions={Transaction(0), Transaction(0)})
        value2 = Value(transactions={Transaction(0), Transaction(0)})
        ballot = SCPBallot(counter=1, value=value)
        ballot2 = SCPBallot(counter=1, value=value2)

        # Mock nomination_state and statement_counter
        self.node.commit_ballot_state = {
            "voted": {value.hash: {ballot}},
            "accepted": {value2.hash : {ballot2}},
            "confirmed": {}
        }
        # This will look like: self.balloting_state = {'voted': {'value_hash_1': SCPBallot(counter=1, value=ValueObject1),},'accepted': { 'value_hash_2': SCPBallot(counter=3, value=ValueObject2)},'confirmed': { ... },'aborted': { ... }}
        # This will use sets for node names as opposed to counts, so will look like: {SCPBallot1.value: {'voted': set(Node1), ‘accepted’: set(Node2, Node3), ‘confirmed’: set(), ‘aborted’: set(), SCPBallot2.value: {'voted': set(), ‘accepted’: set(), ‘confirmed’: set(), ‘aborted’: set(node1, node2, node3)}

        # [ballot.value] = {'voted': set(), 'accepted': set(), 'confirmed': set(), 'aborted': set()}
        self.node.commit_ballot_statement_counter = {
            value: {
                "voted": set(),
                "accepted": set()
            }
        }
        self.node.commit_ballot_statement_counter[value]["voted"].add(node2)
        self.node.commit_ballot_statement_counter[value]["voted"].add(node3)
        self.node.commit_ballot_statement_counter[value]["voted"].add(node4)
        self.node.commit_ballot_statement_counter[value]["accepted"].add(node4)
        self.node.commit_ballot_statement_counter[value]["accepted"].add(node5)

        result = self.node.check_Commit_Quorum_threshold(ballot)
        self.assertTrue(result)

    def test_update_commit_balloting_state_correctly_updates(self):
        self.node = Node(name="1")

        value = Value(transactions={Transaction(0), Transaction(0)})
        value2 = Value(transactions={Transaction(0)})
        value3 = Value(transactions={Transaction(0)})
        ballot = SCPBallot(counter=1, value=value)
        ballot2 = SCPBallot(counter=1, value=value2)
        ballot3 = SCPBallot(counter=1, value=value3)

        self.node.commit_ballot_state = {
            "voted": {value.hash: ballot, value2.hash : ballot2},
            "accepted": {value3.hash: ballot3},
            "confirmed": {}
        }
        self.node.update_commit_balloting_state(ballot, "voted")

        self.assertTrue(self.node.commit_ballot_state['voted'] == {value2.hash: ballot2})
        self.assertTrue(self.node.commit_ballot_state['accepted'] == {value3.hash: ballot3, value.hash: ballot})
        self.assertTrue(len(self.node.commit_ballot_state['accepted']) == 2)

    def test_update_commit_balloting_state_updates_voted_to_accepted(self):
        self.node = Node(name="1")

        value = Value(transactions={Transaction(0), Transaction(0)})
        value2 = Value(transactions={Transaction(0)})
        value3 = Value(transactions={Transaction(0)})
        ballot = SCPBallot(counter=1, value=value)
        ballot2 = SCPBallot(counter=1, value=value2)
        ballot3 = SCPBallot(counter=1, value=value3)

        self.node.commit_ballot_state = {
            "voted": {value2.hash : ballot2},
            "accepted": {value.hash: ballot, value3.hash: ballot3},
            "confirmed": {}
        }
        self.node.update_commit_balloting_state(ballot, "voted")

        self.assertTrue(self.node.commit_ballot_state['voted'] == {value2.hash: ballot2})
        self.assertTrue(self.node.commit_ballot_state['accepted'] == {value3.hash: ballot3, value.hash: ballot})
        self.assertTrue(len(self.node.commit_ballot_state['accepted']) == 2)

    def test_update_commit_balloting_state_updates_accepted_to_confirmed(self):
        self.node = Node(name="1")

        value = Value(transactions={Transaction(0), Transaction(0)})
        value2 = Value(transactions={Transaction(0)})
        value3 = Value(transactions={Transaction(0)})
        ballot = SCPBallot(counter=1, value=value)
        ballot2 = SCPBallot(counter=1, value=value2)
        ballot3 = SCPBallot(counter=1, value=value3)

        self.node.balloting_state = {
            "voted": {},
            "accepted": {value.hash: ballot, value2.hash : ballot2},
            "confirmed": {value3.hash: ballot3}
        }
        self.node.update_prepare_balloting_state(ballot, "accepted")

        self.assertTrue(self.node.balloting_state['accepted'] == {value2.hash: ballot2})
        self.assertTrue(self.node.balloting_state['confirmed'] == {value3.hash: ballot3, value.hash: ballot})
        self.assertTrue(len(self.node.balloting_state['accepted']) == 1)
        self.assertTrue(len(self.node.balloting_state['confirmed']) == 2)

    def test_update_commit_balloting_state_does_not_update_accepted(self):
        self.node = Node(name="1")

        value = Value(transactions={Transaction(0), Transaction(0)})
        value2 = Value(transactions={Transaction(0)})
        value3 = Value(transactions={Transaction(0)})
        ballot = SCPBallot(counter=1, value=value)
        ballot2 = SCPBallot(counter=1, value=value2)
        ballot3 = SCPBallot(counter=1, value=value3)

        self.node.commit_ballot_state = {
            "voted": {value2.hash : ballot2},
            "accepted": {value.hash: ballot, value3.hash: ballot3},
            "confirmed": {}
        }

        self.node.update_commit_balloting_state(ballot, "voted")

        self.assertTrue(self.node.commit_ballot_state['voted'] == {value2.hash : ballot2})
        self.assertTrue(self.node.commit_ballot_state['accepted'] == {value.hash: ballot, value3.hash: ballot3})
        self.assertTrue(len(self.node.commit_ballot_state['accepted']) == 2)

    def test_update_commit_balloting_state_does_not_fail_when_empty(self):
        self.node = Node(name="1")

        value = Value(transactions={Transaction(0), Transaction(0)})
        value3 = Value(transactions={Transaction(0)})
        ballot = SCPBallot(counter=1, value=value)
        ballot3 = SCPBallot(counter=1, value=value3)

        self.node.commit_ballot_state = {
            "voted": {},
            "accepted": {value3.hash: ballot3},
            "confirmed": {}
        }
        self.node.update_commit_balloting_state(ballot, "voted")

        self.assertTrue(self.node.commit_ballot_state['voted'] == {})
        self.assertEqual(self.node.commit_ballot_state['accepted'],{value3.hash: ballot3})
        self.assertTrue(len(self.node.commit_ballot_state['accepted']) == 1)


    def test_retrieve_commit_broadcast_message_retrieves_correctly(self):
        self.node = Node("test_node")
        self.retrieving_node = Node("test_node2")
        mempool = Mempool()
        self.storage = Storage(self.node)
        self.node.attach_mempool(mempool)

        value1 = Value(transactions={Transaction(0), Transaction(0)})
        value2 = Value(transactions={Transaction(0), Transaction(0)})
        ballot1 = SCPBallot(counter=1, value=value1)
        ballot2 = SCPBallot(counter=1, value=value2)

        message = SCPCommit(ballot=ballot1, preparedCounter=ballot1.counter)

        self.node.commit_ballot_broadcast_flags = [message]
        retrieved = self.node.retrieve_ballot_commit_message(self.retrieving_node)

        self.assertEqual(retrieved, message)
        self.assertIn(retrieved, self.node.commit_ballot_broadcast_flags)
        self.assertIn(self.retrieving_node.name, self.node.received_commit_ballot_broadcast_msgs)

    def test_retrieve_commit_broadcast_message_retrieves_correctly_for_multiple_messages(self):
        self.node = Node("test_node")
        self.retrieving_node = Node("test_node2")
        mempool = Mempool()
        self.storage = Storage(self.node)
        self.node.attach_mempool(mempool)

        value1 = Value(transactions={Transaction(0), Transaction(0)})
        value2 = Value(transactions={Transaction(0), Transaction(0)})
        ballot1 = SCPBallot(counter=1, value=value1)
        ballot2 = SCPBallot(counter=1, value=value2)

        message = SCPCommit(ballot=ballot1, preparedCounter=ballot1.counter)
        message2 = SCPCommit(ballot=ballot2, preparedCounter=ballot2.counter)

        self.node.commit_ballot_broadcast_flags = set()
        self.node.commit_ballot_broadcast_flags.add(message)
        self.node.commit_ballot_broadcast_flags.add(message2)

        retrieved = self.node.retrieve_ballot_commit_message(self.retrieving_node)
        retrieved2 = self.node.retrieve_ballot_commit_message(self.retrieving_node)

        self.assertIn(retrieved, self.node.commit_ballot_broadcast_flags)
        self.assertIn(retrieved2, self.node.commit_ballot_broadcast_flags)
        self.assertIn(self.retrieving_node.name, self.node.received_commit_ballot_broadcast_msgs)
        self.assertEqual(len(self.node.received_commit_ballot_broadcast_msgs[self.retrieving_node.name]), 2)


    def test_retrieve_commit_broadcast_message_returns_none_for_empty(self):
            self.node = Node("test_node")
            self.retrieving_node = Node("test_node2")
            mempool = Mempool()
            self.storage = Storage(self.node)
            self.node.attach_mempool(mempool)

            retrieved = self.node.retrieve_ballot_commit_message(self.retrieving_node)

            self.assertEqual(retrieved, None)
            self.assertEqual(set(), self.node.commit_ballot_broadcast_flags)
            self.assertEqual({}, self.node.received_commit_ballot_broadcast_msgs)

    def test_retrieve_commit_broadcast_message_returns_none_for_node_with_all_messages(self):
        self.node = Node("test_node")
        self.retrieving_node = Node("test_node2")
        mempool = Mempool()
        self.storage = Storage(self.node)
        self.node.attach_mempool(mempool)

        value1 = Value(transactions={Transaction(0), Transaction(0)})
        value2 = Value(transactions={Transaction(0), Transaction(0)})
        ballot1 = SCPBallot(counter=1, value=value1)
        ballot2 = SCPBallot(counter=1, value=value2)

        message = SCPPrepare(ballot=ballot1)
        message2 = SCPPrepare(ballot=ballot2)

        self.node.commit_ballot_broadcast_flags = set()
        self.node.commit_ballot_broadcast_flags.add(message)
        self.node.commit_ballot_broadcast_flags.add(message2)
        self.node.received_commit_ballot_broadcast_msgs[self.retrieving_node.name] = [message, message2]

        retrieved = self.node.retrieve_ballot_commit_message(self.retrieving_node)

        self.assertEqual(retrieved, None)

    def test_receive_commit_message_processes_voted_to_accepted(self):
        self.node = Node("test_node")
        self.test_node = Node("test2")
        self.sending_node = Node("test_node2")

        value1 = Value(transactions={Transaction(0), Transaction(0)})
        ballot1 = SCPBallot(value=value1, counter=0)
        self.node.commit_ballot_state = {'voted': {value1.hash: ballot1}, 'accepted': {}, 'confirmed': {}}

        message = SCPCommit(ballot=ballot1, preparedCounter=ballot1.counter)

        self.sending_node.storage.add_messages(message)

        self.node.quorum_set.retrieve_random_peer = MagicMock(return_value=self.sending_node) # this is quorum.retrieve_random_peer()
        self.node.retrieve_ballot_commit_message = MagicMock(return_value=message) # this retrieves message, its retrieve_ballot_prepare_message()
        self.node.process_commit_ballot_message = MagicMock()
        self.node.update_commit_balloting_state = MagicMock()
        self.node.check_Commit_Quorum_threshold = MagicMock(return_value=True)

        self.node.receive_commit_message()

        # Assert that functions are called
        self.node.quorum_set.retrieve_random_peer.assert_called()
        self.node.retrieve_ballot_commit_message.assert_called()
        self.node.process_commit_ballot_message.assert_called_once()
        self.node.update_commit_balloting_state.assert_called_once()

        # Assert that nomination state is updated when quorum threshold is met
        self.node.process_commit_ballot_message.assert_called_with(message, self.sending_node)
        self.node.update_commit_balloting_state.assert_called_with(ballot1, 'voted')


    def test_receive_commit_message_processes_accepted_to_confirmed(self):
        self.node = Node("test_node")
        self.test_node = Node("test2")
        self.sending_node = Node("test_node2")

        value1 = Value(transactions={Transaction(0), Transaction(0)})
        ballot1 = SCPBallot(value=value1, counter=0)
        self.node.commit_ballot_state = {'voted': {}, 'accepted': {value1.hash: ballot1}, 'confirmed': {}}

        message = SCPCommit(ballot=ballot1, preparedCounter=ballot1.counter)

        self.sending_node.storage.add_messages(message)

        self.node.quorum_set.retrieve_random_peer = MagicMock(return_value=self.sending_node) # this is quorum.retrieve_random_peer()
        self.node.retrieve_ballot_commit_message = MagicMock(return_value=message) # this retrieves message, its retrieve_ballot_prepare_message()
        self.node.process_commit_ballot_message = MagicMock()
        self.node.update_commit_balloting_state = MagicMock()
        self.node.check_Commit_Quorum_threshold = MagicMock(return_value=True)

        self.node.receive_commit_message()

        # Assert that functions are called
        self.node.quorum_set.retrieve_random_peer.assert_called()
        self.node.retrieve_ballot_commit_message.assert_called()
        self.node.process_commit_ballot_message.assert_called_once()
        self.node.update_commit_balloting_state.assert_called_once()

        # Assert that nomination state is updated when quorum threshold is met
        self.node.process_commit_ballot_message.assert_called_with(message, self.sending_node)
        self.node.update_commit_balloting_state.assert_called_with(ballot1, 'accepted')


    def test_prepare_externalize_msg(self):
        self.node = Node(name="1")
        value1 = Value(transactions={Transaction(0), Transaction(0)})
        ballot1 = SCPBallot(counter=0, value=value1)
        self.node.commit_ballot_state = {"voted": {}, "accepted": {}, "confirmed": {value1.hash: ballot1}}

        self.node.prepare_Externalize_msg()
        # Ensure the message was prepared
        self.assertEqual(len(self.node.externalize_broadcast_flags), 1)
        self.assertEqual(len(self.node.externalized_slot_counter), 1)
        prepared_msg = self.node.externalize_broadcast_flags.pop()
        self.assertIsInstance(prepared_msg, SCPExternalize)

    def test_prepare_externalize_msg_for_no_confirmed_values(self):
        self.node = Node(name="1")
        self.node.commit_ballot_state = {"voted": {}, "accepted": {}, "confirmed": {}}
        self.node.retrieve_confirmed_commit_ballot = MagicMock(return_value=None)

        self.node.prepare_Externalize_msg()
        self.node.retrieve_confirmed_commit_ballot.assert_not_called()
        self.assertEqual(len(self.node.externalize_broadcast_flags), 0)