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
        self.finalised_transactions = set()
        self._seen_finalised_ballots = set()
        self.MAX_SLOT_TXS = 50

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
        self.log_nomination_data_path = 'nomination_phase_log.txt'

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

        # Filter nomination state (contains Value objects)
        filter_values(self.nomination_state)

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
                return transaction  # Return the valid transaction.
            else:
                log.node.info('Node %s ignored transaction %s as it was already externalized.', self.name,
                              transaction_id)
                # Do not add the transaction to the ledger in this branch.
                self.mempool.transactions.remove(transaction)
                self.log_to_file(
                    f"NODE - INFO - Node {self.name} ignored {transaction} as it was already externalized.")
                return None  # Explicitly return None as the transaction is externalized.
        else:
            log.node.info('Node %s cannot retrieve transaction from mempool because it is empty!', self.name)
            return None  # Ensure something is returned.

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

    def collect_finalised_transactions(self):
        """
        Scan through all externalize messages this node has ever sent,
        and update Node.finalised_transactions with each unique ballot’s tx hashes.
        """
        for ext_msg in self.externalized_slot_counter:
            ballots = ext_msg.ballot
            if not isinstance(ballots, (list, tuple, set)):
                ballots = [ballots]

            for b in ballots:
                key = (b.counter, b.value) # identify a ballot uniquely by its counter and value
                if key not in self._seen_finalised_ballots:
                    self._seen_finalised_ballots.add(key)
                    # assume b.value.transactions always exists
                    self.finalised_transactions.update(
                        tx.hash for tx in b.value.transactions
                    )
        log.node.info("Added %s to finalised_transaction set", self.finalised_transactions)
        return self.finalised_transactions

    def nominate(self):
        """
        Broadcast SCPNominate message to the storage.
        """
        # TODO: A node can nominate a value itself if it has the highest priority in the current round.
        #  If it does not have the highest priority, it waits for higher-priority nodes to propose values before deciding what to nominate
        self.check_update_nomination_round()
        self.get_priority_list()
        if self.name in self.priority_list:
            self.prepare_nomination_msg() # Prepares Values for Nomination and broadcasts message
            """if msg is None:
                return
            voted_val = msg.voted[0]
            accepted_val = msg.accepted[0] if msg.accepted else None

            if type(voted_val) is Value and self.check_Quorum_threshold(voted_val):
                log.node.info('Quorum threshold met for voted value %s at Node %s after preparation', voted_val, self.name)
                self.update_nomination_state(voted_val, "voted")


            if type(accepted_val) is Value and self.check_Quorum_threshold(accepted_val):
                log.node.info('Quorum threshold met for accepted value %s at Node %s after preparation', accepted_val, self.name)
                self.update_nomination_state(accepted_val, "accepted")"""
        else:
            log.node.info("Node %s did not Nominate a Value since it is not in it's priority list", self.name)
        #self.prepare_nomination_msg()
        # self.prepare_nomination_msg()  # Prepares Values for Nomination and broadcasts message
        #priority_node = self.get_highest_priority_neighbor()

        # TODO: Neighbour should check global time & priority neighbour
        # TODO: nominate function should update nominations from peers until the quorum threshold is met
        # TODO: the respective function should be implemented and called here
        return

    """
    # OLD VERSION
    def retrieve_broadcast_message(self, requesting_node):
        # If no messages exist at all, return None.
        if not self.broadcast_flags:
            return None

        # If the requesting node has already received all messages in broadcast_flags, return None.
        if (requesting_node.name in self.received_broadcast_msgs and
                len(self.received_broadcast_msgs[requesting_node.name]) == len(self.broadcast_flags)):
            return None

        # Ensure the requesting node has an entry in received_broadcast_msgs.
        if requesting_node.name not in self.received_broadcast_msgs:
            self.received_broadcast_msgs[requesting_node.name] = []

        # Build list of messages not yet received by the requesting node.
        unseen_messages = [
            msg for msg in self.broadcast_flags
            if msg not in self.received_broadcast_msgs[requesting_node.name]
        ]
        if not unseen_messages:
            # In case all messages have been seen.
            return None

        # Select a random message from unseen messages.
        retrieved_message = np.random.choice(unseen_messages)

        # If the message is externalized, remove it from broadcast_flags.
        if self.is_message_externalized(retrieved_message):
            self.broadcast_flags.remove(retrieved_message)

        # Record that the requesting node has retrieved this message.
        self.received_broadcast_msgs[requesting_node.name].append(retrieved_message)

        return retrieved_message"""


    #LATEST VERSION
    def retrieve_broadcast_message(self, providing_node):
        """
        Pull one unseen envelope from providing_node.broadcast_flags.
        Return None once I've seen them all, or they have none left.
        """
        # 1) nothing to pull if they have no flags
        if not providing_node.broadcast_flags:
            return None

        # 2) track which ones *I* have already pulled from them
        seen = self.received_broadcast_msgs.setdefault(providing_node.name, [])

        # 3) collect the ones they still have that I haven't seen
        unseen = [m for m in providing_node.broadcast_flags if m not in seen]
        if not unseen:
            return None

        # 4) grab one at random
        msg = np.random.choice(unseen)

        # 5) record that *I* have now seen it
        seen.append(msg)

        # 6) if that nomination has already been externalized, drop it at the source
        if self.is_message_externalized(msg):
            providing_node.broadcast_flags.remove(msg)

        return msg

    """
    # NEW (NOT NEWEST) IMPLEMENTATION THAT DID NOT WORK
    def retrieve_broadcast_message(self, priority_node):

        # If no messages exist at all, return None.
        if not self.broadcast_flags:
            return None

        # Ensure the requesting node has an entry in received_broadcast_msgs.
        if priority_node.name not in self.received_broadcast_msgs:
            self.received_broadcast_msgs[priority_node.name] = []

        # Build list of messages not yet received by the requesting node.
        unseen_messages = [
            msg for msg in priority_node.broadcast_flags
            if msg not in self.received_broadcast_msgs[priority_node.name]
        ]
        if not unseen_messages:
            # In case all messages have been seen.
            return None

        # Select a random message from unseen messages.
        retrieved_message = np.random.choice(unseen_messages)

        # Record that the requesting node has retrieved this message.
        self.received_broadcast_msgs[priority_node.name].append(retrieved_message)

        return retrieved_message
        """



    def get_finalized_transaction_ids(self):
        """
        Collects all finalized transaction IDs (hashes) from the ledger.
        """
        finalized_tx_ids = set()
        for slot, ext_msg in self.ledger.slots.items():
            # Handle case where ext_msg is stored as a dict.
            if isinstance(ext_msg, dict) and "ballot" in ext_msg:
                ballot = ext_msg["ballot"]
            else:
                ballot = getattr(ext_msg, "ballot", None)
            if ballot is None:
                continue
            # Get the value from the ballot.
            if hasattr(ballot, "value"):
                value = ballot.value
            elif isinstance(ballot, dict) and "value" in ballot:
                value = ballot["value"]
            else:
                value = None
            if value is None:
                continue
            # Assuming value has an attribute 'transactions'
            if hasattr(value, "transactions"):
                for tx in value.transactions:
                    finalized_tx_ids.add(tx.hash)
        return finalized_tx_ids

    def receive_message(self):
        #if any(self.balloting_state[state] for state in ['voted', 'accepted', 'confirmed', 'aborted']):
        #    log.node.info("Node %s is skipping message processing as it already has ballots in balloting_state.",
        #                  self.name)
            #return

        # This checks if the node has no quorum set, if so then it simply gets ignored
        if not self.quorum_set or (not self.quorum_set.get_nodes() and not self.quorum_set.get_inner_sets()):
            log.node.warning(f"Node {self.name} has no valid quorum set! Skipping priority calculation.")
            return

        self.check_update_nomination_round()
        priority_node = self.get_highest_priority_neighbor()
        if priority_node is None:
            log.node.info("Node %s has no valid priority neighbor!", self.name)
            return
        if priority_node != self:
            print("TRYING TO RETRIEVE BROADCAST MESSAGE")

            ##################################

            # THIS IS A LATEST CHANGE !!!!

            ###################################
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
                    # NEW AND VERIFY!!!!!!!!!!!!!!!!!!!!!!
                    """if voted_val not in self.nomination_state["voted"] and voted_val not in self.nomination_state[
                        "accepted"]:
                        log.node.info('Blocking threshold met for new value %s at Node %s – voting immediately!',
                                      voted_val, self.name)
                        self.nomination_state["voted"].append(voted_val)
                        self.update_local_nomination_broadcast()"""

                accepted_val = message[1] # message[1] is accepted field
                if type(accepted_val) is Value and self.check_Quorum_threshold(accepted_val):

                    log.node.info('Quorum threshold met for accepted value %s at Node %s', accepted_val, self.name)

                    self.update_nomination_state(accepted_val, "accepted")

                if type(accepted_val) is Value and self.check_Blocking_threshold(accepted_val):
                    # NEW AND VERIFY!!!!!!!!!!!!!!!!!!!!!!
                    log.node.info('Blocking threshold met for value %s at Node %s', accepted_val, self.name)
                    """if accepted_val not in self.nomination_state["voted"] and accepted_val not in self.nomination_state[
                        "accepted"]:
                        log.node.info(
                            'Blocking threshold met for new accepted value %s at Node %s – voting immediately!',
                            accepted_val, self.name)
                        self.nomination_state["voted"].append(accepted_val)
                        self.update_local_nomination_broadcast()"""

            else:
                log.node.info('Node %s has no messages to retrieve from his highest priority neighbor Node %s!', self.name, priority_node.name)

    def update_local_nomination_broadcast(self):
        """
        Constructs a new SCPNominate message using the current nomination state
        (voted and accepted) and replaces the node's broadcast flags with only that message.
        """
        voted_vals = self.nomination_state.get('voted', [])
        accepted_vals = self.nomination_state.get('accepted', [])
        confirmed_vals = self.nomination_state.get('confirmed', [])
        if not voted_vals and not accepted_vals:
            log.node.info("Node %s has empty nomination state; not updating broadcast flag.", self.name)
            return
        # Create a new SCPNominate message with the latest nomination state.
        new_nom_msg = SCPNominate(voted=voted_vals, accepted=accepted_vals, confirmed=confirmed_vals)
        # Replace the broadcast flags with just this new message.
        self.broadcast_flags = [new_nom_msg]
        #elf.broadcast_flags.append(new_nom_msg)
        log.node.info("Node %s updated its local nomination broadcast flag: %s", self.name, new_nom_msg)

    """
    def process_received_message(self, message):

        # Retrieve finalized transaction hashes from the ledger.
        finalized_tx_ids = self.get_finalized_transaction_ids()

        # Process the "voted" nomination field.
        incoming_voted = message[0]
        if isinstance(incoming_voted, Value):
            # Filter out finalized transactions from the incoming voted value.
            filtered_voted_transactions = {tx for tx in incoming_voted.transactions if tx.hash not in finalized_tx_ids}
            filtered_incoming_voted = Value(transactions=filtered_voted_transactions)
            voted_list = self.nomination_state.get('voted', [])
            if voted_list:
                last = self.nomination_state['voted'][-1]
                merged = Value.combine([last, filtered_incoming_voted])
                self.nomination_state['voted'][-1] = merged
                log.node.info('Node %s updated its voted nomination state with combined value: %s', self.name,
                             merged)
            else:
                combined_voted = filtered_incoming_voted
                self.nomination_state['voted'].append(combined_voted)
                log.node.info('Node %s updated its voted nomination state with appended value: %s', self.name,
                          combined_voted)

        # Process the "accepted" nomination field.
        incoming_accepted = message[1]
        if isinstance(incoming_accepted, Value):
            if incoming_accepted not in self.nomination_state['accepted']:
                self.nomination_state['accepted'].append(incoming_accepted)
                log.node.info('Node %s updated its accepted nomination state with value: %s', self.name,
                          incoming_accepted)

        self.update_local_nomination_broadcast() """


    def process_received_message(self, message):
        finalized_tx_ids = self.get_finalized_transaction_ids()

        # Process the "voted" nomination field.
        incoming_voted = message[0]
        if isinstance(incoming_voted, Value):
            # Filter out finalized transactions from the incoming voted value.
            filtered_voted_transactions = {tx for tx in incoming_voted.transactions if tx.hash not in finalized_tx_ids}
            filtered_incoming_voted = Value(transactions=filtered_voted_transactions)
            #current_voted = self.nomination_state.get('voted', [])
            # ADDED HERE
            pruned = []
            for old_val in self.nomination_state.get('voted', []):
                keep = {t for t in old_val.transactions
                        if t.hash not in self.finalised_transactions}
                if keep:
                    pruned.append(Value(transactions=keep))
            self.nomination_state['voted'] = pruned

            # merge and cap txs to here
            current_voted = self.nomination_state.get('voted', [])
            combined_voted = Value.combine(current_voted + [filtered_incoming_voted])
            """
            # 4) enforce MAX_SLOT_TXS
            txs = list(combined_voted.transactions)
            if len(txs) > self.MAX_SLOT_TXS:
                # e.g. take first N (or random.sample for fairness)
                limited = set(txs[:self.MAX_SLOT_TXS])
                combined_voted = Value(transactions=limited)
                log.node.info( 'Node %s: truncating merged voted txs → %d (slot limit).', self.name, self.MAX_SLOT_TXS)"""


            self.nomination_state['voted'] = [combined_voted]
            log.node.info('Node %s updated its voted nomination state with combined value: %s', self.name,
                          combined_voted)

            # Process the "accepted" nomination field.
            incoming_accepted = message[1]
            if isinstance(incoming_accepted, Value):
    
                self.nomination_state['accepted'].append(incoming_accepted)
                pruned = []
                for old_val in self.nomination_state.get('accepted', []):
                    keep = {t for t in old_val.transactions
                            if t.hash not in self.finalised_transactions}
                    if keep:
                        pruned.append(Value(transactions=keep))
                self.nomination_state['accepted'] = pruned
                log.node.info('Node %s updated its accepted nomination state with combined value: %s', self.name,
                              pruned)
            """
            incoming_accepted = message[1]
            if isinstance(incoming_accepted, Value):
                # 1) prune out finalized txs from any old accepted Value
                pruned = []
                for old_val in self.nomination_state.get('accepted', []):
                    keep = {t for t in old_val.transactions
                            if t.hash not in self.finalised_transactions}
                    if keep:
                        pruned.append(Value(transactions=keep))

                # 2) merge old + incoming into a single Value
                combined_accepted = Value.combine(pruned + [incoming_accepted])

                # 3) drop if empty
                if not combined_accepted.transactions:
                    log.node.info(
                        'Node %s: no accepted txs remain after pruning; clearing accepted state.',
                        self.name
                    )
                    self.nomination_state['accepted'] = []
                else:
                    # 4) enforce MAX_SLOT_TXS cap
                    txs = list(combined_accepted.transactions)
                    if len(txs) > self.MAX_SLOT_TXS:
                        limited = set(txs[:self.MAX_SLOT_TXS])
                        combined_accepted = Value(transactions=limited)
                        log.node.info(
                            'Node %s: truncating merged accepted txs → %d (slot limit).',
                            self.name, self.MAX_SLOT_TXS
                        )

                    # 5) store back as a single accepted Value
                    self.nomination_state['accepted'] = [combined_accepted]
                    log.node.info(
                        'Node %s updated its accepted nomination state with combined value: %s',
                        self.name, combined_accepted
                    )"""

            self.update_local_nomination_broadcast()

    """
    def retrieve_message_from_peer(self):

        # Update nomination round and priority list if simulation time exceeds nomination round time and
        # choose a neighbor with the highest priority from which we fetch messages
        v = 'test'
        other_node = self.get_highest_priority_neighbor()
        print("OTHER NODE IS ", other_node, " which has type ", type(other_node))
        print("checking against none")
        if other_node is None:
            log.node.info('Node %s has no one in quorum set!',self.name)
            return

        print("now checking against self")

        if other_node is not None:
            print("GOT HERE TO CHECK MESSAGES")
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
    """

    def is_value_already_present(self, new_value):
        """
        Checks if a Value (new_value) is already present in any nomination state
        (voted, accepted, confirmed). Comparison is done using the hash
        (or using __eq__ if that is defined on Value).
        """
        for state in ['voted', 'accepted', 'confirmed']:
            for val in self.nomination_state.get(state, []):
                if new_value == val:  # relies on Value.__eq__ (and __hash__)
                    return True
        return False

    def clean_nomination_state_duplicates(self):
        """
        Cleans each list in nomination_state by removing duplicate Value objects.
        This function modifies nomination_state in-place.
        """
        for state in self.nomination_state:
            seen = set()
            unique_values = []
            # Iterate in order to preserve the order (if necessary).
            for value in self.nomination_state[state]:
                if value not in seen:
                    unique_values.append(value)
                    seen.add(value)
            self.nomination_state[state] = unique_values
        log.node.info("Node %s cleaned nomination_state; current state: %s", self.name, self.nomination_state)


    """
        def prepare_nomination_msg(self):

        # Retrieve a single transaction from the mempool.
        tx = self.retrieve_transaction_from_mempool()
        if tx is None:
            log.node.info('Node %s found no transaction to nominate.', self.name)
            return

        # Gather hashes of all finalized (externalized) transactions.
        self.collect_finalised_transactions()
        # If the transaction has already been finalized, skip nomination.
        if tx.hash in self.finalised_transactions:
            log.node.info('Node %s retrieved transaction %s but it is already finalized. Skipping nomination.',
                          self.name, tx)
            return

        # Now check if this transaction is already in the nomination state (“voted” field)
        for existing_value in self.nomination_state.get('voted', []):
            if any(existing_tx.hash == tx.hash for existing_tx in existing_value.transactions):
                log.node.info('Node %s already contains transaction %s in its nomination state. Skipping nomination.',
                              self.name, tx)
                return
        

        # Wrap the transaction in a new Value.
        new_value = Value(transactions={tx})

        if self.is_value_already_present(new_value):
            log.node.info('Node %s already has a nomination with transaction %s. Skipping nomination.', self.name, tx)
            return

        # Instead of always appending a new Value, check if there's already a nominated value.
        if self.nomination_state['voted']:
            # If there is an existing nominated value, combine it with the new value.
            # This merges the transactions and removes duplicates.

            existing = self.nomination_state.get('voted', [])
            combined_value = Value.combine(existing + [new_value])
            #last = self.nomination_state['voted'][-1]
           # combined_value = Value.combine([last, new_value])
            if self.is_value_already_present(combined_value):
                log.node.info('Node %s already has a nomination with transactions %s. Skipping nomination.', self.name,
                              combined_value.transactions)
                return
            self.nomination_state['voted'] = [combined_value]
            #self.nomination_state['voted'].append(combined_value)
            log.node.info('Node %s merged the new transaction into its voted nomination state: %s', self.name,
                          combined_value)
        else:
            # If no nomination exists, simply add the new value.
            self.nomination_state['voted'] = [new_value]
            log.node.info('Node %s set its voted nomination state to new value: %s', self.name, new_value)

        self.clean_nomination_state_duplicates()
        # Prepare the nomination message.
        voted_vals = self.nomination_state['voted']
        # In many designs, accepted values may be carried over from previous rounds.
        accepted_vals = self.nomination_state['accepted']
        confirmed_vals = self.nomination_state['confirmed']

        # Avoid sending an empty nomination message.
        if not voted_vals and not accepted_vals:
            log.node.info('Node %s has no transactions or accepted values to nominate!', self.name)
            return

        # Create the nomination message.
        message = SCPNominate(voted=voted_vals, accepted=accepted_vals, confirmed=confirmed_vals)
        self.storage.add_messages(message)
        self.broadcast_flags = [message]
        #elf.broadcast_flags.append(message)
        log.node.info('Node %s appended SCPNominate message to its storage and state, message = %s', self.name, message)
        return message"""

    """
        def prepare_nomination_msg(self):

        # Retrieve a single transaction from the mempool.
        tx = self.retrieve_transaction_from_mempool()
        if tx is None:
            log.node.info('Node %s found no transaction to nominate.', self.name)
            return

        # Gather hashes of all finalized (externalized) transactions.
        self.collect_finalised_transactions()
        pruned = []
        for old_val in self.nomination_state.get('voted', []):
            keep = {t for t in old_val.transactions
                    if t.hash not in self.finalised_transactions}
            if keep:
                pruned.append(Value(transactions=keep))
        self.nomination_state['voted'] = pruned

        # 5) now check if *new* tx is already in one of those pruned Values
        for existing_value in pruned:
            if any(t.hash == tx.hash for t in existing_value.transactions):
                log.node.info('Node %s already has tx %s in nomination state. Skipping.',
                              self.name, tx)
                return

        # Now check if this transaction is already in the nomination state (“voted” field)
        for existing_value in self.nomination_state.get('voted', []):
            if any(existing_tx.hash == tx.hash for existing_tx in existing_value.transactions):
                log.node.info('Node %s already contains transaction %s in its nomination state. Skipping nomination.',
                              self.name, tx)
                return

        # Wrap the transaction in a new Value.
        new_value = Value(transactions={tx})

        if self.is_value_already_present(new_value):
            log.node.info('Node %s already has a nomination with transaction %s. Skipping nomination.', self.name, tx)
            return

        # Instead of always appending a new Value, check if there's already a nominated value.
        if self.nomination_state['voted']:
            # If there is an existing nominated value, combine it with the new value.
            # This merges the transactions and removes duplicates.

            existing = self.nomination_state.get('voted', [])
            combined_value = Value.combine(existing + [new_value])
            #last = self.nomination_state['voted'][-1]
           # combined_value = Value.combine([last, new_value])
            if self.is_value_already_present(combined_value):
                log.node.info('Node %s already has a nomination with transactions %s. Skipping nomination.', self.name,
                              combined_value.transactions)
                return
            self.nomination_state['voted'] = [combined_value]
            #self.nomination_state['voted'].append(combined_value)
            log.node.info('Node %s merged the new transaction into its voted nomination state: %s', self.name,
                          combined_value)
        else:
            # If no nomination exists, simply add the new value.
            self.nomination_state['voted'] = [new_value]
            log.node.info('Node %s set its voted nomination state to new value: %s', self.name, new_value)

        self.clean_nomination_state_duplicates()
        # Prepare the nomination message.
        voted_vals = self.nomination_state['voted']
        # In many designs, accepted values may be carried over from previous rounds.
        accepted_vals = self.nomination_state['accepted']
        confirmed_vals = self.nomination_state['confirmed']

        # Avoid sending an empty nomination message.
        if not voted_vals and not accepted_vals:
            log.node.info('Node %s has no transactions or accepted values to nominate!', self.name)
            return

        # Create the nomination message.
        message = SCPNominate(voted=voted_vals, accepted=accepted_vals, confirmed=confirmed_vals)
        self.storage.add_messages(message)
        self.broadcast_flags = [message]
        #elf.broadcast_flags.append(message)
        log.node.info('Node %s appended SCPNominate message to its storage and state, message = %s', self.name, message)
        return message
    """

    def clean_prepare_and_commit_state(self):
        """
        Removes entries from prepare and commit phases that contain finalized transactions.
        Ensures finalized transactions do not block nomination.
        """

        # Helper to check if a ballot's value is entirely finalized
        def is_finalized(value):
            return all(t.hash in self.finalised_transactions for t in value.transactions)

        # Clean prepare phase
        for phase in ['voted', 'accepted', 'confirmed', 'aborted']:
            self.balloting_state[phase] = {
                val_hash: ballot for val_hash, ballot in self.balloting_state[phase].items()
                if not is_finalized(ballot.value)
            }

        self.ballot_statement_counter = {
            val: counters for val, counters in self.ballot_statement_counter.items()
            if not is_finalized(val)
        }

        self.prepared_ballots = {
            val: prep for val, prep in self.prepared_ballots.items()
            if not is_finalized(val)
        }

        # Clean commit phase
        for phase in ['voted', 'accepted', 'confirmed']:
            self.commit_ballot_state[phase] = {
                val_hash: ballot for val_hash, ballot in self.commit_ballot_state[phase].items()
                if not is_finalized(ballot.value)
            }

        self.commit_ballot_statement_counter = {
            val: counters for val, counters in self.commit_ballot_statement_counter.items()
            if not is_finalized(val)
        }

        self.committed_ballots = {
            val: cmt for val, cmt in self.committed_ballots.items()
            if not is_finalized(val)
        }

    def prepare_nomination_msg(self):
        """
        Prepares an SCPNominate message by collecting all available transactions,
        excluding those already nominated, in ballot phases, or finalized.
        Combines new transactions into the nomination state.
        """

        # Step 1: Get all transactions from the mempool
        all_tx = self.mempool.get_all_transactions()

        # NEW TEST CHANGE FOR FULL
        all_tx = self.mempool.get_transaction()
        if not all_tx:
            log.node.info('Node %s found no transactions to nominate.', self.name)
            return

        # Step 2: Update finalized transactions and prune 'voted'
        self.collect_finalised_transactions()
        self.clean_prepare_and_commit_state()  # Optional: if you want to clean out states fully

        pruned = []
        for old_val in self.nomination_state.get('voted', []):
            keep = {t for t in old_val.transactions if t.hash not in self.finalised_transactions}
            if keep:
                pruned.append(Value(transactions=keep))
        self.nomination_state['voted'] = pruned

        # Step 3: Gather hashes to exclude
        excluded_hashes = set(self.finalised_transactions)

        # From nomination state
        for state in ['voted', 'accepted', 'confirmed']:
            for val in self.nomination_state.get(state, []):
                excluded_hashes.update(t.hash for t in val.transactions)

        # From prepare ballot state
        for phase in ['voted', 'accepted', 'confir22med', 'aborted']:
            for ballot in self.balloting_state.get(phase, {}).values():
                excluded_hashes.update(t.hash for t in ballot.value.transactions)

        # From commit ballot state
        for phase in ['voted', 'accepted', 'confirmed']:
            for ballot in self.commit_ballot_state.get(phase, {}).values():
                excluded_hashes.update(t.hash for t in ballot.value.transactions)

        # Step 4: Filter new transactions
        ##new_transactions = {t for t in all_tx if t.hash not in excluded_hashes}
        #if not new_transactions:
        #    log.node.info('Node %s found no new transactions to nominate after filtering.', self.name)
        #    new_transactions = set()

        """"
        # *** ENFORCE SLOT SIZE LIMIT HERE ***
        if len(new_transactions) > self.MAX_SLOT_TXS:
            # choose the top-fee ones
            sorted_txs = sorted(new_transactions, key=lambda t: t.hash, reverse=True)
            limited_set = set(sorted_txs[:self.MAX_SLOT_TXS])
            log.node.info(
                'Node %s: truncating %d new txs → %d (slot limit).',
                self.name, len(new_transactions), self.MAX_SLOT_TXS
            )
        else:
            limited_set = new_transactions"""


        # Step 5: Wrap filtered transactions in a new Value
        new_value = Value(transactions=excluded_hashes)
        if self.is_value_already_present(new_value):
            log.node.info('Node %s already has a nomination with transactions %s. Skipping nomination.',
                          self.name, new_value.transactions)
            return

        # Step 6: Merge with existing 'voted'
        if self.nomination_state['voted']:
            existing = self.nomination_state['voted']
            combined_value = Value.combine(existing + [new_value])
            """
            # --- ENFORCE SLOT SIZE LIMIT AFTER MERGE ---
            if len(combined_value.transactions) > self.MAX_SLOT_TXS:
                # pick a deterministic subset (e.g. first 100 by hash)
                txs_sorted = sorted(combined_value.transactions, key=lambda tx: tx.hash)
                capped = set(txs_sorted[:self.MAX_SLOT_TXS])
                combined_value = Value(transactions=capped)
                log.node.info(
                    'Node %s: truncating merged %d txs → %d (slot limit).',
                    self.name, len(txs_sorted), self.MAX_SLOT_TXS
                )
            # ---------------------------------------------"""

            if self.is_value_already_present(combined_value):
                log.node.info('Node %s already has a nomination with transactions %s. Skipping nomination.',
                              self.name, combined_value.transactions)
                return
            self.nomination_state['voted'] = [combined_value]
            log.node.info('Node %s merged new transactions into voted nomination state: %s',
                          self.name, combined_value)
        else:
            self.nomination_state['voted'] = [new_value]
            log.node.info('Node %s set its voted nomination state to new value: %s',
                          self.name, new_value)

        # Step 7: Final cleanup and message prep
        self.clean_nomination_state_duplicates()
        voted_vals = self.nomination_state['voted']
        accepted_vals = self.nomination_state['accepted']
        confirmed_vals = self.nomination_state['confirmed']

        if not voted_vals and not accepted_vals:
            log.node.info('Node %s has no values to nominate!', self.name)
            return

        message = SCPNominate(voted=voted_vals, accepted=accepted_vals, confirmed=confirmed_vals)
        self.storage.add_messages(message)
        self.broadcast_flags = [message]
        log.node.info('Node %s prepared SCPNominate message: %s', self.name, message)
        return message

    def get_messages(self):
        print("CHECKING GET MESSAGES")
        if len(self.storage.messages) == 0:
            messages = None
            log.node.info('Node %s: No messages to retrieve!',self.name)
        else:
            # TODO: Implement get_messages() in Storage which returns copy of the messages!
            messages = self.storage.messages.copy()
        return messages

    def update_statement_count(self, other_node, message):
        # message might be [Value, Value], or [ [Value,…], [Value,…] ]
        raw_voted, raw_accepted = message

        # Normalize to lists
        if isinstance(raw_voted, Value):
            voted_vals = [raw_voted]
        elif isinstance(raw_voted, list):
            voted_vals = raw_voted
        else:
            voted_vals = []

        if isinstance(raw_accepted, Value):
            accepted_vals = [raw_accepted]
        elif isinstance(raw_accepted, list):
            accepted_vals = raw_accepted
        else:
            accepted_vals = []

        # First handle all the accepted nominations
        for val in accepted_vals:
            h = val.hash
            # Ensure an entry in the counter
            if h not in self.statement_counter:
                self.statement_counter[h] = {"voted": {}, "accepted": {}}
            # If we haven't recorded other_node's accept yet, record it
            if other_node.name not in self.statement_counter[h]["accepted"]:
                self.statement_counter[h]["accepted"][other_node.name] = 1
                log.node.info(
                    "Node %s recorded ACCEPT from %s for value %s",
                    self.name, other_node.name, h
                )

        # Now handle all the voted nominations
        for val in voted_vals:
            h = val.hash
            # Ensure an entry in the counter
            if h not in self.statement_counter:
                self.statement_counter[h] = {"voted": {}, "accepted": {}}
            # If we haven't recorded other_node's vote yet, record it
            if other_node.name not in self.statement_counter[h]["voted"]:
                self.statement_counter[h]["voted"][other_node.name] = 1
                log.node.info(
                    "Node %s recorded VOTE from %s for value %s",
                    self.name, other_node.name, h
                )


    """
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
                            log.node.info('Node %s has added a voted statement counter for Node %s with nominated values!',self.name, other_node.name)

                else:
                    self.statement_counter[incoming_voted.hash] = {"voted": {}, "accepted": {}}
                    self.statement_counter[incoming_voted.hash]['voted'] = {other_node.name: 1}
                    log.node.info('Node %s has set its voted statement counter for %s with nominated values!', self.name, other_node.name)
    """


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

    def get_priority_list(self):
        print(f"Nodes in quorum set: {self.quorum_set.get_nodes()}")
        print(f"Inner sets in quorum set: {self.quorum_set.get_inner_sets()}")
        unique_nodes = set()  # Use set to avoid duplication - used to check for duplicates in loops
        if self.Gi([1, self.nomination_round, str(self.name)]) < (2 ** 256 * 1.0):
            print("SELF WAS ADDED")
            unique_nodes.add(self)

        # LATEST ADDITION - DONT ADD SELF
        for node in self.quorum_set.get_nodes():
            # print("Weight for node ", node.name, " : ", self.quorum_set.weight(node))
            # print("self.Gi([1, self.nomination_round, node.name]) returns ", self.Gi([1, self.nomination_round, node.name]), " for node ", node.name)
            # print(" this is less than ", (2 ** 256 * self.quorum_set.weight(node)), self.Gi([1, self.nomination_round, node.name]) < (2 ** 256 * self.quorum_set.weight(node)))
            if self.Gi([1, self.nomination_round, str(node.name)]) < (2 ** 256 * self.quorum_set.weight(node)):
               unique_nodes.add(node)  # Add to set

        for inner_set in self.quorum_set.get_inner_sets():
            if isinstance(inner_set, list):
                for node in inner_set:
                    if self.Gi([1, self.nomination_round, node.name]) < (
                            2 ** 256 * self.quorum_set.weight(node)):
                        unique_nodes.add(node)
            elif isinstance(inner_set, Node):  # Ensure inner_set is a Node, not a duplicate list
                if self.Gi([1, self.nomination_round, inner_set.name]) < (
                        2 ** 256 * self.quorum_set.weight(inner_set)):
                    unique_nodes.add(inner_set)

            # print("For node ", node.name, " the priority nodes are ", unique_nodes)
        self.priority_list.update(unique_nodes)
        print("THE SELF PRIORITY LIST IS ", self.priority_list)
        print("PRIORITY LIST FOR ", self.name, " IS ", self.priority_list)
        return unique_nodes

    # - Define "priority(n, v)" as "Gi(2 || n || v)", where "2" and "n"
    #   are both 32-bit XDR "int" values.
    def priority(self,v):
        return self.Gi([2,self.nomination_round,v.name])

    def get_highest_priority_neighbor(self):
        # Update nomination round and priority list as needed.
        self.check_update_nomination_round()
        neighbors = self.get_priority_list()

        if not neighbors:
            log.node.warning('Node %s has no nodes in the priority list!', self.name)
            print("Nodes in quorum set:", self.quorum_set.get_nodes(), self.quorum_set.get_inner_sets())
            return None

        # Optionally, filter out self if there are other candidates.
        available_neighbors = [node for node in neighbors if node != self]
        if not available_neighbors:
            available_neighbors = list(neighbors)

        # Choose the node with the lowest Gi value – assuming lower Gi means higher priority.
        highest_priority_neighbor = max(available_neighbors,
                                        key=lambda neighbor: self.priority(neighbor))

        log.node.info('Node %s has highest priority neighbor: %s', self.name, highest_priority_neighbor.name)
        return highest_priority_neighbor

    def is_duplicate_value(self, other_val, current_vals):
        for val in current_vals:
            if other_val == val:
                return True
        return False

    # TODO: Call this after receiving a message + Update state in this event once its met
    def check_Quorum_threshold(self, val):
        """
        Checks if the candidate value (val) meets the quorum threshold for nomination.
        """
        # Condition 1: The node must already have voted for or accepted this value.
        if val not in self.nomination_state["voted"] and val not in self.nomination_state["accepted"]:
            return False

        # Start with a count of 1 for self.
        signed_count = 1
        inner_sets_meeting_threshold_count = 0
        nodes, inner_sets = self.quorum_set.get_quorum()
        threshold = self.quorum_set.minimum_quorum

        # Safely get the vote/accept counts for this candidate Value.
        entry = self.statement_counter.get(val.hash, {'voted': set(), 'accepted': set()})

        for node in nodes:
            # Check if this node's name is recorded as voting or accepting the candidate.
            if node.name in entry.get('voted', set()) or node.name in entry.get('accepted', set()):
                signed_count += 1

        # For each inner set (at one level of nesting), check if it meets threshold.
        for element in inner_sets:
            if isinstance(element, list):
                threshold_met = self.quorum_set.check_threshold(
                    val=val,
                    quorum=element,
                    threshold=threshold,
                    node_statement_counter=self.statement_counter.copy()
                )
                if threshold_met:
                    inner_sets_meeting_threshold_count += 1

        # Return True if the total is at least the quorum threshold.
        return (signed_count + inner_sets_meeting_threshold_count) >= threshold

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
                    if val in self.nomination_state['voted']:
                        self.nomination_state['voted'].remove(val)
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
                    if val in self.nomination_state['accepted']:
                        self.nomination_state['accepted'].remove(val)
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

    def replace_prepare_broadcast_flag(self, new_msg: SCPPrepare):
        # find any existing messages whose .ballot is equal to new_msg.ballot
        to_remove = {m for m in self.ballot_prepare_broadcast_flags
                     if m.ballot == new_msg.ballot}
        if to_remove:
            log.node.debug("Node %s replacing old Prepare(s) %s with %s",
                           self.name, to_remove, new_msg)
        # drop them
        self.ballot_prepare_broadcast_flags.difference_update(to_remove)
        # add the fresh one
        self.ballot_prepare_broadcast_flags.add(new_msg)

    def prepare_ballot_msg(self):
        """
        Prepare Ballot for Prepare Balloting phase
        """
        if len(self.nomination_state['confirmed']) == 0: # Check if there are any values to prepare
            log.node.info('Node %s has no confirmed values in nomination state to prepare for balloting.', self.name)
            return

        # Retrieve a Value from the Nomination 'confirmed' state
        confirmed_val = self.retrieve_confirmed_value()

        if self.is_finalized(confirmed_val):
            log.node.info('Node %s: Value to be prepared %s is already finalized, skipping SCPPrepare ballot preparation.',
                          self.name, confirmed_val)

            # Remove the finalized value from nomination confirmed state
            for state in ['confirmed', 'voted', 'accepted']:
                self.nomination_state[state] = [
                    val for val in self.nomination_state[state]
                    if val != confirmed_val
                ]
            return

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
                self.replace_prepare_broadcast_flag(prepare_msg)
                #self.ballot_prepare_broadcast_flags.add(prepare_msg)
                self.prepared_ballots[ballot.value] = prepare_msg
                if ballot.value not in self.ballot_statement_counter:
                    self.ballot_statement_counter[ballot.value] = {'voted': set(), 'accepted': set(), 'confirmed':set(), 'aborted':set()}
                    self.ballot_statement_counter[ballot.value]['voted'] = set()
                    self.ballot_statement_counter[ballot.value]['voted'].add(self)
            else:
                # If prepare_msg_counters is none then there are no counters for this value and we have to set the defaults
                prepare_msg = SCPPrepare(ballot=ballot)
                self.replace_prepare_broadcast_flag(prepare_msg)
                #self.ballot_prepare_broadcast_flags.add(prepare_msg)
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

    """
    # OLD RETRIEVE FUNCTION
    def retrieve_ballot_prepare_message(self, requesting_node):
        print("RUNNING RETRIEVE BALLOT MESSAGE")
        print("LENGTH OF PREPARE BROADCAST FLAG IS", len(self.ballot_prepare_broadcast_flags) )
        print("THE BROADCAST FLAG IS ", self.ballot_prepare_broadcast_flags)
        # Select a random ballot and check if its already been sent to the requesting_node
        if len(self.ballot_prepare_broadcast_flags) > 0:
            if requesting_node.name not in self.received_prepare_broadcast_msgs:
                retrieved_message = np.random.choice(list(self.ballot_prepare_broadcast_flags))
                if self.check_if_finalised(retrieved_message.ballot):
                    log.node.info(
                            'Node %s: Value in Ballot %s is already finalized, skipping SCPCommit preparation.',
                            self.name, retrieved_message.ballot.value)

                    # Remove the finalized ballot from balloting_state['confirmed']
                    return None

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
    """


    def retrieve_ballot_prepare_message(self, sending_node):
        print("RUNNING RETRIEVE BALLOT MESSAGE")
        print("LENGTH OF PREPARE BROADCAST FLAG IS", len(sending_node.ballot_prepare_broadcast_flags) )
        print("THE BROADCAST FLAG IS ", sending_node.ballot_prepare_broadcast_flags)
        # Select a random ballot and check if its already been sent to the requesting_node
        if len(sending_node.ballot_prepare_broadcast_flags) > 0:
            if sending_node.name not in self.received_prepare_broadcast_msgs:
                retrieved_message = np.random.choice(list(sending_node.ballot_prepare_broadcast_flags))
                if self.check_if_finalised(retrieved_message.ballot):
                    log.node.info(
                            'Node %s: Value in Ballot %s is already finalized, skipping SCPCommit preparation.',
                            self.name, retrieved_message.ballot.value)

                    return None

                self.received_prepare_broadcast_msgs[sending_node.name] = [retrieved_message]
                return retrieved_message

            else:
            # elif len(self.received_prepare_broadcast_msgs[sending_node.name]) != len(list(sending_node.ballot_prepare_broadcast_flags)):
                #statement = True
                #while statement:
                    retrieved_message = np.random.choice(list(sending_node.ballot_prepare_broadcast_flags))
                    if retrieved_message not in self.received_prepare_broadcast_msgs[sending_node.name]:
                        self.received_prepare_broadcast_msgs[sending_node.name].append(retrieved_message)
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
            if self.is_ballot_finalized(confirmed_ballot):
                log.node.info('Node %s: Value in Ballot %s is already finalized, skipping SCPCommit preparation.', self.name,
                              confirmed_ballot.value)

                # Remove the finalized ballot from all balloting states
                self.reset_prepare_ballot_phase(confirmed_ballot)
                self.reset_commit_phase_state(confirmed_ballot)
                return

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
        The update of the counter is done, but it doesn't help SCPPrepare as this doesn't affect prepared ballots due to commits & prepare messages being processed separately
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
                log.node.info('No commit ballots in accepted state, cannot move Ballots %s to confirmed in Node %s', ballot, self.name)


    def retrieve_ballot_commit_message(self, sending_node):
        # Check if there are any broadcast flags
        if len(sending_node.commit_ballot_broadcast_flags) > 0:
            if sending_node.name not in self.received_commit_ballot_broadcast_msgs:
                retrieved_message = np.random.choice(list(sending_node.commit_ballot_broadcast_flags))
                self.received_commit_ballot_broadcast_msgs[sending_node.name] = [retrieved_message]
                return retrieved_message

            already_sent = self.received_commit_ballot_broadcast_msgs[sending_node.name]
            if len(already_sent) < len(sending_node.commit_ballot_broadcast_flags):
                # Choose a random message not yet sent
                remaining_messages = list(set(sending_node.commit_ballot_broadcast_flags) - set(already_sent))
                retrieved_message = np.random.choice(remaining_messages)
                self.received_commit_ballot_broadcast_msgs[sending_node.name].append(retrieved_message)
                return retrieved_message

        return None


    """
    # OLD RETRIEVE COMMIT FUNCTION
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
        """

    def receive_commit_message(self):
        # self.ballot_statement_counter = {}
        # Looks like: {SCPBallot1.value: {'voted': set(Node1), ‘accepted’: set(Node2, Node3), ‘confirmed’: set(), ‘aborted’: set(), SCPBallot2.value: {'voted': set(), ‘accepted’: set(), ‘confirmed’: set(), ‘aborted’: set(node1, node2, node3)}

        sending_node = self.quorum_set.retrieve_random_peer(self)
        if sending_node is not None:
            if sending_node != self and not None:
                message = self.retrieve_ballot_commit_message(sending_node)

                if message is not None:
                    ballot = message.ballot  # Extract the ballot from the message

                    # Check if the ballot has already been finalized
                    if self.is_ballot_finalized(ballot):
                        """log.node.info('Node %s ignored commit ballot %s as it has already been finalized.', self.name,ballot)

                        # Remove the finalized ballot from all balloting states
                        for state in ['voted', 'accepted', 'confirmed']:
                            self.balloting_state[state] = {
                                k: v for k, v in self.balloting_state[state].items()
                                if v != ballot
                            }
                    
                        return  # Stop processing this ballot"""
                        self.reset_prepare_ballot_phase(ballot)
                        self.reset_commit_phase_state(ballot)

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

        if len(self.commit_ballot_state['confirmed']) == 0: # Check if there are any values to prepare
            log.node.info('Node %s has no committed ballots to externalize.', self.name)
            return

        finalised_ballot = self.retrieve_confirmed_commit_ballot() # Retrieve a Value from the SCPPrepare 'confirmed' state
        if finalised_ballot is not None:
            externalize_msg = SCPExternalize(ballot=finalised_ballot, hCounter=finalised_ballot.counter, timestamp=Globals.simulation_time)
            temp_value = copy.deepcopy(externalize_msg.ballot.value)
            # Store the externalized value in the ledger
            self.ledger.add_slot(self.slot, externalize_msg)
            # self.externalize_broadcast_flags.add(externalize_msg)
            self.externalize_broadcast_flags.add((self.slot, externalize_msg))
            self.externalized_slot_counter.add(externalize_msg)
            log.node.info('Node %s appended SCPExternalize message for slot %d to its storage and state, message = %s', self.name, self.slot, externalize_msg)
            # save to log file
            self.log_to_file(f"NODE - INFO - Node {self.name} appended SCPExternalize message for slot {self.slot} to its storage and state, message = {externalize_msg}")

            # Reset Nomination/Balloting data structures for next slot
            # self.remove_finalized_transactions(externalize_msg.ballot.value)
            #self.nomination_state['confirmed'] = []
            self.remove_all_finalized_nomination_transactions()

            self.priority_list.clear()

            self.last_nomination_start_time = Globals.simulation_time
            self.reset_commit_phase_state(externalize_msg.ballot)
            self.reset_prepare_ballot_phase(externalize_msg.ballot)

            # REMOVE TXS FROM MEMPOOL
            print("Temp Value is ", temp_value)
            self.remove_txs_from_mempool(temp_value)

            self.slot += 1
            self.nomination_round = 1
            # self.balloting_state = {'voted': {}, 'accepted': {}, 'confirmed': {}, 'aborted': {}}
            # self.commit_ballot_state = {'voted': {}, 'accepted': {}, 'confirmed': {}, 'aborted': {}}
            # self.commit_ballot_broadcast_flags = set()
            # self.ballot_prepare_broadcast_flags = set()

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

        if slot_number != self.slot:
            log.node.info(
                "Node %s: ignoring externalize for slot %d while at slot %d",
                self.name, slot_number, self.slot
            )
            return

        # Adopt the externalized value.
        log.node.info(f'Node {self.name}  adopting externalized value for slot {slot_number}: {message.ballot.value}', self.name, slot_number, message.ballot.value)
        # save to log file

        self.log_to_file(f"Node {self.name}  adopting externalized value for slot {slot_number}: {message.ballot.value}")
        self.ledger.add_slot(slot_number, message)

        # Update peer externalized statements.
        self.peer_externalised_statements.setdefault(sending_node.name, set()).add((slot_number, message))
        # Optionally, add the (slot, message) tuple to this node's own broadcast flags (or remove it, as desired).
        self.externalize_broadcast_flags.add((slot_number, message))
        self.externalized_slot_counter.add(message)

        # Reset nomination and ballot states for this slot.
        #self.remove_finalized_transactions(message.ballot.value)

        self.nomination_round = 1
        #self.nomination_state['confirmed'] = []
        self.remove_all_finalized_nomination_transactions()

        self.reset_commit_phase_state(message.ballot)
        self.reset_prepare_ballot_phase(message.ballot)

        # REMOVE TXS FROM MEMPOOL
        self.remove_txs_from_mempool(message.ballot.value)

        self.slot += 1

        log.node.info('Node %s has finalized slot %d with value %s', self.name, slot_number, message.ballot.value)


    def reset_commit_phase_state(self, finalized_ballot):
        """
        Clears commit-phase state for ballots whose value contains any transaction
        that has been finalized in the given finalized_ballot.

        This ensures that once a transaction is finalized in a slot, any ballot
        proposing that transaction (even if only part of its value) is removed,
        while ballots proposing new transactions remain.
        """
        # Build a set of finalized transaction hashes from the finalized ballot.
        finalized_tx_ids = {tx.hash for tx in finalized_ballot.value.transactions}

        def ballot_contains_finalized_tx(ballot):
            # For an SCPBallot, ballot.value.transactions is available.
            return any(tx.hash in finalized_tx_ids for tx in ballot.value.transactions)

        def value_contains_finalized_tx(value):
            # For a Value object, it has transactions directly.
            return any(tx.hash in finalized_tx_ids for tx in value.transactions)

        # 1. Clean commit_ballot_statement_counter (keys are Value objects)
        self.commit_ballot_statement_counter = {
            value: data
            for value, data in self.commit_ballot_statement_counter.items()
            if not value_contains_finalized_tx(value)
        }

        # 2. Clean commit_ballot_state for ballots (values are SCPBallot).
        for state in ['voted', 'accepted', 'confirmed']:
            self.commit_ballot_state[state] = {
                key: ballot
                for key, ballot in self.commit_ballot_state[state].items()
                if not ballot_contains_finalized_tx(ballot)
            }

        # 3. Clean commit broadcast messages.
        self.commit_ballot_broadcast_flags = {
            msg for msg in self.commit_ballot_broadcast_flags
            if not ballot_contains_finalized_tx(msg.ballot)
        }

        # 4. Clean received commit ballot broadcast messages.
        for node_name in list(self.received_commit_ballot_broadcast_msgs.keys()):
            self.received_commit_ballot_broadcast_msgs[node_name] = [
                msg for msg in self.received_commit_ballot_broadcast_msgs[node_name]
                if not ballot_contains_finalized_tx(msg.ballot)
            ]

        log.node.info("Cleared commit-phase state for ballots containing any finalized transaction at Node %s",
                      self.name)

    def reset_prepare_ballot_phase(self, finalized_ballot):
        """
        Clears prepare-ballot-phase state for ballots whose value equals the finalized ballot's value.
        This ensures that once a value is externalized, any prepare ballots proposing that value are removed,
        while ballots proposing new (in-progress) values remain intact.
        """
        finalized_value_hash = finalized_ballot.value.hash

        # 1. Remove entries from balloting_state for ballots whose value matches the finalized value.
        for state in ['voted', 'accepted', 'confirmed', 'aborted']:
            self.balloting_state[state] = {
                key: ballot
                for key, ballot in self.balloting_state[state].items()
                if ballot.value.hash != finalized_value_hash
            }

        # 2. Remove entries from the ballot statement counter for ballots with the finalized value.
        self.ballot_statement_counter = {
            value: data
            for value, data in self.ballot_statement_counter.items()
            if value.hash != finalized_value_hash
        }

        # 3. Remove entries from prepared_ballots for ballots with the finalized value.
        self.prepared_ballots = {
            value: ballot
            for value, ballot in self.prepared_ballots.items()
            if value.hash != finalized_value_hash
        }

        # 4. Remove prepare broadcast messages for ballots with the finalized value.
        self.ballot_prepare_broadcast_flags = {
            msg for msg in self.ballot_prepare_broadcast_flags
            if msg.ballot.value.hash != finalized_value_hash
        }

        # 5. Remove outdated prepare ballot messages from received prepare broadcast messages.
        for node_name in list(self.received_prepare_broadcast_msgs.keys()):
            self.received_prepare_broadcast_msgs[node_name] = [
                msg for msg in self.received_prepare_broadcast_msgs[node_name]
                if msg.ballot.value.hash != finalized_value_hash
            ]

        log.node.info("Cleared prepare-ballot-phase state for ballots with value hash %s at Node %s",
                      finalized_value_hash, self.name)

    def is_finalized(self, value):
        """
        Checks if a given value has already been finalized in any slot.
        A value is considered finalized if any of its transactions match
        the transactions in any already finalized value in the ledger.
        Returns True if such a transaction is found, otherwise False.
        """
        for slot_data in self.ledger.slots.values():
            finalized_value = slot_data['value']

            # Compare each transaction in the new value against finalized transactions
            for transaction in value.transactions:
                for finalized_transaction in finalized_value.transactions:
                    if transaction.hash == finalized_transaction.hash:
                        return True  # A matching transaction was found

        return False

    def is_ballot_finalized(self, ballot):
        """
        Checks if a given ballot's value has already been finalized.
        This is done by checking whether any transaction in the ballot's value
        matches any transaction in a finalized value.
        Returns True if a matching transaction is found, otherwise False.
        """
        return self.is_finalized(ballot.value)

    def remove_txs_from_mempool(self, value):
        """
        Removes all transactions contained in the given value from the mempool.
        This is called after externalization to ensure that finalized transactions are not reprocessed.
        """
        self.collect_finalised_transactions()

        for tx in self.finalised_transactions:
            try:
                self.mempool.transactions.remove(tx)
                log.mempool.info(
                    "Removed finalized tx %s from mempool for Node %s.", tx, self.name
                )
            except ValueError:
                # maybe it was already gone
                pass

        for tx in value.transactions:
            print("TX IS ", tx)
            try:
                self.mempool.transactions.remove(tx)
                log.mempool.info('Removed transaction %s from mempool for Node %s.', tx, self.name)
            except ValueError:
                # Transaction might not be present; that's fine.
                log.mempool.info('Transaction %s was not found in mempool for Node %s.', tx, self.name)

    def remove_all_finalized_nomination_transactions(self):
        """
        Removes from the nomination state (keys: 'voted', 'accepted', 'confirmed')
        any transaction that appears in the ledger as finalized.
        """
        # Collect finalized transaction hashes from ledger.
        finalized_hashes = set()
        for slot, ext_msg in self.ledger.slots.items():
            # Assuming ext_msg is stored as a dictionary with a "ballot" key.
            if isinstance(ext_msg, dict) and "ballot" in ext_msg:
                ballot = ext_msg["ballot"]
                # Try to support both dict and object types for ballot.
                if hasattr(ballot, 'value'):
                    value = ballot.value
                    if hasattr(value, 'transactions'):
                        for tx in value.transactions:
                            finalized_hashes.add(tx.hash)
                elif isinstance(ballot, dict) and "value" in ballot:
                    value = ballot["value"]
                    if isinstance(value, dict) and "transactions" in value:
                        for tx in value["transactions"]:
                            finalized_hashes.add(getattr(tx, 'hash', tx))
        log.node.info("Finalized transaction hashes: %s", finalized_hashes)

        # Process each nomination state category.
        for key in ['voted', 'accepted', 'confirmed']:
            new_values = []
            for value in self.nomination_state.get(key, []):
                # Make sure the value has transactions.
                if hasattr(value, 'transactions'):
                    # Filter out any transactions whose hash is in finalized_hashes.
                    filtered_tx = {tx for tx in value.transactions if tx.hash not in finalized_hashes}
                    if filtered_tx:
                        new_values.append(Value(transactions=filtered_tx))
                    else:
                        log.node.info("Removing an empty nomination value from '%s'.", key)
                else:
                    # If for some reason the value does not have transactions, keep it unchanged.
                    new_values.append(value)
            self.nomination_state[key] = new_values

        # Optionally, reset the nomination round.
        self.nomination_round = 1


    def prune_nomination_phase_data(self):
        # -- Step 1: Collect finalized Value hashes from the ledger.
        finalized_value_hashes = set()
        for slot_data in self.ledger.slots.values():
            # Each slot is a dict with key 'value' (a Value object).
            value = slot_data.get('value')
            if not value:
                continue
            finalized_value_hashes.add(value.hash)

        log.node.info("Pruning nomination data: finalized Value hashes: %s", finalized_value_hashes)

        # -- Step 2: Prune statement_counter.
        new_statement_counter = {vh: counters for vh, counters in self.statement_counter.items()
                                 if vh not in finalized_value_hashes}
        for vh in self.statement_counter:
            if vh in finalized_value_hashes:
                log.node.info("Pruning statement counter for finalized value %s", vh)
        self.statement_counter = new_statement_counter

        # -- Helper: flatten nested lists by one level.
        def flatten(values):
            flat = []
            for item in values:
                if isinstance(item, list):
                    flat.extend(item)
                else:
                    flat.append(item)
            return flat

        # -- Step 3: Prune broadcast_flags.
        new_broadcast_flags = []
        for msg in self.broadcast_flags:
            remove_flag = False
            candidate_values = None
            # First, try to get candidate Values from msg.ballot.value.
            if hasattr(msg, "ballot"):
                candidate_values = getattr(msg.ballot, "value", None)
            # If not found, try checking for an attribute like _voted.
            if candidate_values is None and hasattr(msg, "_voted"):
                candidate_values = msg._voted
            if candidate_values:
                # If candidate_values is a list, flatten it one level.
                if isinstance(candidate_values, list):
                    candidates = flatten(candidate_values)
                else:
                    candidates = [candidate_values]
                # Check each candidate Value.
                for candidate in candidates:
                    if hasattr(candidate, "hash"):
                        if candidate.hash in finalized_value_hashes:
                            remove_flag = True
                            log.node.info("Pruning broadcast message %s because candidate Value %s is finalized",
                                          msg, candidate.hash)
                            break
            if not remove_flag:
                new_broadcast_flags.append(msg)
        self.broadcast_flags = new_broadcast_flags

        log.node.info("Pruning complete. Updated statement_counter: %s, broadcast_flags count: %d",
                      self.statement_counter, len(self.broadcast_flags))
