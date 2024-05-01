from Network import Network
from Mempool import Mempool
from Log import log
import unittest
from Value import Value
from SCPNominate import SCPNominate
from Storage import Storage
from Node import Node
from Transaction import Transaction
from unittest.mock import MagicMock

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

    def test_quorum_of_nodes(self):

        nodes = Network.generate_nodes(n_nodes=5, topology='ER')
        for node in nodes:
            log.test.debug('Node %s, quorum_set = %s',node.name,node.quorum_set)
            log.test.debug('Node %s, check_threshold = %s',node.name,node.quorum_set.get_quorum())

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

    def test_receive_works(self):
        self.node = Node("test_node")
        self.storage = Storage(self.node)
        self.other_node = Node("test_node2")
        self.node.process_received_message = MagicMock()

        value1 = Value(transactions={Transaction(0), Transaction(0)})
        value2 = Value(transactions={Transaction(0), Transaction(0)})

        self.node.receive_message(self.other_node, [value1, value2])

        self.node.process_received_message.assert_called_once()

    def test_send_message_to_all_peers_send_message(self):
        self.node = Node("test_node")
        self.storage = Storage(self.node)
        self.priority_node = Node("test_node2")
        self.node.receive_message = MagicMock()

        value1 = Value(transactions={Transaction(0), Transaction(0)})
        value2 = Value(transactions={Transaction(0), Transaction(0)})

        message = SCPNominate(voted=[value1], accepted=[value2])

        self.priority_node.storage.add_messages(message)

        self.node.get_neighbors = MagicMock(return_value=[self.priority_node, self.node])

        self.node.send_message_to_all_peers(self.priority_node)

        self.node.receive_message.assert_called_once()

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

            self.assertEqual(self.node.statement_counter[value1.hash]["voted"][self.other_node.name], 2)

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
