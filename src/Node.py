"""
=========================
Node
=========================

Author: Matija Piskorec, Jaime de Vivero Woods

Last update: December 2024

Node class.

Documentation:

[2] Nicolas Barry and Giuliano Losa and David Mazieres and Jed McCaleb and Stanislas Polu, The Stellar Consensus Protocol (SCP) - technical implementation draft, https://datatracker.ietf.org/doc/draft-mazieres-dinrg-scp/05/
"""
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

        self.nomination_round = 1

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
        self.externalize_broadcast_flags = set()
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

    def retrieve_transaction_from_mempool(self):
        if not os.path.exists(self.log_path):
            with open(self.log_path, 'w') as log_file:
                log_file.write("")

        transaction = self.mempool.get_transaction()
        if transaction is not None:
            # TODO: Check the validity of the transaction in the retrieve_transactions_from_mempool() in Node!
            log.node.info('Node %s retrieved %s from mempool.',self.name,transaction)
            # add to logger file
            self.log_to_file(f"NODE - INFO - Node {self.name} retrieved {transaction} from mempool.")
            self.ledger.add(transaction)
        else:
            log.node.info('Node %s cannot retrieve transaction from mempool because it is empty!',self.name)
        return

    # Add nodes to quorum
    # TODO: Consider removing add_to_quorum() because we are only using set_quorum()!
    def add_to_quorum(self, nodes):
        self.quorum_set.add(nodes)
        return

    # Set quorum to the nodes
    def set_quorum(self, nodes, inner_sets):
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
        self.prepare_nomination_msg() # Prepares Values for Nomination and broadcasts message
        #priority_node = self.get_highest_priority_neighbor()

        # TODO: Neighbour should check global time & priority neighbour
        # TODO: nominate function should update nominations from peers until the quorum threshold is met
        # TODO: the respective function should be implemented and called here
        return

    def retrieve_broadcast_message(self, requesting_node):
        # Select a random message and check if its already been sent to the requesting_node
        # To check -> check if the value hash of the
        if len(self.broadcast_flags) > 0:
            if requesting_node.name not in self.received_broadcast_msgs:
                retrieved_message = np.random.choice(self.broadcast_flags)
                self.received_broadcast_msgs[requesting_node.name] = [retrieved_message]
                return retrieved_message

            elif len(self.received_broadcast_msgs[requesting_node.name]) != len(self.broadcast_flags):
                statement = True
                while statement:
                    retrieved_message = np.random.choice(self.broadcast_flags)
                    if retrieved_message not in self.received_broadcast_msgs[requesting_node.name]:
                        self.received_broadcast_msgs[requesting_node.name].append(retrieved_message)
                        return retrieved_message
        return None


    def receive_message(self):
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

        # Choosing a neighbor with the highest priority from which we fetch messages
        other_node = self.get_highest_priority_neighbor()

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
        """
        Prepare Message for Nomination
        """
        voted_vals = []
        accepted_vals = []

        self.retrieve_transaction_from_mempool() # Retrieve transactions from mempool and adds it to the Node's Ledger
        if len(self.ledger.transactions) > 0:
            voted_vals.append(Value(transactions=self.ledger.transactions.copy()))
            self.nomination_state['voted'].extend(voted_vals)

        if len(self.nomination_state['accepted']) > 0:
            accepted_vals.extend(self.nomination_state['accepted']) # Add all accepted values

        if len(voted_vals) == 0 and len(accepted_vals) == 0:
            log.node.info('Node %s has no transactions or accepted values to nominate!', self.name)
            return

        message = SCPNominate(voted=voted_vals,accepted=accepted_vals,broadcasted=True) # No accepted as node is initalised

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
    def Gi(self,values):
        # If there is only one value as input, convert it to list so that we can iterate over it
        if type(values) is not list:
            values = [values]

        # Concatenate XDR serialized values
        packer = xdrlib3.Packer()
        # Slot value "i" is implicitly passed as the first value to Gi!
        packer.pack_int(Globals.slot)
        for value in values:
            # Assumption is that all values can be cast to int (this includes node.name which is a string)
            if isinstance(value, str):
                packer.pack_bytes(value.encode('utf-8'))
            else:
                packer.pack_int(int(value))
        packed_data = packer.get_buffer()

        # Hash it and interpret the bytes as a big-endian integer number
        return int.from_bytes(hashlib.sha256(packed_data).digest())

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

    def get_neighbors(self):
        unique_nodes = set()  # Use set to avoid duplication - used to check for duplicates in loops

        for node in self.quorum_set.get_nodes():
            if self.Gi([1, self.nomination_round, node.name]) < (2 ** 256 * self.weight(node)):
                unique_nodes.add(node)  # Add to set

        for inner_set in self.quorum_set.get_inner_sets():
            if type(inner_set) is list:
                for node in inner_set:
                    if self.Gi([1, self.nomination_round, node.name]) < (2 ** 256 * self.weight(node)) and node not in unique_nodes:
                        unique_nodes.add(node)
            else:
                if self.Gi([1, self.nomination_round, inner_set.name]) < (
                        2 ** 256 * self.weight(inner_set)) and inner_set not in unique_nodes:
                    unique_nodes.add(inner_set)

        return unique_nodes

    # - Define "priority(n, v)" as "Gi(2 || n || v)", where "2" and "n"
    #   are both 32-bit XDR "int" values.
    def priority(self,v):
        return self.Gi([2,self.nomination_round,v.name])

    def get_highest_priority_neighbor(self):
        # TODO: Check globals.simulation_time
        neighbors = self.get_neighbors()
        if not neighbors:  # Avoid empty sequence error
            log.node.warning('Node %s has no neighbors!', self.name)
            return self  # Return self or handle the case differently
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
            externalize_msg = SCPExternalize(ballot=finalised_ballot, hCounter=finalised_ballot.counter)
            self.externalize_broadcast_flags.add(externalize_msg)
            self.externalized_slot_counter.add(externalize_msg)
            log.node.info('Node %s appended SCPExternalize message to its storage and state, message = %s', self.name, externalize_msg)
            # save to log file
            self.log_to_file(f"NODE - INFO - Node {self.name} appended SCPExternalize message to its storage and state, message = {externalize_msg}")
        log.node.info('Node %s could not retrieve a confirmed SCPCommit message from its peer!')

    def retrieve_externalize_msg(self, requesting_node):
        # Check if there are any broadcast flags
        if len(requesting_node.externalize_broadcast_flags) > 0:
            retrieved_message = np.random.choice(list(requesting_node.externalize_broadcast_flags))
            if requesting_node not in self.peer_externalised_statements:
                self.peer_externalised_statements[requesting_node.name] = set()
                self.peer_externalised_statements[requesting_node.name].add(retrieved_message)
            else:
                self.peer_externalised_statements[requesting_node.name].add(retrieved_message)
            return retrieved_message
        return None

    def receive_Externalize_msg(self):
        sending_node = self.quorum_set.retrieve_random_peer(self)
        if sending_node is not None and sending_node != self:
                message = self.retrieve_externalize_msg(sending_node)
                if message is not None:
                    log.node.info('Node %s has retrieved SCPExternalise message %s from peer node %s!', self.name, message, sending_node.name)

                    log.node.info('Node %s could not retrieved SCPExternalise message from peer node!', self.name)
                    self.peer_externalised_statements[sending_node].add(message)
