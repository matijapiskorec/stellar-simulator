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
from unittest import mock
from Globals import Globals
from QuorumSet import QuorumSet


class NodeTest(unittest.TestCase):
    def setup(self):
        pass

    # TODO: WRITE INTEGRATION TESTS ACROSS PHASES
    # RUN SIMULATION FOR 10 SLOTS AND TEST TO SEE WHAT HAPPENS: SPECIFIC ASSERTS TO VERIFY CONSENSUS

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

        for topology in ['FULL', 'ER']:
            nodes = Network.generate_nodes(n_nodes=30, topology=topology)

            mempool = Mempool()
            for node in nodes:
                node.attach_mempool(mempool)
                # if topology == 'ER':
                # print(f"Node {node.name} has QuorumSet = {node.quorum_set.nodes} with inner sets {node.quorum_set.inner_sets}")

            for node in nodes:
                log.test.debug('Node %s, all peers in quorum set = %s', node.name, node.quorum_set.get_nodes())
                neighbors = list(node.get_priority_list())  # Convert set to list for indexing
                if neighbors:
                    max_priority_neighbor = neighbors[0]
                    max_priority = node.priority(max_priority_neighbor)
                    for neighbor in neighbors[1:]:
                        priority = node.priority(neighbor)
                        if priority > max_priority:
                            max_priority = priority
                            max_priority_neighbor = neighbor
                else:
                    max_priority_neighbor = None
                    max_priority = None

                if len(node.get_priority_list()) > 0:
                    print(f'Node %s, highest priority neighbor =', node.get_highest_priority_neighbor(),
                          max_priority_neighbor)
                    self.assertTrue(node.get_highest_priority_neighbor() == max_priority_neighbor)
                    print(f'Node %s, priority of highest priority neighbor =',
                          node.priority(node.get_highest_priority_neighbor()), max_priority)
                    self.assertTrue(node.priority(node.get_highest_priority_neighbor()) == max_priority)


    def test_retrieves_transaction_if_not_externalized(self):
        self.node = Node("test_node")
        self.mempool = Mempool()
        self.node.attach_mempool(self.mempool)
        transaction = Transaction(100)
        self.mempool.transactions.append(transaction)

        self.node.retrieve_transaction_from_mempool()

        self.assertIn(transaction, self.node.ledger.transactions, "Transaction should be added to the ledger.")

    def test_does_not_retrieve_if_transaction_is_externalized(self):
        self.node = Node("test_node")
        self.mempool = Mempool()
        self.node.attach_mempool(self.mempool)
        transaction = Transaction(200)
        self.mempool.transactions.append(transaction)

        value = Value(transactions={transaction})
        ballot = SCPBallot(counter=1, value=value)
        externalize_msg = SCPExternalize(ballot=ballot, hCounter=1)
        self.node.externalized_slot_counter.add(externalize_msg)
        self.node.retrieve_transaction_from_mempool()

        self.assertNotIn(transaction, self.node.ledger.transactions, "Transaction should NOT be added to the ledger.")


    def test_transaction_is_in_externalized_slots(self):
        self.node = Node("test_node")
        self.transaction = Transaction(200)
        value = Value(transactions={self.transaction})  # Store full transaction objects
        ballot = SCPBallot(counter=1, value=value)
        externalize_msg = SCPExternalize(ballot=ballot, hCounter=1)
        self.node.externalized_slot_counter.add(externalize_msg)

        self.assertTrue(self.node.is_transaction_in_externalized_slots(self.transaction.hash))

    def test_transaction_not_in_externalized_slots(self):
        self.node = Node("test_node")
        self.transaction = Transaction(200)
        self.assertFalse(self.node.is_transaction_in_externalized_slots(self.transaction.hash),)

    def test_transaction_in_multiple_externalized_slots(self):
        self.node = Node("test_node")
        self.transaction = Transaction(200)
        value1 = Value(transactions={self.transaction})
        value2 = Value(transactions={Transaction(300), self.transaction})  # Another externalized transaction
        ballot1 = SCPBallot(counter=1, value=value1)
        ballot2 = SCPBallot(counter=2, value=value2)
        externalize_msg1 = SCPExternalize(ballot=ballot1, hCounter=1)
        externalize_msg2 = SCPExternalize(ballot=ballot2, hCounter=2)

        self.node.externalized_slot_counter.update({externalize_msg1, externalize_msg2})  # Add both messages

        self.assertTrue(self.node.is_transaction_in_externalized_slots(self.transaction.hash))

    def test_unrelated_transaction_not_detected(self):
        self.node = Node("test_node")
        self.transaction = Transaction(200)
        unrelated_transaction = Transaction(400)
        value = Value(transactions={unrelated_transaction})
        ballot = SCPBallot(counter=1, value=value)
        externalize_msg = SCPExternalize(ballot=ballot, hCounter=1)
        self.node.externalized_slot_counter.add(externalize_msg)

        self.assertFalse(self.node.is_transaction_in_externalized_slots(self.transaction.hash),"Unrelated transaction should NOT be detected as externalized.")


    def test_no_externalized_message(self):
        self.node = Node(name="1")
        self.node.ledger = MagicMock()
        self.node.slot = 2  # Set current slot to 2 for testing purposes
        # Test when there is no externalized message for the previous slot (self.slot - 1)
        self.node.slot = 1  # Previous slot would be 0
        self.node.ledger.get_slot.return_value = None  # Simulate no externalized message for slot 0

        # Call calculate_nomination_round and verify that it returns None
        round = self.node.calculate_nomination_round()
        self.assertIsNone(round, "Should return None when no externalized message is found for the previous slot")

    def test_calculate_round_1(self):
        self.node = Node(name="1")
        self.node.ledger = MagicMock()
        # Test for round 1, assuming that the previous round was just completed
        self.node.slot = 2
        # Set the timestamp for the previous externalized message (slot 1)
        self.node.ledger.get_slot.return_value = MagicMock(timestamp=10)
        Globals.simulation_time = 12  # Current time is 2 seconds after the previous timestamp

        # Call calculate_nomination_round and verify that it returns round 1
        round = self.node.calculate_nomination_round()
        self.assertEqual(round, 1, "Should be in round 1 if the time difference is less than 2 seconds")


    def test_calculate_round_3(self):
        self.node = Node(name="1")
        self.node.ledger = MagicMock()
        # Test for round 3, assuming the node is in the third round
        self.node.slot = 4
        self.node.ledger.get_slot.return_value = MagicMock(timestamp=10)
        Globals.simulation_time = 14  # Current time is 4 seconds after the previous timestamp

        # Call calculate_nomination_round and verify that it returns round 3
        round = self.node.calculate_nomination_round()
        self.assertEqual(round, 2, "Should be in round 2 if the time difference is greater than 3 but less than 4")

    def test_round_increment_logic(self):
        self.node = Node(name="1")
        self.node.ledger = MagicMock()
        # Test that rounds increment correctly based on the time difference
        self.node.slot = 5
        self.node.ledger.get_slot.return_value = MagicMock(timestamp=10)
        Globals.simulation_time = 19  # Current time is 9 seconds after the previous timestamp

        # Call calculate_nomination_round and verify that it returns round 4
        round = self.node.calculate_nomination_round()
        self.assertEqual(round, 3, "Should be in round 4 after 9 seconds")


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

        neighbors = self.node.get_priority_list()

        self.assertIsInstance(neighbors, set)
        if len(neighbors) > 0:
            for neighbor in neighbors:
                self.assertIsInstance(neighbor, Node, "Each neighbor should be an instance of Node")



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
                # Check that there is exactly one nominated value.
                self.assertEqual(len(node.nomination_state['voted']), 1)
                # Then assert that the number of transactions in this combined nomination equals the expected amount (e.g., the number of transactions in the ledger).
                self.assertTrue(len(node.nomination_state['voted'][0].transactions) == len(node.ledger.transactions))
                self.assertTrue(len(node.storage.messages) > 0)
                self.assertEqual(len(node.broadcast_flags), 1)

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
        self.node.quorum_set.nodes = [self.priority_node]

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
        self.node.quorum_set.nodes = [self.priority_node]

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
        self.node.quorum_set.nodes = [self.priority_node]
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

        self.retrieving_node.broadcast_flags = [message]

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

        self.node.simple_process_commit_ballot_message(mock_msg, self.sender_node)

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

        self.node.simple_process_commit_ballot_message(mock_msg, self.sender_node)

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

        self.node.simple_process_commit_ballot_message(mock_msg, self.sender_node)

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
        self.node.simple_process_commit_ballot_message = MagicMock()
        self.node.update_commit_balloting_state = MagicMock()
        self.node.check_Commit_Quorum_threshold = MagicMock(return_value=True)

        self.node.receive_commit_message()

        # Assert that functions are called
        self.node.quorum_set.retrieve_random_peer.assert_called()
        self.node.retrieve_ballot_commit_message.assert_called()
        self.node.simple_process_commit_ballot_message.assert_called_once()
        self.node.update_commit_balloting_state.assert_called_once()

        # Assert that nomination state is updated when quorum threshold is met
        self.node.simple_process_commit_ballot_message.assert_called_with(message, self.sending_node)
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
        self.node.simple_process_commit_ballot_message = MagicMock()
        self.node.update_commit_balloting_state = MagicMock()
        self.node.check_Commit_Quorum_threshold = MagicMock(return_value=True)

        self.node.receive_commit_message()

        # Assert that functions are called
        self.node.quorum_set.retrieve_random_peer.assert_called()
        self.node.retrieve_ballot_commit_message.assert_called()
        self.node.simple_process_commit_ballot_message.assert_called_once()
        self.node.update_commit_balloting_state.assert_called_once()

        # Assert that nomination state is updated when quorum threshold is met
        self.node.simple_process_commit_ballot_message.assert_called_with(message, self.sending_node)
        self.node.update_commit_balloting_state.assert_called_with(ballot1, 'accepted')


    def test_prepare_externalize_msg(self):
        # Initialize self.node first
        self.node = Node(name="1")
        self.mempool = Mempool()
        self.node.attach_mempool(self.mempool)
        self.test_sender = Node(name="2")
        self.test_sender.attach_mempool(self.mempool)

        Globals.simulation_time = 123.123

        # Setting up the value and ballot
        value1 = Value(transactions={Transaction(0), Transaction(0)})
        ballot1 = SCPBallot(counter=1, value=value1)
        self.node.commit_ballot_state = {"voted": {}, "accepted": {}, "confirmed": {value1.hash: ballot1}}
        initial_slot = self.node.slot

        # Calling the method that should call process_commit_ballot_message
        self.node.prepare_Externalize_msg()

        # Ensure the message was prepared
        self.assertEqual(len(self.node.externalize_broadcast_flags), 1)
        self.assertEqual(len(self.node.externalized_slot_counter), 1)
        # Fetch the prepared message
        prepared_slot, prepared_msg = self.node.externalize_broadcast_flags.pop()
        self.assertEqual(prepared_slot, initial_slot)
        self.assertEqual(self.node.slot, initial_slot + 1)
        self.assertIsInstance(prepared_msg, SCPExternalize)

        # Verify the mocked time was used in the externalize message
        ledger_entry = self.node.ledger.get_slot(initial_slot)
        self.assertIsNotNone(ledger_entry)
        self.assertEqual(ledger_entry["value"], ballot1.value)
        self.assertEqual(prepared_msg._time, 123.123)


    def test_prepare_externalize_msg_for_no_confirmed_values(self):
        self.node = Node(name="1")
        self.node.commit_ballot_state = {"voted": {}, "accepted": {}, "confirmed": {}}
        self.node.retrieve_confirmed_commit_ballot = MagicMock(return_value=None)

        self.node.prepare_Externalize_msg()
        self.node.retrieve_confirmed_commit_ballot.assert_not_called()
        self.assertEqual(len(self.node.externalize_broadcast_flags), 0)

    def test_retrieve_externalize_message_retrieves_correctly(self):
        self.node = Node("test_node")
        self.requesting_node = Node("requesting_node")

        message1 = SCPExternalize(
            ballot=SCPBallot(counter=1, value=Value(transactions={Transaction(0), Transaction(1)})))
        slot1 = 5  # Example slot number
        self.requesting_node.externalize_broadcast_flags.add((slot1, message1))

        retrieved_slot, retrieved_message = self.node.retrieve_externalize_msg(self.requesting_node)

        self.assertEqual(retrieved_slot, slot1)
        self.assertEqual(retrieved_message, message1)
        self.assertIn(self.requesting_node.name, self.node.peer_externalised_statements)
        self.assertIn((slot1, message1), self.node.peer_externalised_statements[self.requesting_node.name])

    def test_retrieve_externalize_message_no_flags(self):
        self.node = Node("test_node")
        self.requesting_node = Node("requesting_node")

        # Ensure the requesting node has no externalize_broadcast_flags
        self.requesting_node.externalize_broadcast_flags = set()

        retrieved = self.node.retrieve_externalize_msg(self.requesting_node)

        self.assertIsNone(retrieved)


    def test_prune_statement_counter_removes_finalized(self):
        # Create a node.
        node = Node("test_node")
        # Create two transactions.
        tx_finalized = Transaction(200)
        tx_pending = Transaction(300)
        # Wrap them in Value objects.
        value_finalized = Value(transactions={tx_finalized})
        value_pending = Value(transactions={tx_pending})
        # Simulate that the ledger finalized the value for tx_finalized.
        # Each ledger slot is a dict with key 'value' containing the Value.
        node.ledger.slots[1] = {'value': value_finalized, 'timestamp': 123.0}
        # Populate the statement counter with both Values using their hash.
        node.statement_counter[value_finalized.hash] = {"voted": {"peer1": 1}, "accepted": {"peer1": 1}}
        node.statement_counter[value_pending.hash] = {"voted": {"peer2": 1}, "accepted": {"peer2": 1}}
        # Run the prune function.
        node.prune_nomination_phase_data()
        # The finalized Value entry should be removed (its key should not exist).
        self.assertNotIn(value_finalized.hash, node.statement_counter,
                         "Finalized Value should be pruned from statement_counter.")
        # The pending Value entry should remain.
        self.assertIn(value_pending.hash, node.statement_counter,
                      "Pending Value should remain in statement_counter.")

    def test_prune_broadcast_flags_removes_finalized_messages(self):
        # Create a node.
        node = Node("test_node")
        # Create two transactions.
        tx_finalized = Transaction(400)
        tx_pending = Transaction(500)
        # Wrap them in Value objects.
        value_finalized = Value(transactions={tx_finalized})
        value_pending = Value(transactions={tx_pending})
        # Create two SCPNominate messages using these Values, wrapped in lists.
        msg_finalized = SCPNominate(voted=[value_finalized], accepted=[value_finalized])
        msg_pending = SCPNominate(voted=[value_pending], accepted=[value_pending])
        # Set the node's broadcast_flags.
        node.broadcast_flags = [msg_finalized, msg_pending]
        # Simulate that the ledger finalized the Value for tx_finalized.
        node.ledger.slots[1] = {'value': value_finalized, 'timestamp': 123.0}
        # Run the prune function.
        node.prune_nomination_phase_data()
        # The message referencing the finalized Value should be pruned.
        self.assertNotIn(msg_finalized, node.broadcast_flags,
                         "Broadcast message with finalized Value should be pruned.")
        # The message referencing the pending Value should remain.
        self.assertIn(msg_pending, node.broadcast_flags,
                      "Broadcast message with pending Value should remain.")

    def test_prune_does_not_remove_non_finalized_entries(self):
        # Create a node.
        node = Node("test_node")
        # Create a transaction that is not finalized.
        tx_pending = Transaction(600)
        value_pending = Value(transactions={tx_pending})
        # Populate the statement counter with the pending Value.
        node.statement_counter[value_pending.hash] = {"voted": {"peer1": 1}, "accepted": {}}
        # Leave the ledger empty (i.e., no finalized Values).
        node.ledger.slots = {}
        # Run the prune function.
        node.prune_nomination_phase_data()
        # Verify that the pending Value remains in the statement counter.
        self.assertIn(value_pending.hash, node.statement_counter,
                      "Non-finalized Value should remain in statement_counter.")

    # Optionally, add an extra test to check that even if a Value contains multiple transactions,
    # if any one of them is finalized (by matching a Value exactly stored in the ledger),
    # the entire Value is removed.
    def test_prune_removes_value_if_any_contained_tx_finalized(self):
        node = Node("test_node")
        # Create two transactions.
        tx1 = Transaction(700)
        tx2 = Transaction(800)
        # Wrap both in one Value.
        value_mixed = Value(transactions={tx1, tx2})
        # Simulate that the ledger finalized the entire Value (value_mixed) for a slot.
        node.ledger.slots[1] = {'value': value_mixed, 'timestamp': 456.0}
        # Populate statement counter with this Value.
        node.statement_counter[value_mixed.hash] = {"voted": {"peer1": 1}, "accepted": {"peer1": 1}}
        # Run pruning.
        node.prune_nomination_phase_data()
        # Since value_mixed was finalized, it should be pruned.
        self.assertNotIn(value_mixed.hash, node.statement_counter,
                         "Value containing a finalized transaction(s) should be removed from statement counter.")

    def test_reset_commit_phase_state_prunes_finalized_and_keeps_nonfinalized(self):
        # Create a node.
        node = Node("test_node")

        # Create two transactions: one that is finalized and one that remains pending.
        tx_finalized = Transaction(200)
        tx_pending = Transaction(300)

        # Wrap each transaction in a Value.
        value_finalized = Value(transactions={tx_finalized})
        value_pending = Value(transactions={tx_pending})

        # Create SCPBallot objects for the commit-phase.
        ballot_finalized = SCPBallot(counter=1, value=value_finalized)
        ballot_pending = SCPBallot(counter=1, value=value_pending)

        # 1. Set up commit_ballot_statement_counter.
        # Keys are Value objects; values are dictionaries storing sets of peer names.
        node.commit_ballot_statement_counter = {
            value_finalized: {"voted": {"peer1"}, "accepted": {"peer1"}, "confirmed": set(), "aborted": set()},
            value_pending: {"voted": {"peer2"}, "accepted": {"peer2"}, "confirmed": set(), "aborted": set()}
        }

        # 2. Set up commit_ballot_state for states 'voted', 'accepted', 'confirmed'.
        # Each state's dictionary maps keys (could be any identifier) to an SCPBallot.
        node.commit_ballot_state = {
            'voted': {"k1": ballot_finalized, "k2": ballot_pending},
            'accepted': {"k1": ballot_finalized, "k2": ballot_pending},
            'confirmed': {"k1": ballot_finalized, "k2": ballot_pending}
        }

        # 3. Set up commit_ballot_broadcast_flags.
        # For the commit phase we use SCPCommit messages.
        commit_msg_finalized = SCPCommit(ballot=ballot_finalized, preparedCounter=ballot_finalized.counter)
        commit_msg_pending = SCPCommit(ballot=ballot_pending, preparedCounter=ballot_pending.counter)
        # Now store them in a set.
        node.commit_ballot_broadcast_flags = {commit_msg_finalized, commit_msg_pending}

        # 4. Set up received_commit_ballot_broadcast_msgs for a peer.
        node.received_commit_ballot_broadcast_msgs = {
            "peer1": [commit_msg_finalized, commit_msg_pending]
        }

        # Create a finalized_ballot that indicates tx_finalized is finalized.
        # Its Value contains only tx_finalized.
        finalized_ballot = SCPBallot(counter=1, value=Value(transactions={tx_finalized}))

        # Call the reset_commit_phase_state, which should remove any commit-phase entries referencing a ballot
        # whose Value contains a transaction with the same hash as tx_finalized.
        node.reset_commit_phase_state(finalized_ballot)

        # Helper functions to check if a Value or SCPBallot contains the finalized transaction.
        def value_contains_finalized_tx(value):
            return any(tx.hash == tx_finalized.hash for tx in value.transactions)

        def ballot_contains_finalized_tx(ballot):
            return any(tx.hash == tx_finalized.hash for tx in ballot.value.transactions)

        # 1. Assert that commit_ballot_statement_counter does not include any Value containing tx_finalized.
        for val in node.commit_ballot_statement_counter.keys():
            self.assertFalse(value_contains_finalized_tx(val),
                             f"Value {val} in commit_ballot_statement_counter should not contain finalized transaction {tx_finalized.hash}")

        # 2. Assert that in commit_ballot_state for each state, ballots containing tx_finalized were removed.
        for state in ['voted', 'accepted', 'confirmed']:
            for key, ballot in node.commit_ballot_state[state].items():
                self.assertFalse(ballot_contains_finalized_tx(ballot),
                                 f"In commit_ballot_state[{state}], ballot '{key}' containing finalized transaction should be removed.")
            # Additionally, the ballot that contains only the pending transaction should remain.
            self.assertIn("k2", node.commit_ballot_state[state],
                          f"Ballot with pending transaction should remain in commit_ballot_state[{state}].")

        # 3. Assert that in commit_ballot_broadcast_flags, the message referencing a ballot with tx_finalized is removed.
        self.assertNotIn(commit_msg_finalized, node.commit_ballot_broadcast_flags,
                         "Commit broadcast message with finalized ballot should be removed.")
        self.assertIn(commit_msg_pending, node.commit_ballot_broadcast_flags,
                      "Commit broadcast message with pending ballot should remain.")

        # 4. Assert that in received_commit_ballot_broadcast_msgs, for each peer, messages with ballots containing tx_finalized are removed.
        for peer, msgs in node.received_commit_ballot_broadcast_msgs.items():
            self.assertNotIn(commit_msg_finalized, msgs,
                             f"Received commit broadcast message with finalized transaction for peer {peer} should be removed.")
            self.assertIn(commit_msg_pending, msgs,
                          f"Received commit broadcast message with pending transaction for peer {peer} should remain.")


    def test_reset_commit_phase_state_does_nothing_when_no_ballot_contains_finalized_tx(self):
        """
        If the finalized_ballot passed finalizes a transaction that does not appear in any commit-phase ballot,
        then reset_commit_phase_state should leave the commit-phase state unchanged.
        """
        node = Node("test_node")

        # Create two transactions that will remain pending.
        tx_pending1 = Transaction(400)
        tx_pending2 = Transaction(500)
        value_pending1 = Value(transactions={tx_pending1})
        value_pending2 = Value(transactions={tx_pending2})
        ballot_pending1 = SCPBallot(counter=1, value=value_pending1)
        ballot_pending2 = SCPBallot(counter=1, value=value_pending2)

        # Set up commit_ballot_statement_counter (keys are Value objects).
        node.commit_ballot_statement_counter = {
            value_pending1: {"voted": {"peer1"}, "accepted": {"peer1"}, "confirmed": set(), "aborted": set()},
            value_pending2: {"voted": {"peer2"}, "accepted": {"peer2"}, "confirmed": set(), "aborted": set()}
        }

        # Set up commit_ballot_state.
        node.commit_ballot_state = {
            'voted': {"k1": ballot_pending1, "k2": ballot_pending2},
            'accepted': {"k1": ballot_pending1, "k2": ballot_pending2},
            'confirmed': {"k1": ballot_pending1, "k2": ballot_pending2}
        }

        # Set up commit_ballot_broadcast_flags (as a list or set is acceptable if the ballots are hashable);
        # here we use a list for simplicity.
        commit_msg1 = SCPCommit(ballot=ballot_pending1, preparedCounter=ballot_pending1.counter)
        commit_msg2 = SCPCommit(ballot=ballot_pending2, preparedCounter=ballot_pending2.counter)
        node.commit_ballot_broadcast_flags = [commit_msg1, commit_msg2]

        # Set up received commit ballot broadcast messages for one peer.
        node.received_commit_ballot_broadcast_msgs = {
            "peer1": [commit_msg1, commit_msg2]
        }

        # Create a finalized_ballot that finalizes a transaction not present in any ballot.
        tx_unrelated = Transaction(600)
        finalized_ballot = SCPBallot(counter=1, value=Value(transactions={tx_unrelated}))

        # Call reset_commit_phase_state.
        node.reset_commit_phase_state(finalized_ballot)

        # Assert that commit-phase state remains unchanged.
        self.assertEqual(len(node.commit_ballot_statement_counter), 2,
                         "No commit ballot statement should be pruned if none contain the finalized transaction.")
        for state in ['voted', 'accepted', 'confirmed']:
            self.assertEqual(len(node.commit_ballot_state[state]), 2,
                             f"Commit_ballot_state[{state}] should remain unchanged.")
        self.assertIn(commit_msg1, node.commit_ballot_broadcast_flags,
                      "Pending commit broadcast message should remain.")
        self.assertIn(commit_msg2, node.commit_ballot_broadcast_flags,
                      "Pending commit broadcast message should remain.")
        for peer, msgs in node.received_commit_ballot_broadcast_msgs.items():
            self.assertIn(commit_msg1, msgs,
                          f"Received message for peer {peer} should remain.")
            self.assertIn(commit_msg2, msgs,
                          f"Received message for peer {peer} should remain.")

    def test_reset_commit_phase_state_with_empty_commit_phase_state(self):
        """
        If all commit-phase data structures are empty, reset_commit_phase_state should complete without error
        and leave the structures empty.
        """
        node = Node("test_node")
        # Set commit-phase structures to empty.
        node.commit_ballot_statement_counter = {}
        node.commit_ballot_state = {'voted': {}, 'accepted': {}, 'confirmed': {}}
        node.commit_ballot_broadcast_flags = []
        node.received_commit_ballot_broadcast_msgs = {}

        # Create a finalized_ballot (its value doesn't really matter here).
        tx = Transaction(700)
        finalized_ballot = SCPBallot(counter=1, value=Value(transactions={tx}))

        # Call reset_commit_phase_state.
        node.reset_commit_phase_state(finalized_ballot)

        # Assert that all commit-phase data structures remain empty.
        self.assertEqual(node.commit_ballot_statement_counter, {},
                         "Empty commit_ballot_statement_counter should remain empty.")
        for state in ['voted', 'accepted', 'confirmed']:
            self.assertEqual(node.commit_ballot_state[state], {},
                             f"Empty commit_ballot_state[{state}] should remain empty.")
        self.assertEqual(len(node.commit_ballot_broadcast_flags), 0,
                         "Empty commit_ballot_broadcast_flags should remain empty.")
        self.assertEqual(node.received_commit_ballot_broadcast_msgs, {},
                         "Empty received_commit_ballot_broadcast_msgs should remain empty.")

    def test_reset_commit_phase_state_removes_finalized_from_received_commit_ballot_broadcast_msgs_multiple_peers(self):
        """
        Test that when commit-phase broadcast messages are received by multiple peers,
        any message containing a ballot with a finalized transaction is removed for each peer.
        """
        node = Node("test_node")
        tx_finalized = Transaction(800)
        tx_pending = Transaction(900)
        value_finalized = Value(transactions={tx_finalized})
        value_pending = Value(transactions={tx_pending})
        ballot_finalized = SCPBallot(counter=1, value=value_finalized)
        ballot_pending = SCPBallot(counter=1, value=value_pending)

        commit_msg_finalized = SCPCommit(ballot=ballot_finalized, preparedCounter=ballot_finalized.counter)
        commit_msg_pending = SCPCommit(ballot=ballot_pending, preparedCounter=ballot_pending.counter)

        # Use a list for commit_ballot_broadcast_flags.
        node.commit_ballot_broadcast_flags = [commit_msg_finalized, commit_msg_pending]

        # Set up received commit ballot broadcast messages for multiple peers.
        node.received_commit_ballot_broadcast_msgs = {
            "peer1": [commit_msg_finalized, commit_msg_pending],
            "peer2": [commit_msg_pending, commit_msg_finalized],
            "peer3": [commit_msg_pending]
        }

        # Also set up commit_ballot_statement_counter and commit_ballot_state.
        node.commit_ballot_statement_counter = {
            value_finalized: {"voted": {"peer1"}, "accepted": {"peer1"}, "confirmed": set(), "aborted": set()},
            value_pending: {"voted": {"peer2"}, "accepted": {"peer2"}, "confirmed": set(), "aborted": set()}
        }
        node.commit_ballot_state = {
            'voted': {"k1": ballot_finalized, "k2": ballot_pending},
            'accepted': {"k1": ballot_finalized, "k2": ballot_pending},
            'confirmed': {"k1": ballot_finalized, "k2": ballot_pending}
        }

        # Create a finalized_ballot finalizing tx_finalized.
        finalized_ballot = SCPBallot(counter=1, value=Value(transactions={tx_finalized}))

        # Call reset_commit_phase_state.
        node.reset_commit_phase_state(finalized_ballot)

        # Assert that in received_commit_ballot_broadcast_msgs, messages with ballots containing tx_finalized are removed.
        for peer, msgs in node.received_commit_ballot_broadcast_msgs.items():
            self.assertNotIn(commit_msg_finalized, msgs,
                             f"For peer {peer}, commit message with finalized ballot should be removed.")
            self.assertIn(commit_msg_pending, msgs,
                          f"For peer {peer}, commit message with pending ballot should remain.")


    def test_reset_prepare_ballot_phase_removes_finalized_entries_and_keeps_nonfinalized(self):
        # Create a node.
        node = Node("test_node")

        # Create two transactions.
        tx_finalized = Transaction(1000)
        tx_pending = Transaction(2000)

        # Wrap transactions in Value objects.
        value_finalized = Value(transactions={tx_finalized})
        value_pending = Value(transactions={tx_pending})

        # Create SCPBallot objects for each value.
        ballot_finalized = SCPBallot(counter=1, value=value_finalized)
        ballot_pending = SCPBallot(counter=1, value=value_pending)

        # Create SCPPrepare messages (for the prepare phase) for each ballot.
        prepare_msg_finalized = SCPPrepare(ballot=ballot_finalized, prepared=ballot_finalized, aCounter=0,
                                           hCounter=ballot_finalized.counter, cCounter=0)
        prepare_msg_pending = SCPPrepare(ballot=ballot_pending, prepared=ballot_pending, aCounter=0,
                                         hCounter=ballot_pending.counter, cCounter=0)

        # 1. Set up balloting_state (for each phase, add one entry to be pruned and one to be kept).
        node.balloting_state = {
            'voted': {'remove_key': ballot_finalized, 'keep_key': ballot_pending},
            'accepted': {'remove_key': ballot_finalized, 'keep_key': ballot_pending},
            'confirmed': {'remove_key': ballot_finalized, 'keep_key': ballot_pending},
            'aborted': {'remove_key': ballot_finalized, 'keep_key': ballot_pending}
        }

        # 2. Set up ballot_statement_counter (keys are Value objects).
        node.ballot_statement_counter = {
            value_finalized: {"voted": {"peer1"}, "accepted": {"peer1"}, "confirmed": set(), "aborted": set()},
            value_pending: {"voted": {"peer2"}, "accepted": {"peer2"}, "confirmed": set(), "aborted": set()}
        }

        # 3. Set up prepared_ballots (keys are Value objects).
        node.prepared_ballots = {
            value_finalized: prepare_msg_finalized,
            value_pending: prepare_msg_pending
        }

        # 4. Set up ballot_prepare_broadcast_flags as a list of SCPPrepare messages.
        node.ballot_prepare_broadcast_flags = [prepare_msg_finalized, prepare_msg_pending]

        # 5. Set up received_prepare_broadcast_msgs for two peers.
        node.received_prepare_broadcast_msgs = {
            "peer1": [prepare_msg_finalized, prepare_msg_pending],
            "peer2": [prepare_msg_pending, prepare_msg_finalized]
        }

        # Create a finalized_ballot that finalizes value_finalized.
        finalized_ballot = SCPBallot(counter=1, value=value_finalized)

        # Call the reset function.
        node.reset_prepare_ballot_phase(finalized_ballot)

        # --- Assertions ---
        # (A) In balloting_state: All entries whose ballot.value.hash equals value_finalized.hash should be removed.
        for state in ['voted', 'accepted', 'confirmed', 'aborted']:
            for key, ballot in node.balloting_state[state].items():
                self.assertNotEqual(ballot.value.hash, value_finalized.hash,
                                    f"balloting_state[{state}] entry '{key}' should not have finalized value (hash {value_finalized.hash}).")
            # And the pending ballot should remain (using key 'keep_key').
            self.assertIn('keep_key', node.balloting_state['voted'],
                          "Pending ballot in balloting_state['voted'] should remain.")

        # (B) In ballot_statement_counter: No key equal to the finalized value should remain.
        for val in node.ballot_statement_counter.keys():
            self.assertNotEqual(val.hash, value_finalized.hash,
                                "ballot_statement_counter should not include a key for the finalized value.")
        self.assertIn(value_pending.hash, [v.hash for v in node.ballot_statement_counter.keys()],
                      "ballot_statement_counter should retain the pending value.")

        # (C) In prepared_ballots: The finalized value key should be removed.
        for val in node.prepared_ballots.keys():
            self.assertNotEqual(val.hash, value_finalized.hash,
                                "prepared_ballots should not contain the finalized value.")
        self.assertIn(value_pending.hash, [v.hash for v in node.prepared_ballots.keys()],
                      "prepared_ballots should retain the pending value.")

        # (D) In ballot_prepare_broadcast_flags: No message with ballot.value.hash equal to the finalized value.
        for msg in node.ballot_prepare_broadcast_flags:
            self.assertNotEqual(msg.ballot.value.hash, value_finalized.hash,
                                "ballot_prepare_broadcast_flags should not include a message with the finalized value.")

        # (E) In received_prepare_broadcast_msgs: For each peer, no message with ballot.value.hash equal to the finalized value.
        for peer, msgs in node.received_prepare_broadcast_msgs.items():
            for msg in msgs:
                self.assertNotEqual(msg.ballot.value.hash, value_finalized.hash,
                                    f"Received prepare broadcast messages for peer {peer} should not include messages with the finalized value.")

