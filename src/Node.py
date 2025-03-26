"""
=========================
Node
=========================

Author: Matija Piskorec, Jaime de Vivero Woods

Last update: March 2025

Node class.

Documentation:

[2] Nicolas Barry and Giuliano Losa and David Mazieres and Jed McCaleb and Stanislas Polu, The Stellar Consensus Protocol (SCP) - technical implementation draft, https://datatracker.ietf.org/doc/draft-mazieres-dinrg-scp/05/
"""
import random

import numpy as np
from Log import log
from Event import Event
from Ledger import Ledger
from QuorumSet import QuorumSet
from SCPNominate import SCPNominate
from SCPBallot import SCPBallot
from SCPPrepare import SCPPrepare
from SCPCommit import SCPCommit
from SCPExternalize import SCPExternalize
from Value import Value
from Storage import Storage
from Globals import Globals
import copy
import xdrlib3
import hashlib
import os

class Node():
    name = None
    quorum_set = None
    ledger = None
    mempool = None
    storage = None
    nomination_round = None

    def __init__(self, name, quorum_set=None, ledger=None, storage=None):
        self.name = name
        self.quorum_set = quorum_set if quorum_set is not None else QuorumSet(self)
        self.ledger = ledger if ledger is not None else Ledger(self)
        self.slot = 1
        self.mempool = None

        # self.nomination_rounds = value.hash : [round_number: timestamp, ]

        # round_time = "simulation_time + n"

        # TODO: Consider making a special structure to store messages on nodes!

        self.storage = storage if storage is not None else Storage(self)
        default_state = {'voted': [], 'accepted': [], 'confirmed': []}
        self.nomination_state = copy.deepcopy(default_state)
        self.balloting_state = copy.deepcopy(default_state)
        self.statement_counter = {} # This hashmap (or dictionary) keeps track of all Values added and how many times unique nodes have made statements on it
        # This dictionary looks like this {Value_hash: {'voted': {node_id: count,...}}, {'accepted': {node_id:count}}}
        self.broadcast_flags = []  # Add every message here for other
        self.received_broadcast_msgs = {} # This hashmap (or dictionary) keeps track of all Messages retrieved by each node
        # This dictionary looks like this {{node.name: SCPNominate,...},...}
        self.priority_list = set()

        #  TODO: function get/retrieve nomination round which gets nomination round based on current global sim time - not class variable, but running function
        #   this needs time of externalise - to compare with sim time (what is time 1?)
        #   Rounds are node-specific: Use timestamp of most recent tx in Value as finalise time
        #   This allows for synchroncity as all nodes will agree on this timestamp

        self.nomination_round = 1
        self.last_nomination_start_time = 0.0

        ###################################
        # PREPARE BALLOT PHASE STRUCTURES #
        ###################################
        self.balloting_state = {'voted': {}, 'accepted': {}, 'confirmed': {}, 'aborted': {}} # This will look like: self.balloting_state = {'voted': {'value_hash_1': SCPBallot(counter=1, value=ValueObject1),},'accepted': { 'value_hash_2': SCPBallot(counter=3, value=ValueObject2)},'confirmed': { ... },'aborted': { ... }}
        self.ballot_statement_counter = {} # This will use sets for node names as opposed to counts, so will look like: {SCPBallot1.value: {'voted': set(Node1), ‘accepted’: set(Node2, Node3), ‘confirmed’: set(), ‘aborted’: set(), SCPBallot2.value: {'voted': set(), ‘accepted’: set(), ‘confirmed’: set(), ‘aborted’: set(node1, node2, node3)}
        self.ballot_prepare_broadcast_flags = set() # Add every SCPPrepare message here - this will look like
        self.received_prepare_broadcast_msgs = {}
        self.prepared_ballots = {} # This looks like: self.prepared_ballots[ballot.value] = SCPPrepare('aCounter': aCounter,'cCounter': cCounter,'hCounter': hCounter,'highestCounter': ballot.counter)

        ###################################
        # SCPCOMMIT BALLOT PHASE STRUCTURES #
        ###################################
        self.commit_ballot_state = {'voted': {}, 'accepted': {}, 'confirmed': {}} # This will look like: self.balloting_state = {'voted': {'value_hash_1': SCPBallot(counter=1, value=ValueObject1),},'accepted': { 'value_hash_2': SCPBallot(counter=3, value=ValueObject2)},'confirmed': { ... },'aborted': { ... }}
        self.commit_ballot_statement_counter = {} # This will use sets for node names as opposed to counts, so will look like: {SCPBallot1.value: {'voted': set(Node1), ‘accepted’: set(Node2, Node3), ‘confirmed’: set(), ‘aborted’: set(), SCPBallot2.value: {'voted': set(), ‘accepted’: set(), ‘confirmed’: set(), ‘aborted’: set(node1, node2, node3)}
        self.commit_ballot_broadcast_flags = set() # Add every SCPPrepare message here - this will look like
        self.received_commit_ballot_broadcast_msgs = {}
        self.committed_ballots = {} # This looks like: self.prepared_ballots[ballot.value] = SCPPrepare('aCounter': aCounter,'cCounter': cCounter,'hCounter': hCounter,'highestCounter': ballot.counter)

        ###################################
        # EXTERNALIZE PHASE STRUCTURES    #
        ###################################
        self.externalize_broadcast_flags = set() # Change to store (slot, message) tuples
        self.externalized_slot_counter = set()
        self.peer_externalised_statements = {} # This will be used to track finalised slots for nodes, so will look like: {Node1: set(SCPExternalize(ballot, 1), SCPExternalize(ballot2, 3), Node2:{})}

        # TODO: Implement the logic for advancing the nomination rounds each n+1 seconds!

        # Although nomination rounds are synchronous (they last for "1+n" seconds), we don't have
        # to implement them with sychronous events, but rather just allow each node to update
        # its state appropriately once its turn comes. Node check their time each time they update
        # and advance to another round if enough time has passed.

        log.node.info('Initialized node %s, quorum_set=%s, ledger=%s, storage=%s.',
                      self.name,
                      self.quorum_set,
                      self.ledger,
                      self.storage)


        self.log_path = 'simulator_events_log.txt'

    def remove_finalized_transactions(self, finalized_value):
        """
        Remove all Values from all data structures where any transaction in the finalized value appears.
        """
        finalized_transactions = set(finalized_value.transactions)  # Extract finalized transactions

        def filter_values(state_dict):
            """
            Helper function to remove values containing finalized transactions.
            """
            for key in state_dict.keys():
                state_dict[key] = [
                    value for value in state_dict[key]
                    if hasattr(value, "transactions") and not finalized_transactions.intersection(value.transactions)
                ]

        def filter_ballots(state_dict):
            """
            Helper function to remove ballots where their value contains finalized transactions.
            """
            for key in list(state_dict.keys()):  # Iterate over keys to avoid modifying the dict while iterating
                ballot = state_dict[key]  # Each entry is an SCPBallot
                if hasattr(ballot.value, "transactions") and finalized_transactions.intersection(
                        ballot.value.transactions):
                    del state_dict[key]  # Remove the ballot if any transaction is finalized

        # Filter nomination state (contains Value objects)
        filter_values(self.nomination_state)

        # Filter balloting state (contains SCPBallot objects)
        for state in ['voted', 'accepted', 'confirmed', 'aborted']:
            if state in self.balloting_state:
                filter_ballots(self.balloting_state[state])

        # Remove entries from statement_counter that contain finalized transactions
        self.statement_counter = {
            value: count for value, count in self.statement_counter.items()
            if hasattr(value, "transactions") and not finalized_transactions.intersection(value.transactions)
        }

        log.node.info("Node %s removed all values and ballots containing finalized transactions.", self.name)

    #### LOGGER FUNCTION
    def log_to_file(self, message):
        with open(self.log_path, 'a') as log_file:
            log_file.write(f"{Globals.simulation_time:.2f} - {message}\n")

    def __repr__(self):
        return '[Node: %s]' % self.name

    def __eq__(self, name):
        return self.name == name

    # To make Node hashable so that we can store them in a Set or as keys in dictionaries.
    def __hash__(self):
        return hash(self.name)

    # TODO: Not really used now, but just to show that we can have node specific events.
    @classmethod
    def get_events(cls):
        events = [Event('node')]
        log.consensus.info('Sending Node events %s.' %events)
        return events

    def extract_transaction_id(self, transaction):
        return transaction.hash

    def is_transaction_in_externalized_slots(self, transaction_id):
        # TODO: Check the validity of the transaction in the retrieve_transactions_from_mempool() in Node!
        for externalized_message in self.externalized_slot_counter:
            ballot = externalized_message.ballot
            if ballot and hasattr(ballot, 'value') and hasattr(ballot.value, 'transactions'):
                if any(tx.hash == transaction_id for tx in ballot.value.transactions):
                    return True
        return False

    def is_message_externalized(self, message):
        """
        Checks if the transactions in a broadcast message have been externalized (approved).
        This is just an example, you should define it according to your externalization criteria.
        """
        for value in message.voted:
            if hasattr(value, 'transactions'):
                for tx in value.transactions:
                    if self.is_transaction_in_externalized_slots(tx.hash):
                        return True
        # Check the 'accepted' values
        for value in message.accepted:
            if hasattr(value, 'transactions'):
                for tx in value.transactions:
                    if self.is_transaction_in_externalized_slots(tx.hash):
                        return True
        return False


    def calculate_nomination_round(self):
        """
        A node always begins nomination in round "1". Round "n" lasts for
        "1+n" seconds, after which, if no value has been confirmed nominated,
        the node proceeds to round "n+1". A node continues to echo votes
        from the highest priority neighbor in prior rounds as well as the
        current round. In particular, until any value is confirmed
        nominated, a node continues expanding its "voted" field with values
        nominated by highest priority neighbors from prior rounds even when
        the values appeared after the end of those prior rounds
        """
        if self.slot <= 0 or not self.ledger.get_slot(self.slot - 1): # check that there is a slot which externalised
            log.node.error("No externalized message available for previous slot.")
            return None

        previous_slot_message = self.ledger.get_slot(self.slot - 1)
        previous_timestamp = previous_slot_message.timestamp

        current_time = Globals.simulation_time
        time_diff = current_time - previous_timestamp
        self.last_nomination_start_time = current_time

        round = 1
        cumulative_time = 1 + round  # the finish time of round 1 is 1 + 1 = 2

        while time_diff > cumulative_time:
            round += 1
            cumulative_time += (1 + round)  # add the duration of the next round

        log.node.debug('Node %s is in round %d based on the timestamp of slot %d (time difference: %.2f seconds)',
                       self.name, round, self.slot - 1, time_diff)

        return round

    def check_update_nomination_round(self):
        """
        1. increase nomination round count and update priority list
        2. Each round lasts (1+round) - so check if last nomination start time + nomination_round < global.simulation_time, and update if True
        """
        if Globals.simulation_time > (self.last_nomination_start_time + self.nomination_round):
            self.nomination_round += 1
            self.get_priority_list()
            log.node.info("Node %s updated its Nomination Round to %s", self.name, self.nomination_round)


    def retrieve_transaction_from_mempool(self):
        if not os.path.exists(self.log_path):
            with open(self.log_path, 'w') as log_file:
                log_file.write("")

        transaction = self.mempool.get_transaction()
        if transaction:
            transaction_id = self.extract_transaction_id(transaction)

            if not self.is_transaction_in_externalized_slots(transaction_id):
                log.node.info('Node %s retrieved %s from mempool.', self.name, transaction)
                self.log_to_file(f"NODE - INFO - Node {self.name} retrieved {transaction} from mempool.")
                self.ledger.add(transaction)
            else:
                log.node.info('Node %s ignored transaction %s as it was already externalized.', self.name, transaction_id)
                self.log_to_file(f"NODE - INFO - Node {self.name} ignored {transaction} as it was already externalized.")
        else:
            log.node.info('Node %s cannot retrieve transaction from mempool because it is empty!', self.name)

    # Add nodes to quorum
    # TODO: Consider removing add_to_quorum() because we are only using set_quorum()!
    def add_to_quorum(self, nodes):
        self.quorum_set.add(nodes)
        return

    # Set quorum to the nodes
    def set_quorum(self, nodes, inner_sets, threshold=None):
        if threshold is not None:
            self.quorum_set.threshold = threshold
        self.quorum_set.set(nodes=nodes, inner_sets=inner_sets)
        return

    def attach_mempool(self, mempool):
        self.mempool = mempool
        return

    # TODO: URGENT! Keep track which transactions are already included in the ledger and broadcasted!
    # TODO: - We can do it on the level of Ledger (better) or Transactions (worse)!

    # TODO: URGENT! At beginning of nominate(), combine all values in storage and then nominate!
    # TODO: - Use Value.combine() for combining multiple values into one!

    def nominate(self):
        """
        Broadcast SCPNominate message to the storage.
        """
        # TODO: A node can nominate a value itself if it has the highest priority in the current round.
        #  If it does not have the highest priority, it waits for higher-priority nodes to propose values before deciding what to nominate
        if any(self.balloting_state[state] for state in ['voted', 'accepted', 'confirmed', 'aborted']):
            log.node.info("Node %s is skipping message processing as it already has ballots in balloting_state.",
                          self.name)
            return
        self.check_update_nomination_round()
        self.get_priority_list()
        if self.name in self.priority_list:
            self.prepare_nomination_msg() # Prepares Values for Nomination and broadcasts message
        else:
            log.node.info("Node %s did not Nominate a Value since it is not in it's priority list", self.name)
        #self.prepare_nomination_msg()
        # self.prepare_nomination_msg()  # Prepares Values for Nomination and broadcasts message
        #priority_node = self.get_highest_priority_neighbor()

        # TODO: Neighbour should check global time & priority neighbour
        # TODO: nominate function should update nominations from peers until the quorum threshold is met
        # TODO: the respective function should be implemented and called here
        return

    def retrieve_broadcast_message(self, requesting_node):
        """
        Retrieve a broadcast message for a requesting node.
        If a message has approved transactions (i.e., it's been externalized),
        remove it from the broadcast flags.
        """
        if len(self.broadcast_flags) > 0:
            if requesting_node.name not in self.received_broadcast_msgs:
                retrieved_message = np.random.choice(self.broadcast_flags)
                self.received_broadcast_msgs[requesting_node.name] = [retrieved_message]
                return retrieved_message

            elif len(self.received_broadcast_msgs[requesting_node.name]) != len(self.broadcast_flags):
                statement = True
                while statement:
                    # Choose a random message to retrieve
                    retrieved_message = np.random.choice(self.broadcast_flags)
                    if retrieved_message not in self.received_broadcast_msgs[requesting_node.name]:
                        if self.is_message_externalized(retrieved_message):
                            # Remove from broadcast flags if externalized
                            self.broadcast_flags.remove(retrieved_message)

                        # Add the message to the received list for the requesting node
                        self.received_broadcast_msgs[requesting_node.name].append(retrieved_message)
                        return retrieved_message
        return None


    def receive_message(self):
        if any(self.balloting_state[state] for state in ['voted', 'accepted', 'confirmed', 'aborted']):
            log.node.info("Node %s is skipping message processing as it already has ballots in balloting_state.",
                          self.name)
            return

        self.check_update_nomination_round()
        self.get_priority_list()
        priority_node = self.get_highest_priority_neighbor()
        if priority_node != self:
            message = self.retrieve_broadcast_message(priority_node)

            if message is not None:
                message = message.parse_message_state(message) # message is an array of 2 arrays, the first being the voted values and the second the accepted values
                self.process_received_message(message)
                self.update_statement_count(priority_node, message)
                log.node.info('Node %s retrieving messages from his highest priority neighbor Node %s!', self.name,priority_node.name)

                voted_val = message[0] # message[0] is voted field
                if type(voted_val) is Value and self.check_Quorum_threshold(voted_val):

                    log.node.info('Quorum threshold met for voted value %s at Node %s', voted_val, self.name)
                    self.update_nomination_state(voted_val, "voted")

                if type(voted_val) is Value and self.check_Blocking_threshold(voted_val):
                    log.node.info('Blocking threshold met for value %s at Node %s', voted_val, self.name)

                accepted_val = message[1] # message[1] is accepted field
                if type(accepted_val) is Value and self.check_Quorum_threshold(accepted_val):

                    log.node.info('Quorum threshold met for accepted value %s at Node %s', accepted_val, self.name)
                    self.update_nomination_state(accepted_val, "accepted")

                if type(accepted_val) is Value and self.check_Blocking_threshold(accepted_val):
                    log.node.info('Blocking threshold met for value %s at Node %s', accepted_val, self.name)

            else:
                log.node.info('Node %s has no messages to retrieve from his highest priority neighbor Node %s!', self.name, priority_node.name)

    def process_received_message(self, message):
        incoming_voted = message[0]
        incoming_accepted = message[1]

        if type(incoming_voted) == Value and self.is_duplicate_value(incoming_voted, self.nomination_state['voted']) == False:
                self.nomination_state['voted'].append(incoming_voted)
                log.node.info('Node %s has updated its voted field in nomination state')

        if type(incoming_accepted) == Value: # If it's a Value it means that there are transactions to be combined
                self.nomination_state['accepted'].append(incoming_accepted)
                log.node.info('Node %s has updated its accepted field in nomination state')

    def retrieve_message_from_peer(self):
        """
        Retrieve a message from a random peer.
        """

        # Update nomination round and priority list if simulation time exceeds nominatoin round time and
        # choose a neighbor with the highest priority from which we fetch messages
        other_node = self.get_highest_priority_neighbor()
        print("OTHER NODE IS ", other_node)

        if other_node is None:
            log.node.info('Node %s has no one in quorum set!',self.name)
            return

        if other_node is not self:
            log.node.info('Node %s retrieving messages from his highest priority neighbor Node %s!',
                          self.name,other_node.name)
            retrieved_messages = other_node.get_messages()
            if retrieved_messages is not None:
                self.storage.add_messages(retrieved_messages)
            else:
                log.node.info('Node %s has no messages to retrieve from his highest priority neighbor Node %s!',
                              self.name,other_node.name)
        else:
            log.node.info('Node %s is his own highest priority neighbor!',self.name)
        return

    def prepare_nomination_msg(self):
        voted_vals = []
        accepted_vals = []

        self.retrieve_transaction_from_mempool()

        finalised_transactions = set()
        for externalized_message in self.externalized_slot_counter: # Filter out transactions already externalized
            ballot = externalized_message.ballot
            if ballot and hasattr(ballot, 'value') and hasattr(ballot.value, 'transactions'):
                finalised_transactions.update(tx.hash for tx in ballot.value.transactions)

        filtered_transactions = {tx for tx in self.ledger.transactions if tx.hash not in finalised_transactions} # Filter to exclude finalised transactions

        if filtered_transactions:
            voted_vals.append(Value(transactions=filtered_transactions))
            self.nomination_state['voted'].extend(voted_vals)

        if self.nomination_state['accepted']:
            accepted_vals.extend(self.nomination_state['accepted'])  # Add all accepted values

        if not voted_vals and not accepted_vals:
            log.node.info('Node %s has no transactions or accepted values to nominate!', self.name)
            return

        message = SCPNominate(voted=voted_vals, accepted=accepted_vals, broadcasted=True)

        self.storage.add_messages(message)
        self.broadcast_flags.append(message)
        log.node.info('Node %s appended SCPNominate message to its storage and state, message = %s', self.name, message)

    def get_messages(self):
        if len(self.storage.messages) == 0:
            messages = None
            log.node.info('Node %s: No messages to retrieve!',self.name)
        else:
            # TODO: Implement get_messages() in Storage which returns copy of the messages!
            messages = self.storage.messages.copy()
        return messages

    def update_statement_count(self, other_node, message):
        incoming_voted = message[0]
        incoming_accepted = message[1]

        if type(incoming_accepted) == Value:
            if incoming_accepted.hash in self.statement_counter:
                    if other_node.name not in self.statement_counter[incoming_accepted.hash]['accepted']:
                        # As value has a dictionary but this node isn't in it, simpy set the node counter to 1
                        self.statement_counter[incoming_accepted.hash]['accepted'][other_node.name] = 1
                        log.node.info('Node %s has set an accepted statement counter for Node %s with nominated value!', self.name, other_node.name)
            else:
                # Initiate dictionary for value & accepted for the value and then add the count for the node
                self.statement_counter[incoming_accepted.hash] = {"voted": {}, "accepted": {}}
                self.statement_counter[incoming_accepted.hash]['accepted'][other_node.name] = 1
                log.node.info('Node %s has added an accepted statement counter for Node %s with nominated values!', self.name, other_node.name)

        if type(incoming_voted) == Value:
                if incoming_voted.hash in self.statement_counter:
                        if other_node.name not in self.statement_counter[incoming_voted.hash]['voted']:
                            self.statement_counter[incoming_voted.hash]['voted'][other_node.name] = 1
                            log.node.info('Node %s has added an accepted statement counter for Node %s with nominated values!',self.name, other_node.name)

                else:
                    self.statement_counter[incoming_voted.hash] = {"voted": {}, "accepted": {}}
                    self.statement_counter[incoming_voted.hash]['voted'] = {other_node.name: 1}
                    log.node.info('Node %s has set its voted statement counter for %s with nominated values!', self.name, other_node.name)

    # In round "n" of slot "i", each node determines an additional
    # peer whose nominated values it should incorporate in its own
    # "SCPNominate" message as follows:

    # TODO: Consider making some of these priority functions as class methods of Node or QuorumSet!

    # - Let "Gi(m) = SHA-256(i || m)", where "||" denotes the
    #   concatenation of serialized XDR values.  Treat the output of "Gi"
    #   as a 256-bit binary number in big-endian format.
    def Gi(self, values):
        """
        Computes the Gi function: SHA-256(i || m) as per SCP specifications.
        """
        # Ensure values is always a list
        if not isinstance(values, list):
            values = [values]

        # Concatenate XDR serialized values
        packer = xdrlib3.Packer()

        # Slot value "i" is implicitly passed as the first value to Gi!
        packer.pack_int(self.slot)

        for value in values:
            if isinstance(value, str):
                packer.pack_bytes(value.encode('utf-8'))
            elif isinstance(value, int):
                packer.pack_int(value)
            elif isinstance(value, bytes):  # Directly handle bytes
                packer.pack_bytes(value)
            elif hasattr(value, "serialize_xdr"):  # Assume custom serialization for objects
                packer.pack_bytes(value.serialize_xdr())
            else:
                raise TypeError(f"Unsupported value type in Gi: {type(value)}")

        packed_data = packer.get_buffer()

        # Compute SHA-256 hash and interpret as a big-endian integer
        hash_bytes = hashlib.sha256(packed_data).digest()

        # Convert the hash bytes to a big-endian integer
        return int.from_bytes(hash_bytes, byteorder='big')

    # - For each peer "v", define "weight(v)" as the fraction of quorum
    #   slices containing "v".
    def weight(self,v):
        # TODO: Because our QuorumSet only has a single slice, the weight is 1.0 for all peers!
        # TODO: Implement get_weight() in QuorumSet and expand it to have multiple slices!
        # return self.quorum_set.get_weight(v)
        return 1.0

    # - Define the set of nodes "neighbors(n)" as the set of nodes v for
    #   which "Gi(1 || n || v) < 2^{256} * weight(v)", where "1" and "n"
    #   are both 32-bit XDR "int" values.  Note that a node is always its
    #   own neighbor because conceptually a node belongs to all of its own
    #   quorum slices.

    # Because Gi(1 || n || v) is a random function with a maximum value of 2^{256}, this formula effectivelly
    # selects a peer as a neighbor with a probability equal to its weight!

    def get_priority_list(self): # TODO: RENAME TO GET_HIGHPRIORITY_NODES/LIST
        unique_nodes = set()  # Use set to avoid duplication - used to check for duplicates in loops

        for node in self.quorum_set.get_nodes():
            # print("Weight for node ", node.name, " : ", self.quorum_set.weight(node))
            # print("self.Gi([1, self.nomination_round, node.name]) returns ", self.Gi([1, self.nomination_round, node.name]), " for node ", node.name)
            # print(" this is less than ", (2 ** 256 * self.quorum_set.weight(node)), self.Gi([1, self.nomination_round, node.name]) < (2 ** 256 * self.quorum_set.weight(node)))
            if self.Gi([1, self.nomination_round, str(node.name)]) < (2 ** 256 * self.quorum_set.weight(node)):
                unique_nodes.add(node)  # Add to set

        for inner_set in self.quorum_set.get_inner_sets():
            if type(inner_set) is list:
                for node in inner_set:
                    if self.Gi([1, self.nomination_round, node.name]) < (2 ** 256 * self.quorum_set.weight(node)) and node not in unique_nodes:
                        unique_nodes.add(node)
            else:
                if self.Gi([1, self.nomination_round, inner_set.name]) < (
                        2 ** 256 * self.quorum_set.weight(inner_set)) and inner_set not in unique_nodes:
                    unique_nodes.add(inner_set)
        # print("For node ", node.name, " the priority nodes are ", unique_nodes)
        self.priority_list.update(unique_nodes)
        print("PRIORITY LIST FOR ", self.name, " IS ", self.priority_list)
        return unique_nodes

    # - Define "priority(n, v)" as "Gi(2 || n || v)", where "2" and "n"
    #   are both 32-bit XDR "int" values.
    def priority(self,v):
        return self.Gi([2,self.nomination_round,v.name])

    def get_highest_priority_neighbor(self):
        self.check_update_nomination_round()
        neighbors = self.priority_list
        if len(neighbors) < 1:  # Avoid empty sequence error
            log.node.warning('Node %s has no priority list!', self.name)
            print("nodes quorum set is ", self.quorum_set.nodes, " ", self.quorum_set.inner_sets)
            return self  # Return self or handle the case differently
        print("GOING TO RETURN",  max(neighbors, key=self.priority), "with type", type(max(neighbors, key=self.priority)))
        return max(neighbors, key=self.priority)

    def is_duplicate_value(self, other_val, current_vals):
        for val in current_vals:
            if other_val == val:
                return True
        return False

    # TODO: Call this after receiving a message + Update state in this event once its met
    def check_Quorum_threshold(self, val):
        # Check for Quorum threshold:
        # 1. the node itself has signed the message
        # 2. Number of nodes in the current QuorumSet who have signed + the number of innerSets that meet threshold is at least k
        # 3. These conditions apply recursively to the inner sets to fulfill condition 2.
        if val in (self.nomination_state["voted"]) or val in (self.nomination_state["accepted"]): # Condition 1. - node itself has signed message
            signed_count = 1 # Node itself has voted for it so alrady has a count of 1
            inner_sets_meeting_threshold_count = 0
            nodes, inner_sets = self.quorum_set.get_quorum()
            threshold = self.quorum_set.minimum_quorum

            for node in nodes:
                # check if the node name from the quorum is in the value's voted or accepted dict - meaning it has voted for the message
                if node.name in self.statement_counter[val.hash]['voted'] or node.name in self.statement_counter[val.hash]['accepted']:
                    signed_count += 1

            for element in inner_sets: # Keep to just 1 layer of depth for now - so only 1 inner set per quorum, [ [], [] ], not [ [], [[]] ]
                if isinstance(element, list):
                        # 2. Check if the innerSets meet threshold
                        threshold_met = self.quorum_set.check_threshold(val=val, quorum=element, threshold=threshold, node_statement_counter=self.statement_counter.copy())
                        if threshold_met:
                            inner_sets_meeting_threshold_count += 1

            if signed_count + inner_sets_meeting_threshold_count >= threshold: # 3. conditions apply recursively to the inner sets to fulfill condition 2
                return True
            else:
                return False
        else:
            return False

    def check_Blocking_threshold(self, val):
        # Check for Blocking threshold:
        # A message reaches blocking threshold at "v" when the number of
        # "validators" making the statement plus (recursively) the number
        # "innerSets" reaching blocking threshold exceeds "n-k".
        # Blocking threshold is met when  at least one member of each of "v"'s
        # quorum slices (a set that does not necessarily include "v" itself) has issued message "m"
        if val in (self.nomination_state["voted"]) or val in (self.nomination_state["accepted"]):  # Condition 1. - node itself has signed message
            signed_count = 1
            validators, inner_sets = self.quorum_set.get_quorum()
            n = len(validators)
            seen = set()
            for node in validators:
                seen.add(node)

            for element in inner_sets:
                if isinstance(element, list):
                    for node in element:
                        if node not in seen:
                            n += 1
                            seen.add(node)

            k = self.quorum_set.minimum_quorum

            if n == 0:
                return False

            signed_seen = set()
            for node in validators:
                if node.name != self.name and (node in self.statement_counter[val.hash]["voted"] or node in self.statement_counter[val.hash]["accepted"]) and (node not in signed_seen):
                    signed_count += 1
                    signed_seen.add(node)

            inner_set_count = 0
            for slice in inner_sets:
                if isinstance(slice, list):
                    inner_set_count += self.quorum_set.check_inner_set_blocking_threshold(calling_node=self, val=val, quorum=slice)

            return (signed_count + inner_set_count) > (n - k)

        return False

    def update_nomination_state(self, val, field):
        if field == "voted":
            if len(self.nomination_state["voted"]) > 0 :
                if val in self.nomination_state['accepted']:
                    log.node.info('Value %s is already accepted in Node %s', val, self.name)
                    return

                if val in self.nomination_state['voted']:
                    self.nomination_state['voted'].remove(val)

                self.nomination_state['accepted'].append(val)
                log.node.info('Value %s has been moved to accepted in Node %s', val, self.name)
            else:
                log.node.info('No values in voted state, cannot move Value %s to accepted in Node %s', val, self.name)

        elif field == "accepted":
            if len(self.nomination_state["accepted"]) > 0:
                if val in self.nomination_state['confirmed']:
                    log.node.info('Value %s is already confirmed in Node %s', val, self.name)
                    return

                if val in self.nomination_state['accepted']:
                    self.nomination_state['accepted'].remove(val)

                self.nomination_state['confirmed'].append(val)
                log.node.info('Value %s has been moved to confirmed in Node %s', val, self.name)
            else:
                log.node.info('No values in accepted state, cannot move Value %s to confirmed in Node %s', val, self.name)

    # retrieve a confirmed Value from nomination_state
    def retrieve_confirmed_value(self):
        if len(self.nomination_state['confirmed']) > 0:
            confirmed_value = np.random.choice(self.nomination_state['confirmed'])  # Take a random Value from the confirmed state
            log.node.info('Node %s retrieved confirmed value %s for SCPPrepare', self.name, confirmed_value)
            return confirmed_value
        else:
            log.node.info('Node %s has no confirmed values to use for SCPPrepare!', self.name)
            return None

    # Get the counters for balloting state given a value
    def get_prepared_ballot_counters(self, value):
        return self.prepared_ballots.get(value)

    def prepare_ballot_msg(self):
        """
        Prepare Ballot for Prepare Balloting phase
        """
        if len(self.nomination_state['confirmed']) == 0: # Check if there are any values to prepare
            log.node.info('Node %s has no confirmed values in nomination state to prepare for balloting.', self.name)
            return

        # Retrieve a Value from the Nomination 'confirmed' state
        confirmed_val = self.retrieve_confirmed_value()
        # If the value has been aborted in the past then it should not be prepared
        if confirmed_val.hash in self.balloting_state['aborted']:
            log.node.info('Node %s has aborted ballot %s previously, so it cannot be prepared.', self.name,
                          confirmed_val.hash)
            return

        if len(self.balloting_state['voted']) > 0 and confirmed_val.hash in self.balloting_state['voted']:
            # Retrieve the counter from the state and increase it by one for the new ballot to be created
            new_counter = self.balloting_state['voted'][confirmed_val.hash].counter + 1
            self.balloting_state['voted'][confirmed_val.hash].counter += 1
            ballot = SCPBallot(counter=new_counter, value=confirmed_val)
            log.node.info('Node %s created SCPBallot with larger count: %s', self.name, ballot.value)
        else:
            # Make ballot with default counter of 1
            ballot = SCPBallot(counter=1, value=confirmed_val)
            log.node.info('Node %s created SCPBallot: %s', self.name, ballot.value)

        if not self.check_if_finalised(ballot):
            # Get counters for new SCPPrepare message
            prepare_msg_counters = self.get_prepared_ballot_counters(confirmed_val)
            if prepare_msg_counters is not None:
                prepare_msg = SCPPrepare(ballot=ballot, aCounter=prepare_msg_counters.aCounter, cCounter=prepare_msg_counters.cCounter, hCounter=prepare_msg_counters.hCounter)
                log.node.info('Node %s has increased counter on prepared SCPPrepare message with ballot %s, h_counter=%d, a_counter=%d, c_counter=%d.',self.name, confirmed_val, prepare_msg_counters.aCounter, prepare_msg_counters.cCounter,prepare_msg_counters.hCounter)
                self.ballot_prepare_broadcast_flags.add(prepare_msg)
                self.prepared_ballots[ballot.value] = prepare_msg
                if ballot.value not in self.ballot_statement_counter:
                    self.ballot_statement_counter[ballot.value] = {'voted': set(), 'accepted': set(), 'confirmed':set(), 'aborted':set()}
                    self.ballot_statement_counter[ballot.value]['voted'] = set()
                    self.ballot_statement_counter[ballot.value]['voted'].add(self)
            else:
                # If prepare_msg_counters is none then there are no counters for this value and we have to set the defaults
                prepare_msg = SCPPrepare(ballot=ballot)
                self.ballot_prepare_broadcast_flags.add(prepare_msg)
                self.prepared_ballots[ballot.value] = prepare_msg
                self.balloting_state['voted'][confirmed_val.hash] = ballot
                if ballot.value not in self.ballot_statement_counter:
                    self.ballot_statement_counter[ballot.value] = {'voted': set(), 'accepted': set(), 'confirmed':set(), 'aborted':set()}
                    self.ballot_statement_counter[ballot.value]['voted'] = set()
                    self.ballot_statement_counter[ballot.value]['voted'].add(self)
                log.node.info('Node %s has prepared SCPPrepare message with ballot %s, h_counter=%d, a_counter=%d, c_counter=%d.', self.name, confirmed_val, 0, 0,0)

            log.node.info('Node %s appended SCPPrepare message to its storage and state, message = %s', self.name, prepare_msg)
        else:
            log.node.info('Node %s has not prepared SCPPrepare message as the ballot %s has already been finalised', self.name, ballot)

    def process_prepare_ballot_message(self, message, sender):
        received_ballot = message.ballot

        # This will look like: self.balloting_state = {'voted': {'value_hash_1': SCPBallot(counter=1, value=ValueObject1),},'accepted': { 'value_hash_2': SCPBallot(counter=3, value=ValueObject2)},'confirmed': {

        # Case 1: New ballot received has the same value but a higher counter
        if received_ballot.value.hash in self.balloting_state['voted']:
            if received_ballot.value == self.balloting_state['voted'][received_ballot.value.hash].value and received_ballot.counter > self.balloting_state['voted'][received_ballot.value.hash].counter:
                log.node.info("Node %s received a ballot with the same value but a higher counter. Updating to the new counter.", self.name)
                self.balloting_state['voted'][received_ballot.value.hash] = received_ballot
                if received_ballot.value not in self.ballot_statement_counter:
                    self.ballot_statement_counter[received_ballot.value] = {'voted': set(), 'accepted': set(), 'confirmed': set(), 'aborted': set()}
                    self.ballot_statement_counter[received_ballot.value]['voted'].add(sender)

                else:
                    self.ballot_statement_counter[received_ballot.value]['voted'].add(sender)
                return

            # Case 3: New ballot received has the same value but a lower counter
            if received_ballot.counter < self.balloting_state['voted'][received_ballot.value.hash].counter:
                log.node.info("Node %s that has been received has the same value but a lower counter than a previously voted ballot.", self.name)
                if received_ballot.value not in self.ballot_statement_counter:
                    self.ballot_statement_counter[received_ballot.value] = {'voted': set(),'accepted': set(),'confirmed': set(),'aborted': set()}
                    self.ballot_statement_counter[received_ballot.value]['voted'].add(sender)
                else:
                    self.ballot_statement_counter[received_ballot.value]['voted'].add(sender)
                return

        elif received_ballot.value.hash not in self.balloting_state['voted']:
            for voted_ballot in self.balloting_state['voted'].values():
                # Case 2: New ballot received has different value and a higher counter
                if received_ballot.counter > voted_ballot.counter:
                    log.node.info("Node %s received a ballot with a different value and a higher counter. Aborting previous ballots.",self.name)
                    # Abort any previous ballots with a smaller counter and different value
                    self.abort_ballots(received_ballot)
                    self.balloting_state['voted'][received_ballot.value.hash] = received_ballot
                    if received_ballot.value not in self.ballot_statement_counter:
                        self.ballot_statement_counter[received_ballot.value] = {'voted': set(), 'accepted': set(),'confirmed': set(), 'aborted': set()}
                        self.ballot_statement_counter[received_ballot.value]['voted'].add(sender)
                    else:
                        self.ballot_statement_counter[received_ballot.value]['voted'].add(sender)
                    return

            # Case 4: New ballot received has different value and a lower counter - JUST abort this received ballot
            self.balloting_state['aborted'][received_ballot.value.hash] = received_ballot
            if received_ballot.value not in self.ballot_statement_counter:
                self.ballot_statement_counter[received_ballot.value] = {'voted': set(), 'accepted': set(),'confirmed': set(), 'aborted': set()}
                self.ballot_statement_counter[received_ballot.value]['aborted'].add(sender)
            else:
                if sender in self.ballot_statement_counter[received_ballot.value]['voted']:
                    self.ballot_statement_counter[received_ballot.value]['voted'].remove(sender)
                self.ballot_statement_counter[received_ballot.value]['aborted'].add(sender)
            log.node.info("Node %s has a different value and lower counter than a previously voted value. Aborting this ballot.")

    def abort_ballots(self, received_ballot):
        voted_ballots_to_del = []
        accepted_ballots_to_del = []

        # Abort all ballots from 'voted' field that have a lower counter
        for ballot in self.balloting_state['voted'].values():
            if ballot.counter < received_ballot.counter:
                if ballot.value.hash != received_ballot.value.hash: # every ballot less than "b" containing a value other than "b.value"
                    self.balloting_state['aborted'][ballot.value.hash] = ballot
                    voted_ballots_to_del.append(ballot.value.hash)

        for ballot in voted_ballots_to_del:
            self.balloting_state['voted'].pop(ballot)

        # Abort all Values from 'accepted' field that have a lower counter
        for ballot in self.balloting_state['accepted'].values():
            if ballot.counter < received_ballot.counter:
                if ballot.value.hash != received_ballot.value.hash:
                    self.balloting_state['aborted'][ballot.value.hash] = ballot
                    accepted_ballots_to_del.append(ballot.value.hash)

        for ballot in accepted_ballots_to_del:
            self.balloting_state['accepted'].pop(ballot)


    def check_Prepare_Quorum_threshold(self, ballot):
        # Check for Quorum threshold:
        # 1. the node itself has signed the message
        # 2. Number of nodes in the current QuorumSet who have signed + the number of innerSets that meet threshold is at least k
        # 3. These conditions apply recursively to the inner sets to fulfill condition 2.
        if ballot.value.hash in (self.balloting_state["voted"]) or ballot.value.hash in (self.balloting_state["accepted"]): # Condition 1. - node itself has signed message
            signed_count = 1 # Node itself has voted for it so already has a count of 1
            inner_sets_meeting_threshold_count = 0
            nodes, inner_sets = self.quorum_set.get_quorum()
            threshold = self.quorum_set.minimum_quorum

            for node in nodes:
                # check if the node name from the quorum is in the value's voted or accepted dict - meaning it has voted for the message
                if node in self.ballot_statement_counter[ballot.value]['voted'] or node in self.ballot_statement_counter[ballot.value]['accepted']:
                    signed_count += 1

            for element in inner_sets: # Keep to just 1 layer of depth for now - so only 1 inner set per quorum, [ [], [] ], not [ [], [[]] ]
                if isinstance(element, list):
                        # 2. Check if the innerSets meet threshold
                        threshold_met = self.quorum_set.check_prepare_threshold(ballot=ballot, quorum=element, threshold=threshold, prepare_statement_counter=self.ballot_statement_counter.copy())
                        if threshold_met:
                            inner_sets_meeting_threshold_count += 1

            if signed_count + inner_sets_meeting_threshold_count >= threshold: # 3. conditions apply recursively to the inner sets to fulfill condition 2
                return True
            else:
                return False
        else:
            return False


    def update_prepare_balloting_state(self, ballot, field):
        if field == "voted":
            if len(self.balloting_state["voted"]) > 0 :
                if ballot.value.hash in self.balloting_state['accepted']:
                    log.node.info('Value %s is already accepted in Node %s', ballot.value, self.name)
                    return

                if ballot.value.hash in self.balloting_state['voted']:
                    self.balloting_state["accepted"][ballot.value.hash] = (self.balloting_state["voted"][ballot.value.hash])
                    self.balloting_state["voted"].pop(ballot.value.hash)
                    log.node.info('Ballot %s has been moved to accepted in Node %s', ballot, self.name)
            else:
                log.node.info('No ballots in voted state, cannot move Ballot %s to accepted in Node %s', ballot, self.name)

        elif field == "accepted":
            if len(self.balloting_state["accepted"]) > 0:
                if ballot.value.hash in self.balloting_state['confirmed']:
                    log.node.info('Ballot %s is already confirmed in Node %s', ballot, self.name)
                    return

                if ballot.value.hash in self.balloting_state['accepted']:
                    self.balloting_state["confirmed"][ballot.value.hash] = (self.balloting_state["accepted"][ballot.value.hash])
                    self.balloting_state["accepted"].pop(ballot.value.hash)

                log.node.info('Ballot %s has been moved to confirmed in Node %s', ballot.value.hash, self.name)
            else:
                log.node.info('No ballots in accepted state, cannot move Ballots %s to confirmed in Node %s', ballot, self.name)


    def retrieve_ballot_prepare_message(self, requesting_node):
        print("RUNNING RETRIEVE BALLOT MESSAGE")
        print("LENGTH OF PREPARE BROADCAST FLAG IS", len(self.ballot_prepare_broadcast_flags) )
        print("THE BROADCAST FLAG IS ", self.ballot_prepare_broadcast_flags)
        # Select a random ballot and check if its already been sent to the requesting_node
        if len(self.ballot_prepare_broadcast_flags) > 0:
            if requesting_node.name not in self.received_prepare_broadcast_msgs:
                retrieved_message = np.random.choice(list(self.ballot_prepare_broadcast_flags))
                self.received_prepare_broadcast_msgs[requesting_node.name] = [retrieved_message]
                return retrieved_message

            elif len(self.received_prepare_broadcast_msgs[requesting_node.name]) != len(list(self.ballot_prepare_broadcast_flags)):
                statement = True
                while statement:
                    retrieved_message = np.random.choice(list(self.ballot_prepare_broadcast_flags))
                    if retrieved_message not in self.received_prepare_broadcast_msgs[requesting_node.name]:
                        self.received_prepare_broadcast_msgs[requesting_node.name].append(retrieved_message)
                        return retrieved_message
        return None

    def receive_prepare_message(self):
        # self.ballot_statement_counter = {}
        # Looks like: {SCPBallot1.value: {'voted': set(Node1), ‘accepted’: set(Node2, Node3), ‘confirmed’: set(), ‘aborted’: set(), SCPBallot2.value: {'voted': set(), ‘accepted’: set(), ‘confirmed’: set(), ‘aborted’: set(node1, node2, node3)}

        sending_node = self.quorum_set.retrieve_random_peer(self)
        if sending_node is not None:
            if sending_node != self and not None:
                message = self.retrieve_ballot_prepare_message(sending_node)

                if message is not None and not self.check_if_finalised(message.ballot):
                    self.process_prepare_ballot_message(message, sending_node)
                    log.node.info('Node %s retrieving messages from his peer Node %s!', self.name,sending_node.name)
                    ballot = message.ballot # message[0] is voted field
                    if type(ballot) is SCPBallot and ballot.value.hash in self.balloting_state['voted'] and self.check_Prepare_Quorum_threshold(ballot):
                        log.node.info('Quorum threshold met for voted ballot %s at Node %s', ballot, self.name)
                        self.update_prepare_balloting_state(ballot, "voted")

                    elif type(ballot) is SCPBallot and ballot.value.hash in self.balloting_state['accepted'] and self.check_Prepare_Quorum_threshold(ballot):

                        log.node.info('Quorum threshold met for accepted ballot %s at Node %s', ballot, self.name)
                        self.update_prepare_balloting_state(ballot, "accepted")
                else:
                    log.node.info('Node %s has no SCPPrepare messages to retrieve from neighbor Node %s!', self.name, sending_node.name)
        else:
            log.node.info('Node %s could not retrieve peer!', self.name)

    def retrieve_confirmed_prepare_ballot(self):
        if len(self.balloting_state['confirmed']) > 0:
            # random_ballot_hash = np.random.choice(self.balloting_state['confirmed'])
            random_ballot_hash = np.random.choice(list(self.balloting_state['confirmed'].keys()))
            confirmed_prepare_ballot = self.balloting_state['confirmed'][random_ballot_hash]  # Take a random Value from the confirmed state
            log.node.info('Node %s retrieved confirmed prepared ballot %s for SCPCommit', self.name, confirmed_prepare_ballot)
            return confirmed_prepare_ballot
        else:
            log.node.info('Node %s has no confirmed prepared ballots to use for SCPCommit!', self.name)
            return None


    def prepare_SCPCommit_msg(self):
        """
        Prepare SCPCommit message for Commit Ballot phase
        """
        if len(self.balloting_state['confirmed']) == 0: # Check if there are any values to prepare
            log.node.info('Node %s has no confirmed values in nomination state to prepare for balloting.', self.name)
            return

        confirmed_ballot = self.retrieve_confirmed_prepare_ballot() # Retrieve a Value from the SCPPrepare 'confirmed' state
        if confirmed_ballot is not None:
            commit_msg = SCPCommit(ballot=confirmed_ballot, preparedCounter=confirmed_ballot.counter)
            self.commit_ballot_broadcast_flags.add(commit_msg)
            self.commit_ballot_state['voted'][confirmed_ballot.value.hash] = confirmed_ballot
            if confirmed_ballot.value not in self.commit_ballot_statement_counter:
                    self.commit_ballot_statement_counter[confirmed_ballot.value] = {'voted': set(), 'accepted': set(), 'confirmed':set(), 'aborted':set()}
                    self.commit_ballot_statement_counter[confirmed_ballot.value]['voted'] = set()
                    self.commit_ballot_statement_counter[confirmed_ballot.value]['voted'].add(self)
            log.node.info('Node %s has prepared SCPCommit message with ballot %s, preparedCounter=%d.', self.name, confirmed_ballot, confirmed_ballot.counter)
            log.node.info('Node %s appended SCPPrepare message to its storage and state, message = %s', self.name, commit_msg)
        log.node.info('Node %s could not retrieve a confirmed SCPPrepare messages from its peer!')

    def process_commit_ballot_message(self, message, sender):
        """
        The purpose of continuing to update the counter and send this field is to assist other nodes still in the PREPARE phase in synchronizing their counters.
        The update of the counter is done, but it doesn't help SCPPrepare as this doesnt affect prepared ballots due to commits & prepare messages being processed separately
        Also, we do not abort, just update counters if larger
        """
        received_ballot = message.ballot
        # This will look like: self.commit_ballot_state = {'voted': {'value_hash_1': SCPBallot(counter=1, value=ValueObject1),},'accepted': { 'value_hash_2': SCPBallot(counter=3, value=ValueObject2)},'confirmed': {

        # Case 1: New ballot received has the same value but a higher counter
        if received_ballot.value.hash in self.commit_ballot_state['voted']:
            if received_ballot.value == self.commit_ballot_state['voted'][received_ballot.value.hash].value and received_ballot.counter > self.commit_ballot_state['voted'][received_ballot.value.hash].counter:
                log.node.info("Node %s received a commit ballot with the same value but a higher counter. Updating to the new counter.", self.name)
                self.commit_ballot_state['voted'][received_ballot.value.hash] = received_ballot

                if received_ballot.value not in self.commit_ballot_statement_counter:
                    self.commit_ballot_statement_counter[received_ballot.value] = {'voted': set(), 'accepted': set(), 'confirmed': set(), 'aborted': set()}
                    self.commit_ballot_statement_counter[received_ballot.value]['voted'].add(sender)

                else:
                    self.commit_ballot_statement_counter[received_ballot.value]['voted'].add(sender)
                return

            # Case 3: New ballot received has the same value but a lower counter
            if received_ballot.counter < self.commit_ballot_state['voted'][received_ballot.value.hash].counter:
                log.node.info("Node %s that has been received has the same commit ballot value but a lower counter than a previously voted commit ballot.", self.name)
                if received_ballot.value not in self.commit_ballot_statement_counter:
                    self.commit_ballot_statement_counter[received_ballot.value] = {'voted': set(),'accepted': set(),'confirmed': set()}
                    self.commit_ballot_statement_counter[received_ballot.value]['voted'].add(sender)
                else:
                    self.commit_ballot_statement_counter[received_ballot.value]['voted'].add(sender)
                return

        # Case 2: New ballot received has different value and a higher counter
        elif received_ballot.value.hash not in self.commit_ballot_state['voted']:
            self.commit_ballot_state['voted'][received_ballot.value.hash] = received_ballot
            log.node.info("Node %s has received and added a commit ballot to its state.", self.name)
            if received_ballot.value not in self.commit_ballot_statement_counter:
                self.commit_ballot_statement_counter[received_ballot.value] = {'voted': set(), 'accepted': set(),'confirmed': set()}
                self.commit_ballot_statement_counter[received_ballot.value]['voted'].add(sender)
            else:
                self.commit_ballot_statement_counter[received_ballot.value]['voted'].add(sender)
            return


    def check_Commit_Quorum_threshold(self, ballot):
        # Check for Quorum threshold:
        # 1. the node itself has signed the message
        # 2. Number of nodes in the current QuorumSet who have signed + the number of innerSets that meet threshold is at least k
        # 3. These conditions apply recursively to the inner sets to fulfill condition 2.
        if ballot.value.hash in (self.commit_ballot_state["voted"]) or ballot.value.hash in (self.commit_ballot_state["accepted"]): # Condition 1. - node itself has signed message
            signed_count = 1 # Node itself has voted for it so already has a count of 1
            inner_sets_meeting_threshold_count = 0
            nodes, inner_sets = self.quorum_set.get_quorum()
            threshold = self.quorum_set.minimum_quorum

            for node in nodes:
                # check if the node name from the quorum is in the value's voted or accepted dict - meaning it has voted for the message
                if node in self.commit_ballot_statement_counter[ballot.value]['voted'] or node in self.commit_ballot_statement_counter[ballot.value]['accepted']:
                    signed_count += 1

            for element in inner_sets: # Keep to just 1 layer of depth for now - so only 1 inner set per quorum, [ [], [] ], not [ [], [[]] ]
                if isinstance(element, list):
                        # 2. Check if the innerSets meet threshold
                        threshold_met = self.quorum_set.check_commit_threshold(ballot=ballot, quorum=element, threshold=threshold, commit_statement_counter=self.commit_ballot_statement_counter.copy())
                        if threshold_met:
                            inner_sets_meeting_threshold_count += 1

            if signed_count + inner_sets_meeting_threshold_count >= threshold: # 3. conditions apply recursively to the inner sets to fulfill condition 2
                return True
            else:
                return False
        else:
            return False

    def update_commit_balloting_state(self, ballot, field):
        if field == "voted":
            if len(self.commit_ballot_state["voted"]) > 0 :
                if ballot.value.hash in self.commit_ballot_state['accepted']:
                    log.node.info('Commit ballot %s is already accepted in Node %s', ballot.value, self.name)
                    return

                if ballot.value.hash in self.commit_ballot_state['voted']:
                    self.commit_ballot_state["accepted"][ballot.value.hash] = (self.commit_ballot_state["voted"][ballot.value.hash])
                    self.commit_ballot_state["voted"].pop(ballot.value.hash)
                    log.node.info('Commit ballot %s has been moved to accepted in Node %s', ballot, self.name)
            else:
                log.node.info('No commit ballots in voted state, cannot move Ballot %s to accepted in Node %s', ballot, self.name)

        elif field == "accepted":
            if len(self.commit_ballot_state["accepted"]) > 0:
                if ballot.value.hash in self.commit_ballot_state['confirmed']:
                    log.node.info('Commit ballot %s is already confirmed in Node %s', ballot, self.name)
                    return

                if ballot.value.hash in self.commit_ballot_state['accepted']:
                    self.commit_ballot_state["confirmed"][ballot.value.hash] = (self.commit_ballot_state["accepted"][ballot.value.hash])
                    self.commit_ballot_state["accepted"].pop(ballot.value.hash)

                log.node.info('Commit ballot %s has been moved to confirmed in Node %s', ballot.value.hash, self.name)
            else:
                log.node.info('No commit ballots in accepted state, cannot move Ballots %s to confirmed in Node %s', ballot, self.name)\


    def retrieve_ballot_commit_message(self, requesting_node):
        # Check if there are any broadcast flags
        if len(self.commit_ballot_broadcast_flags) > 0:
            if requesting_node.name not in self.received_commit_ballot_broadcast_msgs:
                retrieved_message = np.random.choice(list(self.commit_ballot_broadcast_flags))
                self.received_commit_ballot_broadcast_msgs[requesting_node.name] = [retrieved_message]
                return retrieved_message

            already_sent = self.received_commit_ballot_broadcast_msgs[requesting_node.name]
            if len(already_sent) < len(self.commit_ballot_broadcast_flags):
                # Choose a random message not yet sent
                remaining_messages = list(set(self.commit_ballot_broadcast_flags) - set(already_sent))
                retrieved_message = np.random.choice(remaining_messages)
                self.received_commit_ballot_broadcast_msgs[requesting_node.name].append(retrieved_message)
                return retrieved_message

        return None

    def receive_commit_message(self):
        # self.ballot_statement_counter = {}
        # Looks like: {SCPBallot1.value: {'voted': set(Node1), ‘accepted’: set(Node2, Node3), ‘confirmed’: set(), ‘aborted’: set(), SCPBallot2.value: {'voted': set(), ‘accepted’: set(), ‘confirmed’: set(), ‘aborted’: set(node1, node2, node3)}

        sending_node = self.quorum_set.retrieve_random_peer(self)
        if sending_node is not None:
            if sending_node != self and not None:
                message = self.retrieve_ballot_commit_message(sending_node)

                if message is not None:
                    self.process_commit_ballot_message(message, sending_node)
                    log.node.info('Node %s retrieving messages from his peer Node %s!', self.name,sending_node.name)
                    ballot = message.ballot # message[0] is voted field
                    if type(ballot) is SCPBallot and ballot.value.hash in self.commit_ballot_state['accepted'] and self.check_Commit_Quorum_threshold(ballot):
                        log.node.info('Quorum threshold met for accepted commit ballot %s at Node %s', ballot, self.name)
                        self.update_commit_balloting_state(ballot, "accepted")
                    elif type(ballot) is SCPBallot and ballot.value.hash in self.commit_ballot_state['voted'] and self.check_Commit_Quorum_threshold(ballot):
                        log.node.info('Quorum threshold met for voted commit ballot %s at Node %s', ballot, self.name)
                        self.update_commit_balloting_state(ballot, "voted")

                else:
                    log.node.info('Node %s has no SCPCommit messages to retrieve from neighbor Node %s!', self.name, sending_node.name)
        else:
            log.node.info('Node %s could not retrieve peer!', self.name)

    def retrieve_confirmed_commit_ballot(self):
        if len(self.commit_ballot_state['confirmed']) > 0:
            # random_ballot_hash = np.random.choice(self.balloting_state['confirmed'])
            random_ballot_hash = np.random.choice(list(self.commit_ballot_state['confirmed'].keys()))
            confirmed_commit_ballot = self.commit_ballot_state['confirmed'][random_ballot_hash]  # Take a random Value from the confirmed state
            log.node.info('Node %s retrieved confirmed commit ballot %s for SCPExternalize', self.name, confirmed_commit_ballot)
            return confirmed_commit_ballot
        else:
            log.node.info('Node %s has no confirmed commit ballots to use for SCPExternalize!', self.name)
            return None

    def check_if_finalised(self, ballot):
        for externalize_msg in self.externalized_slot_counter:
            if externalize_msg.ballot == ballot:
                return True
        return False

    def prepare_Externalize_msg(self):
        """
        Prepare SCPExternalize message for Externalize phase
        """
        if len(self.commit_ballot_state['confirmed']) == 0: # Check if there are any values to prepare
            log.node.info('Node %s has no committed ballots to externalize.', self.name)
            return

        finalised_ballot = self.retrieve_confirmed_commit_ballot() # Retrieve a Value from the SCPPrepare 'confirmed' state
        if finalised_ballot is not None:
            externalize_msg = SCPExternalize(ballot=finalised_ballot, hCounter=finalised_ballot.counter, timestamp=Globals.simulation_time)

            # Store the externalized value in the ledger
            self.ledger.add_slot(self.slot, externalize_msg)
            # self.externalize_broadcast_flags.add(externalize_msg)
            self.externalize_broadcast_flags.add((self.slot, externalize_msg))
            self.externalized_slot_counter.add(externalize_msg)
            self.slot += 1  # initalise next slot
            log.node.info('Node %s appended SCPExternalize message for slot %d to its storage and state, message = %s', self.name, self.slot, externalize_msg)

            # Reset Nomination/Balloting data structures for next slot
            self.remove_finalized_transactions(externalize_msg.ballot.value)

            self.priority_list = set()
            self.nomination_round = 1
            self.last_nomination_start_time = Globals.simulation_time
            self.committed_ballots = {}
            self.balloting_state = {'voted': {}, 'accepted': {}, 'confirmed': {}, 'aborted': {}}
            self.commit_ballot_state = {'voted': {}, 'accepted': {}, 'confirmed': {}, 'aborted': {}}
            self.commit_ballot_broadcast_flags = set()

            # save to log file
            self.log_to_file(f"NODE - INFO - Node {self.name} appended SCPExternalize message to its storage and state, message = {externalize_msg}")
        log.node.info('Node %s could not retrieve a confirmed SCPCommit message from its peer!')

    def retrieve_externalize_msg(self, requesting_node):
        # Check if there are any broadcast flags
        if len(requesting_node.externalize_broadcast_flags) > 0:
            retrieved_slot, retrieved_message = random.choice(list(requesting_node.externalize_broadcast_flags))

            if requesting_node.name not in self.peer_externalised_statements:
                self.peer_externalised_statements[requesting_node.name] = set()
                self.peer_externalised_statements[requesting_node.name].add((retrieved_slot, retrieved_message))
            else:
                self.peer_externalised_statements[requesting_node.name].add((retrieved_slot, retrieved_message))
            return retrieved_slot, retrieved_message
        return None

    def receive_Externalize_msg(self):
        # Retrieve a random externalize message from a random peer.
        sending_node = self.quorum_set.retrieve_random_peer(self)
        if sending_node is not None and sending_node != self:
            result = self.retrieve_externalize_msg(sending_node)  # expected to return (slot_number, message)
            if result is not None:
                slot_number, message = result
                self.process_externalize_msg(slot_number, message, sending_node)
            else:
                log.node.info('Node %s has no SCPExternalize messages to retrieve from peer node %s!',
                              self.name, sending_node.name)
        else:
            log.node.info('Node %s could not retrieve a valid peer for externalize messages!', self.name)

    def process_externalize_msg(self, slot_number, message, sending_node):
        # Check if the slot has already been finalized in the ledger.
        if slot_number in self.ledger.slots:
            log.node.info('Node %s already externalized slot %d. Ignoring message from %s.',
                          self.name, slot_number, sending_node.name)
            return

        # Adopt the externalized value.
        log.node.info('Node %s adopting externalized value for slot %d: %s', self.name, slot_number, message.ballot.value)
        self.ledger.add_slot(slot_number, message)

        # Update peer externalized statements.
        self.peer_externalised_statements.setdefault(sending_node.name, set()).add((slot_number, message))
        # Optionally, add the (slot, message) tuple to this node's own broadcast flags (or remove it, as desired).
        self.externalize_broadcast_flags.add((slot_number, message))
        self.externalized_slot_counter.add(message)

        # Reset nomination and ballot states for this slot.
        self.remove_finalized_transactions(message.ballot.value)

        self.slot += 1
        self.nomination_round = 1
        self.committed_ballots = {}

        self.ballot_statement_counter = {}

        self.ballot_prepare_broadcast_flags = set()
        self.received_prepare_broadcast_msgs = {}
        self.prepared_ballots = {}

        self.balloting_state = {'voted': {}, 'accepted': {}, 'confirmed': {}, 'aborted': {}}
        self.ballot_statement_counter = {}
        self.ballot_prepare_broadcast_flags = set()
        self.received_prepare_broadcast_msgs = {}
        self.prepared_ballots = {}

        self.commit_ballot_state = {'voted': {}, 'accepted': {}, 'confirmed': {}}
        self.commit_ballot_statement_counter = {}
        self.commit_ballot_broadcast_flags = set()
        self.received_commit_ballot_broadcast_msgs = {}
        self.committed_ballots = {}

        log.node.info('Node %s has finalized slot %d with value %s', self.name, slot_number, message.ballot.value)
