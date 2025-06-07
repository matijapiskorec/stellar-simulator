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
import math
import random
from collections import deque

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
from typing import List

def _flatten_quorum_list(q: List) -> List["Node"]:
    """
    Recursively flatten a (possibly nested) list of Node objects.
    If an element is a Node, add it. If it’s a list, recurse into it.
    """
    result = []
    for x in q:
        if isinstance(x, Node):
            result.append(x)
        elif isinstance(x, list):
            result.extend(_flatten_quorum_list(x))
        # anything else we ignore
    return result



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
        self.tx_queue = deque()

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
        self.MAX_SLOT_TXS = 20

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
        if self.slot == 1: # no slots finalised yet
            return
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
        if self in self.priority_list:
            msg = self.prepare_nomination_msg() # Prepares Values for Nomination and broadcasts message
            if msg is None:
                return
            voted_val = msg.voted[0]
            accepted_val = msg.accepted[0] if msg.accepted else None

            if type(voted_val) is Value and self.check_Quorum_threshold(voted_val):
                log.node.info('Quorum threshold met for voted value %s at Node %s after preparation', voted_val, self.name)
                self.update_nomination_state(voted_val, "voted")

            if type(accepted_val) is Value and self.check_Quorum_threshold(accepted_val):
                log.node.info('Quorum threshold met for accepted value %s at Node %s after preparation', accepted_val, self.name)
                self.update_nomination_state(accepted_val, "accepted")
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
        if len(self.priority_list) < 1:
            log.node.info("Node %s has no valid priority neighbor!", self.name)
            return
        #peers = list(self.get_priority_list())
        #peers.sort(key=lambda p: self.priority(p), reverse=True)
        for priority_node in self.priority_list:
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
                        ##################################################
                        ##################################################
                        # NEW AND VERIFY!!!!!!!!!!!!!!!!!!!!!!
                        ### MAKE SURRE!!!!!
                        ##################################################
                        ##################################################
                        """ if voted_val not in self.nomination_state["voted"] and voted_val not in self.nomination_state[
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

        # 1) Prune any already-finalized tx from our current nomination state
        for phase in ['voted', 'accepted', 'confirmed']:
            pruned = []
            for old_val in self.nomination_state.get(phase, []):
                keep = {t for t in old_val.transactions if t.hash not in finalized_tx_ids}
                if keep:
                    pruned.append(Value(transactions=keep))
            self.nomination_state[phase] = pruned

        # --- Handle incoming “voted” field ---
        incoming_voted = message[0]
        if isinstance(incoming_voted, Value):
            # 1) Prune out finalized txs
            filtered = {tx for tx in incoming_voted.transactions if tx.hash not in finalized_tx_ids}
            if filtered:
                # 2) Merge with our existing voted Values
                current = self.nomination_state.get('voted', [])
                merged = Value.combine(current + [Value(transactions=filtered)])

                # 3) ENFORCE MAX_SLOT_TXS CAP
                txs = sorted(merged.transactions, key=lambda tx: tx.hash)
                if len(txs) > self.MAX_SLOT_TXS:
                    capped = set(txs[: self.MAX_SLOT_TXS])
                    merged = Value(transactions=capped)
                    log.node.info(
                        "Node %s: truncating merged voted txs → %d (slot limit).",
                        self.name, self.MAX_SLOT_TXS
                    )

                # 4) Store back
                self.nomination_state['voted'] = [merged]
                log.node.info(
                    "Node %s updated voted nomination state with capped merged value: %s",
                    self.name, merged
                )

        # --- Handle incoming “accepted” field ---
        incoming_accepted = message[1]
        if isinstance(incoming_accepted, Value):
            # Same pattern: prune, merge, cap, store
            filtered = {tx for tx in incoming_accepted.transactions if tx.hash not in finalized_tx_ids}
            if filtered:
                current = self.nomination_state.get('accepted', [])
                merged = Value.combine(current + [Value(transactions=filtered)])

                # Cap it
                txs = sorted(merged.transactions, key=lambda tx: tx.hash)
                if len(txs) > self.MAX_SLOT_TXS:
                    capped = set(txs[: self.MAX_SLOT_TXS])
                    merged = Value(transactions=capped)
                    log.node.info(
                        "Node %s: truncating merged accepted txs → %d (slot limit).",
                        self.name, self.MAX_SLOT_TXS
                    )

                self.nomination_state['accepted'] = [merged]
                log.node.info(
                    "Node %s updated accepted nomination state with capped merged value: %s",
                    self.name, merged
                )

        # Broadcast your updated state
        self.update_local_nomination_broadcast()

    """
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

            # 4) enforce MAX_SLOT_TXS
            txs = list(combined_voted.transactions)

            #if len(txs) > self.MAX_SLOT_TXS:
                # e.g. take first N (or random.sample for fairness)
                #limited = set(txs[:self.MAX_SLOT_TXS])
                #combined_voted = Value(transactions=limited)
                #log.node.info( 'Node %s: truncating merged voted txs → %d (slot limit).', self.name, self.MAX_SLOT_TXS)


            self.nomination_state['voted'] = [combined_voted]
            log.node.info('Node %s updated its voted nomination state with combined value: %s', self.name,
                          combined_voted)


            # Process the "accepted" nomination field.
            #incoming_accepted = message[1]
            #if isinstance(incoming_accepted, Value):
    
            #    self.nomination_state['accepted'].append(incoming_accepted)
            #    pruned = []
            #    for old_val in self.nomination_state.get('accepted', []):
            #        keep = {t for t in old_val.transactions
            #                if t.hash not in self.finalised_transactions}
            #        if keep:
            #            pruned.append(Value(transactions=keep))
            #    self.nomination_state['accepted'] = pruned
            #    log.node.info('Node %s updated its accepted nomination state with combined value: %s', self.name,
            #                  pruned)

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
                    
                    #if len(txs) > self.MAX_SLOT_TXS:
                    #    limited = set(txs[:self.MAX_SLOT_TXS])
                    #    combined_accepted = Value(transactions=limited)
                    #    log.node.info(
                    #        'Node %s: truncating merged accepted txs → %d (slot limit).',
                    #        self.name, self.MAX_SLOT_TXS
                    #   )

                    # 5) store back as a single accepted Value
                    self.nomination_state['accepted'] = [combined_accepted]
                    log.node.info(
                        'Node %s updated its accepted nomination state with combined value: %s',
                        self.name, combined_accepted
                    )

            self.update_local_nomination_broadcast()"""

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
        Prepares an SCPNominate message by selecting up to MAX_SLOT_TXS new transactions
        using a sliding-window queue. Every seen transaction is enqueued, and each slot
        nominates at most MAX_SLOT_TXS in FIFO order, ensuring no starvation.
        """
        # Initialize tx_queue if not already present
        if not hasattr(self, 'tx_queue'):
            from collections import deque
            self.tx_queue = deque()

        # Step 1: Enqueue any new transactions from mempool
        all_tx = self.mempool.get_all_transactions()
        for tx in all_tx:
            # Only enqueue if not finalized and not already enqueued
            if tx.hash not in self.finalised_transactions and tx not in self.tx_queue:
                self.tx_queue.append(tx)

        # Step 2: Prune nomination_state of finalized txs
        self.collect_finalised_transactions()
        self.clean_prepare_and_commit_state()
        for phase in ['voted', 'accepted', 'confirmed']:
            pruned = []
            for old_val in self.nomination_state.get(phase, []):
                keep = {t for t in old_val.transactions if t.hash not in self.finalised_transactions}
                if keep:
                    pruned.append(Value(transactions=keep))
            self.nomination_state[phase] = pruned

        # Step 3: Select up to MAX_SLOT_TXS from the front of the tx_queue
        to_nominate = []
        for _ in range(min(self.MAX_SLOT_TXS, len(self.tx_queue))):
            to_nominate.append(self.tx_queue.popleft())

        if not to_nominate:
            log.node.info('Node %s found no transactions to nominate after queue processing.', self.name)
            return

        # Step 4: Build new Value and merge with existing 'voted'
        new_value = Value(transactions=set(to_nominate))
        if self.is_value_already_present(new_value):
            log.node.info('Node %s already has a nomination with transactions %s. Skipping.',
                          self.name, new_value.transactions)
            return

        if self.nomination_state['voted']:
            existing = self.nomination_state['voted']
            combined = Value.combine(existing + [new_value])
            # Optionally enforce cap after merge (rarely needed since queue ensures cap)
            if len(combined.transactions) > self.MAX_SLOT_TXS:
                sorted_txs = sorted(combined.transactions, key=lambda tx: tx.hash)
                capped = set(sorted_txs[:self.MAX_SLOT_TXS])
                combined = Value(transactions=capped)
                log.node.info(
                    'Node %s: truncating merged %d txs → %d (slot limit).',
                    self.name, len(sorted_txs), self.MAX_SLOT_TXS
                )
            self.nomination_state['voted'] = [combined]
            log.node.info('Node %s merged new txs into voted nomination: %s', self.name, combined)
        else:
            self.nomination_state['voted'] = [new_value]
            log.node.info('Node %s set its voted nomination to new value: %s', self.name, new_value)

        # Step 5: Broadcast the SCPNominate message
        message = SCPNominate(
            voted=self.nomination_state['voted'],
            accepted=self.nomination_state['accepted'],
            confirmed=self.nomination_state['confirmed'],
        )
        self.storage.add_messages(message)
        self.broadcast_flags = [message]
        log.node.info('Node %s prepared SCPNominate message: %s', self.name, message)
        return message

    """
    def prepare_nomination_msg(self):

        #if len(self.nomination_state['voted']) >= 100:
        #    return

        # Step 1: Get all transactions from the mempool
        all_tx = self.mempool.get_all_transactions()

        if not all_tx:
            log.node.info('Node %s found no transactions to nominate.', self.name)
            return

        # Step 2: Update finalized transactions and prune 'voted'
        self.collect_finalised_transactions()
        self.clean_prepare_and_commit_state()  # Optional: if you want to clean out states fully

        # OLD PRUNE REPLACED FOR PRUNNING OF ALL STATES
        #pruned = []
        #for old_val in self.nomination_state.get('voted', []):
        #    keep = {t for t in old_val.transactions if t.hash not in self.finalised_transactions}
        #    if keep:
        #        pruned.append(Value(transactions=keep))
        #self.nomination_state['voted'] = pruned

        for phase in ['voted', 'accepted', 'confirmed']:
            pruned = []
            for old_val in self.nomination_state.get(phase, []):
                keep = {t for t in old_val.transactions if t.hash not in self.finalised_transactions}
                if keep:
                    pruned.append(Value(transactions=keep))
            self.nomination_state[phase] = pruned

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
        new_transactions = {t for t in all_tx if t.hash not in excluded_hashes}
        if not new_transactions:
            log.node.info('Node %s found no new transactions to nominate after filtering.', self.name)
            new_transactions = set()


        # *** ENFORCE SLOT SIZE LIMIT HERE ***
        #if len(new_transactions) > self.MAX_SLOT_TXS:
        #    # choose the top-fee ones
        #    sorted_txs = sorted(new_transactions, key=lambda t: t.hash, reverse=True)
        #    limited_set = set(sorted_txs[:self.MAX_SLOT_TXS])
        #    log.node.info(
        #        'Node %s: truncating %d new txs → %d (slot limit).',
        #        self.name, len(new_transactions), self.MAX_SLOT_TXS
        #    )
        #else:
        #    limited_set = new_transactions


        # Step 5: Wrap filtered transactions in a new Value
        new_value = Value(transactions=new_transactions)
        if self.is_value_already_present(new_value):
            log.node.info('Node %s already has a nomination with transactions %s. Skipping nomination.',
                          self.name, new_value.transactions)
            return

        # Step 6: Merge with existing 'voted'
        if self.nomination_state['voted']:
            existing = self.nomination_state['voted']
            combined_value = Value.combine(existing + [new_value])

            # --- ENFORCE SLOT SIZE LIMIT AFTER MERGE ---
            
            #if len(combined_value.transactions) > self.MAX_SLOT_TXS:
            #    # pick a deterministic subset (e.g. first 100 by hash)
            #    txs_sorted = sorted(combined_value.transactions, key=lambda tx: tx.hash)
            #    capped = set(txs_sorted[:self.MAX_SLOT_TXS])
            #    combined_value = Value(transactions=capped)
            #    log.node.info(
            #        'Node %s: truncating merged %d txs → %d (slot limit).',
            #        self.name, len(txs_sorted), self.MAX_SLOT_TXS
            #    )
            # ---------------------------------------------

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
        voted_vals = self.nomination_state['voted']  # every Value you've voted for
        accepted_vals = self.nomination_state['accepted']  # every Value you've accepted
        confirmed_vals = self.nomination_state['confirmed']

        # Build the nomination that echoes your full history
        message = SCPNominate(
            voted=voted_vals,
            accepted=accepted_vals,
            confirmed=confirmed_vals
        )

        # Push or assign it so peers pull this exact list
        self.storage.add_messages(message)
        self.broadcast_flags = [message]
        log.node.info('Node %s prepared SCPNominate message: %s', self.name, message)
        return message"""

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

    def _flatten_nested(self, q):
        """
        Recursively descend into `q`, which may be:
          - a Node
          - a list of Node
          - a list of lists (and so on)
        Return a flat Python list of all Node objects found inside.
        """
        flat = []
        for x in q:
            if isinstance(x, list):
                flat.extend(self._flatten_nested(x))
            else:
                # we assume anything not a list is a Node instance
                flat.append(x)
        return flat

    def get_priority_list(self):
        print(f"Nodes in quorum set: {self.quorum_set.get_nodes()}")
        print(f"Inner sets in quorum set: {self.quorum_set.get_inner_sets()}")

        unique_nodes = set()

        # 1) Always allow “self” if hash‐prng gives it priority
        if self.Gi([1, self.nomination_round, str(self.name)]) < (2 ** 256 * 1.0):
            print("SELF WAS ADDED")
            unique_nodes.add(self)

        # 2) Check each top‐level validator
        for node in self.quorum_set.get_nodes():
            if self.Gi([1, self.nomination_round, str(node.name)]) < (
                    2 ** 256 * self.quorum_set.weight(node)):
                unique_nodes.add(node)

        # 3) Now descend into all nested inner‐sets (any depth)
        for inner_set in self.quorum_set.get_inner_sets():
            # `inner_set` might be a list of Node or a list of lists…
            all_nodes = self._flatten_nested(inner_set)
            for node in all_nodes:
                if self.Gi([1, self.nomination_round, str(node.name)]) < (
                        2 ** 256 * self.quorum_set.weight(node)):
                    unique_nodes.add(node)

        # 4) Update and return
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
        Return True iff at least `self.quorum_set.threshold` members of
        my *flattened* quorum (including nested inner-lists) have voted
        or accepted `val`.  Here `threshold` is an absolute count
        loaded straight from JSON.
        """
        # 1) We must have signed already
        if val not in self.nomination_state["voted"] \
           and val not in self.nomination_state["accepted"]:
            return False

        # 2) Grab top-level validators + every nested inner-list
        top = self.quorum_set.get_nodes()
        inner = self.quorum_set.get_inner_sets()

        def _flatten(q):
            flat = []
            for x in q:
                if isinstance(x, list):
                    flat.extend(_flatten(x))
                else:
                    flat.append(x)
            return flat

        all_peers = list(top) + _flatten(inner)
        # dedupe by object identity
        unique = []
        seen = set()
        for p in all_peers:
            if id(p) not in seen:
                seen.add(id(p))
                unique.append(p)
        # include self
        unique.append(self)

        # 3) Count who’s already voted/accepted
        entry = self.statement_counter.get(val.hash,
                   {"voted": set(), "accepted": set()})
        signed = 0
        for peer in unique:
            if peer is self or peer.name in entry["voted"] \
                             or peer.name in entry["accepted"]:
                signed += 1

        # 4) Compare against absolute JSON threshold
        return signed >= self.quorum_set.threshold


    def check_Blocking_threshold(self, val):
        """
        Checks whether `val` meets the blocking threshold.  We must count:

          1) all “validators” (top‐level) in this node’s quorum, plus
          2) all members of every nested inner‐list (recursively flattened)

        and then see if enough of them have voted/accepted to exceed (n – k).

        We also assume `self.statement_counter[val.hash]['voted']` and
        `['accepted']` are sets of Node objects that have signed.
        """

        # 1) First, the node itself must already have “voted” or “accepted” this value.
        if val not in self.nomination_state["voted"] and val not in self.nomination_state["accepted"]:
            return False

        # 2) Grab the top‐level validators and the inner_sets (which are nested lists)
        validators, inner_sets = self.quorum_set.get_quorum()

        # 3) Define a helper to recursively flatten any nested list structure:
        def _flatten(q):
            flat = []
            for x in q:
                if isinstance(x, list):
                    flat.extend(_flatten(x))
                else:
                    flat.append(x)
            return flat

        # 4) Build one flat list of *all* Nodes in this quorum: top‐level + all nested
        all_quorum_nodes = list(validators) + _flatten(inner_sets)

        # 5) n = total number of distinct Node objects in that flat quorum
        #    (duplicates can occur if the same Node appears in multiple inner‐lists;
        #     so we dedupe by identity).
        unique_quorum_nodes = []
        seen_ids = set()
        for node in all_quorum_nodes:
            if id(node) not in seen_ids:
                seen_ids.add(id(node))
                unique_quorum_nodes.append(node)
        n = len(unique_quorum_nodes)

        # 6) k = quorum_set.minimum_quorum
        k = self.quorum_set.minimum_quorum

        if n == 0:
            return False

        # 7) Count how many of those unique_quorum_nodes (excluding self) have already voted/accepted
        signed_count = 1  # start with “1” because this node itself has signed (by step #1)
        seen_signed = set()  # to avoid double‐counting the same Node
        for node in unique_quorum_nodes:
            if node is self:
                continue
            # check if that node has “voted” or “accepted” in statement_counter for this value
            voted_set = self.statement_counter[val.hash]["voted"]
            accepted_set = self.statement_counter[val.hash]["accepted"]
            if (node in voted_set or node in accepted_set) and node not in seen_signed:
                seen_signed.add(node)
                signed_count += 1

        # 8) Now we must add up, for each *inner slice*, whether that slice itself reached its blocking threshold.
        #    Suppose check_inner_set_blocking_threshold expects a flat list of Nodes in that slice.
        inner_set_count = 0
        for raw_slice in inner_sets:
            # flatten that one slice …
            flat_slice = _flatten([raw_slice])
            # … and ask QuorumSet to count how many signed
            inner_set_count += self.quorum_set.check_inner_set_blocking_threshold(
                calling_node=self,
                val=val,
                quorum=flat_slice
            )

        # 9) Finally: blocking threshold is met if (signed_count + inner_set_count) > (n – k)
        return (signed_count + inner_set_count) > (n - k)


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
                    self.ballot_statement_counter[ballot.value]['accepted'].add(self)
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
                    self.ballot_statement_counter[ballot.value]['accepted'].add(self)
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
                    self.ballot_statement_counter[received_ballot.value]['accepted'].add(sender)

                else:
                    self.ballot_statement_counter[received_ballot.value]['voted'].add(sender)
                    self.ballot_statement_counter[received_ballot.value]['accepted'].add(sender)
                return

            # Case 3: New ballot received has the same value but a lower counter
            if received_ballot.counter < self.balloting_state['voted'][received_ballot.value.hash].counter:
                log.node.info("Node %s that has been received has the same value but a lower counter than a previously voted ballot.", self.name)
                if received_ballot.value not in self.ballot_statement_counter:
                    self.ballot_statement_counter[received_ballot.value] = {'voted': set(),'accepted': set(),'confirmed': set(),'aborted': set()}
                    self.ballot_statement_counter[received_ballot.value]['voted'].add(sender)
                    self.ballot_statement_counter[received_ballot.value]['accepted'].add(sender)
                else:
                    self.ballot_statement_counter[received_ballot.value]['voted'].add(sender)
                    self.ballot_statement_counter[received_ballot.value]['accepted'].add(sender)
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
                        self.ballot_statement_counter[received_ballot.value]['accepted'].add(sender)
                    else:
                        self.ballot_statement_counter[received_ballot.value]['voted'].add(sender)
                        self.ballot_statement_counter[received_ballot.value]['accepted'].add(sender)
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
            log.node.info("Node %s hreceived a ballot with a different value and a higher counter. Abortingthis ballot.")

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
        """
        Checks whether `ballot` meets the prepare‐phase quorum threshold,
        flattening any nested inner‐sets.
        """
        val_hash = ballot.value.hash

        # 1) We must already have voted or accepted this value
        if val_hash not in self.balloting_state["voted"] and \
           val_hash not in self.balloting_state["accepted"]:
            return False

        # 2) Gather every Node in this quorum: top‐level + all nested inner‐sets
        validators, inner_sets = self.quorum_set.get_quorum()
        all_quorum = list(validators) + self._flatten_nested(inner_sets)

        # 3) Count how many have voted/accepted (excluding self)
        signed = 1  # self
        entry = self.ballot_statement_counter.get(ballot.value, {"voted": set(), "accepted": set()})
        for n in all_quorum:
            if n is self:
                continue
            if n in entry["voted"] or n in entry["accepted"]:
                signed += 1

        # 4) Compare to the minimum quorum (ceil(percent * size))
        return signed >= self.quorum_set.minimum_quorum

    def update_prepare_balloting_state(self, ballot, field):
        if field == "voted":
            if len(self.balloting_state["voted"]) > 0 :
                if ballot.value.hash in self.balloting_state['accepted']:
                    log.node.info('Value %s is already accepted for SCPPrepare phase in Node %s', ballot.value, self.name)
                    return

                if ballot.value.hash in self.balloting_state['voted']:
                    self.balloting_state["accepted"][ballot.value.hash] = (self.balloting_state["voted"][ballot.value.hash])
                    self.balloting_state["voted"].pop(ballot.value.hash)
                    log.node.info('Ballot %s has been moved to accepted for SCPPrepare phase in Node %s', ballot, self.name)
            else:
                log.node.info('No ballots in voted state, cannot move Ballot %s to accepted in Node %s', ballot, self.name)

        elif field == "accepted":
            if len(self.balloting_state["accepted"]) > 0:
                if ballot.value.hash in self.balloting_state['confirmed']:
                    log.node.info('Ballot %s is already confirmed for SCPPrepare phase in Node %s', ballot, self.name)
                    return

                if ballot.value.hash in self.balloting_state['accepted']:
                    self.balloting_state["confirmed"][ballot.value.hash] = (self.balloting_state["accepted"][ballot.value.hash])
                    self.balloting_state["accepted"].pop(ballot.value.hash)

                log.node.info('Ballot %s has been moved to confirmed for SCPPrepare phase in Node %s', ballot.value.hash, self.name)
            else:
                log.node.info('No ballots in accepted state, cannot move Ballots %s for SCPPrepare phase to confirmed in Node %s', ballot, self.name)
    # Get the counters for balloting state given a value

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


    def is_v_blocking(self, other_ballot):
        """
        True if more than (n - k) of your peers have voted/accepted other_ballot,
        i.e. v‐blocking for your current ballot.
        """
        validators, inner_sets = self.quorum_set.get_quorum()
        all_quorum = list(validators) + self._flatten_nested(inner_sets)

        # n = distinct number of peers in the flat quorum
        unique_peers = {id(n) for n in all_quorum}
        n = len(unique_peers)

        # k = minimum_quorum (ceil(percent * size))
        k = self.quorum_set.minimum_quorum
        threshold = n - k

        entry = self.ballot_statement_counter.get(other_ballot.value, {"voted": set(), "accepted": set()})
        count = len(entry["voted"] | entry["accepted"])
        return count > threshold

    def receive_prepare_message(self):
        """
        Pulls and processes *all* outstanding SCPPrepare messages
        from a single randomly‐chosen peer in one go, using a set to track seen msgs.
        """
        # 1) Pick one peer
        peer = self.quorum_set.retrieve_random_peer(self)
        if peer is None or peer is self:
            log.node.info('Node %s: no valid peer for prepare messages', self.name)
            return

        # 2) Ensure we have a SET for this peer’s seen messages
        existing = self.received_prepare_broadcast_msgs.get(peer.name)
        if not isinstance(existing, set):
            # Replace any list or other with a fresh set
            self.received_prepare_broadcast_msgs[peer.name] = set()
        seen = self.received_prepare_broadcast_msgs[peer.name]

        # 3) Gather all unseen Prepare msgs
        unseen = [msg for msg in peer.ballot_prepare_broadcast_flags if msg not in seen]
        if not unseen:
            log.node.info('Node %s: no new prepare messages from %s', self.name, peer.name)
            return

        # 4) Process each one
        for msg in unseen:
            # Mark it seen so we don't re-process
            seen.add(msg)

            # Skip if it’s already finalized
            if self.check_if_finalised(msg.ballot):
                log.node.info('Node %s: skipping finalized prepare %s from %s',
                              self.name, msg.ballot, peer.name)
                continue

            # Record & handle the ballot
            self.process_prepare_ballot_message(msg, peer)
            log.node.info('Node %s retrieved prepare from %s: %s',
                          self.name, peer.name, msg.ballot)

            b = msg.ballot
            is_ballot = isinstance(b, SCPBallot)
            b_hash = b.value.hash

            # 4a) Quorum promotions
            if is_ballot and b_hash in self.balloting_state['voted'] \
                    and self.check_Prepare_Quorum_threshold(b):
                log.node.info('Node %s: quorum met for voted %s', self.name, b)
                self.update_prepare_balloting_state(b, "voted")

            elif is_ballot and b_hash in self.balloting_state['accepted'] \
                    and self.check_Prepare_Quorum_threshold(b):
                log.node.info('Node %s: quorum met for accepted %s', self.name, b)
                self.update_prepare_balloting_state(b, "accepted")

            # 4b) Blocking‐threshold check
            for old_hash, old_ballot in list(self.balloting_state['voted'].items()):
                if old_hash != b_hash and self.is_v_blocking(b):
                    log.node.info('Node %s: %s v-blocks %s → aborting %s',
                                  self.name, b, old_ballot, old_ballot)
                    self.abort_ballots(b)
                    # ensure you vote for the blocking ballot if not already
                    if b_hash not in self.balloting_state['voted']:
                        self.balloting_state['voted'][b_hash] = b
                    break

    """ NEW RECEIVE BUT THAT TAKES SINGLE MESSAGE - NEW ONE TAKES ALL OUTSTANDING PREPARE MESSAGE FROM NODE TO AMORTIZE THE PER-PULL
    def receive_prepare_message(self):
        # 1) Fetch a peer to pull from
        peer = self.quorum_set.retrieve_random_peer(self)
        if peer is None or peer is self:
            log.node.info('Node %s: no valid peer for prepare messages', self.name)
            return

        # 2) Pull one prepare and skip if none or already finalized
        msg = self.retrieve_ballot_prepare_message(peer)
        if msg is None or self.check_if_finalised(msg.ballot):
            log.node.info('Node %s: no new prepare from %s', self.name, peer.name)
            return

        # 3) Record and process the incoming prepare
        self.process_prepare_ballot_message(msg, peer)
        log.node.info('Node %s retrieved prepare from %s: %s', self.name, peer.name, msg.ballot)

        b = msg.ballot
        is_ballot = isinstance(b, SCPBallot)
        b_hash = b.value.hash

        # 4) Quorum threshold: promote voted→accepted or accepted→confirmed
        if is_ballot and b_hash in self.balloting_state['voted'] \
                and self.check_Prepare_Quorum_threshold(b):
            log.node.info('Node %s: quorum met for voted %s', self.name, b)
            self.update_prepare_balloting_state(b, "voted")
        elif is_ballot and b_hash in self.balloting_state['accepted'] \
                and self.check_Prepare_Quorum_threshold(b):
            log.node.info('Node %s: quorum met for accepted %s', self.name, b)
            self.update_prepare_balloting_state(b, "accepted")

        # 5) Blocking threshold: abort any old voted ballots that are now v-blocked
        #    and cast your vote for the stronger one if not already
        for old_hash, old_ballot in list(self.balloting_state['voted'].items()):
            if old_hash != b_hash and self.is_v_blocking(b):
                log.node.info('Node %s: %s v-blocks %s → aborting %s',
                              self.name, b, old_ballot, old_ballot)
                self.abort_ballots(b)  # abort lower-support ballots
                # ensure you vote for the blocking ballot
                if b_hash not in self.balloting_state['voted']:
                    self.balloting_state['voted'][b_hash] = b
                break
    """

    """ OLD RECEIVE PREPARE MESSAGE WITHOUT BLOCKING THRESHOLD
    
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

    
    """



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



    def simple_process_commit_ballot_message(self, message, sender):
        """
        Simplified commit handler: just record the received ballot and track the sender.
        """
        received = message.ballot
        h = received.value.hash

        # Initialize state containers if necessary
        if h not in self.commit_ballot_state['voted']:
            self.commit_ballot_state['voted'][h] = received

        # Track senders for this ballot
        if received.value not in self.commit_ballot_statement_counter:
            self.commit_ballot_statement_counter[received.value] = {
                'voted': set(),
                'accepted': set(),
                'confirmed': set(),
                'aborted': set()
            }
        self.commit_ballot_statement_counter[received.value]['voted'].add(sender)

        # Log receipt
        log.node.info("Node %s recorded commit ballot for %s from %s", self.name, h, sender)


    """ OLD PROCESS BALLOT MESSAGE
    def process_commit_ballot_message(self, message, sender):

        #The purpose of continuing to update the counter and send this field is to assist other nodes still in the PREPARE phase in synchronizing their counters.
        #The update of the counter is done, but it doesn't help SCPPrepare as this doesn't affect prepared ballots due to commits & prepare messages being processed separately
        #Also, we do not abort, just update counters if larger

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
                self.commit_ballot_statement_counter[received_ballot.value]['accepted'].add(sender)
            else:
                self.commit_ballot_statement_counter[received_ballot.value]['voted'].add(sender)
            return"""

    def check_Commit_Quorum_threshold(self, ballot):
        """
        Return True iff at least `threshold` (absolute) of *all* nodes
        in my quorum (including nested inner-lists) have voted or accepted `ballot`.
        """

        # 1) Must have already “voted” or “accepted” yourself
        h = ballot.value.hash
        if h not in self.commit_ballot_state["voted"] and h not in self.commit_ballot_state["accepted"]:
            return False

        # 2) Grab top-level validators and nested inner_sets
        validators, inner_sets = self.quorum_set.get_quorum()

        # 3) Recursively flatten any nested list structure
        def _flatten(q):
            flat = []
            for x in q:
                if isinstance(x, list):
                    flat.extend(_flatten(x))
                else:
                    # anything not a list is assumed to be a Node
                    flat.append(x)
            return flat

        # 4) Build the full unique peer set
        all_peers = []
        all_peers.extend(validators)
        all_peers.extend(_flatten(inner_sets))
        # dedupe by identity
        seen = set()
        unique_peers = []
        for node in all_peers + [self]:  # include self
            if id(node) not in seen:
                seen.add(id(node))
                unique_peers.append(node)

        n = len(unique_peers)
        k = self.quorum_set.threshold  # absolute count from JSON

        # 5) Count how many have actually voted/accepted in commit state
        signed = 0
        for node in unique_peers:
            if node is self:
                signed += 1
            else:
                entry = self.commit_ballot_statement_counter.get(ballot.value, {"voted": set(), "accepted": set()})
                if node in entry["voted"] or node in entry["accepted"]:
                    signed += 1

        # 6) Promise if we meet threshold
        return signed >= k

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

    def _is_v_blocking_commit(self, ballot: SCPBallot) -> bool:
        """
        Returns True if more than (n - k) of your peers have voted or accepted
        the given commit ballot, meaning no quorum can form for any other ballot
        without including supporters of this one.
        """
        # 1) Gather vote/accept counts for this ballot
        entry = self.commit_ballot_statement_counter.get(
            ballot.value, {"voted": set(), "accepted": set()}
        )
        # 2) Flatten all peers (top‐level + any nested inner_sets)
        validators, inner_sets = self.quorum_set.get_quorum()

        def _flatten(q):
            flat = []
            for x in q:
                if isinstance(x, list):
                    flat.extend(_flatten(x))
                else:
                    flat.append(x)
            return flat

        all_peers = list(validators) + _flatten(inner_sets)

        # 3) Deduplicate by identity
        seen_ids = set()
        unique_peers = []
        for p in all_peers:
            if id(p) not in seen_ids:
                seen_ids.add(id(p))
                unique_peers.append(p)

        n = len(unique_peers)
        k = self.quorum_set.minimum_quorum

        # 4) Count how many of those have voted or accepted
        signed = sum(
            1
            for p in unique_peers
            if (p in entry["voted"] or p in entry["accepted"])
        )

        # 5) v-blocking if signed > (n - k)
        return signed > (n - k)

    def receive_commit_message(self):
        """
        Pulls and processes *all* outstanding SCPCommit messages
        from a single randomly‐chosen peer in one go.
        """
        # 1) Pick a peer
        peer = self.quorum_set.retrieve_random_peer(self)
        if peer is None or peer is self:
            log.node.info('Node %s: no valid peer for commit', self.name)
            return

        # 2) Ensure we have a SET for this peer’s seen commit msgs
        existing = self.received_commit_ballot_broadcast_msgs.get(peer.name)
        if not isinstance(existing, set):
            self.received_commit_ballot_broadcast_msgs[peer.name] = set()
        seen = self.received_commit_ballot_broadcast_msgs[peer.name]

        # 3) Gather all unseen commit messages
        unseen = [msg for msg in peer.commit_ballot_broadcast_flags if msg not in seen]
        if not unseen:
            log.node.info('Node %s: no new commit messages from %s', self.name, peer.name)
            return

        # 4) Process each one
        for msg in unseen:
            # Mark it seen
            seen.add(msg)

            b = msg.ballot
            log.node.info('Node %s retrieved commit %s from %s', self.name, b, peer.name)

            # 5) Finalize‐check
            if self.is_ballot_finalized(b):
                self.reset_prepare_ballot_phase(b)
                self.reset_commit_phase_state(b)
                continue

            # 6) Record the commit vote
            self.simple_process_commit_ballot_message(msg, peer)

            # 7) Quorum‐threshold promotions
            bh = b.value.hash
            if bh in self.commit_ballot_state['accepted'] and self.check_Commit_Quorum_threshold(b):
                log.node.info('Node %s: quorum met for accepted commit %s', self.name, b)
                self.update_commit_balloting_state(b, "accepted")
                self.prepare_Externalize_msg()
            elif bh in self.commit_ballot_state['voted'] and self.check_Commit_Quorum_threshold(b):
                log.node.info('Node %s: quorum met for voted commit %s', self.name, b)
                self.update_commit_balloting_state(b, "voted")

            # 8) Blocking‐threshold: abort any outstanding voted ballots v‐blocked by b
            for old_hash, old_ballot in list(self.commit_ballot_state['voted'].items()):
                if old_hash != bh and self._is_v_blocking_commit(b):
                    log.node.info('Node %s: %s v-blocks %s → aborting', self.name, b, old_ballot)
                    self.reset_commit_phase_state(old_ballot)
                    # ensure you vote for the stronger ballot if not already
                    if bh not in self.commit_ballot_state['voted']:
                        self.commit_ballot_state['voted'][bh] = b
                    break

    """
        def receive_commit_message(self):
        # 1) pick a peer
        peer = self.quorum_set.retrieve_random_peer(self)
        if peer is None or peer is self:
            log.node.info('Node %s: no valid peer for commit', self.name)
            return

        # 2) pull one commit from that peer
        msg = self.retrieve_ballot_commit_message(peer)
        if msg is None:
            log.node.info('Node %s: no commit from %s', self.name, peer.name)
            return

        b = msg.ballot
        log.node.info('Node %s retrieved commit %s from %s', self.name, b, peer.name)

        # 3) finalize‐check
        if self.is_ballot_finalized(b):
            self.reset_prepare_ballot_phase(b)
            self.reset_commit_phase_state(b)
            return

        # 4) record the commit vote
        self.simple_process_commit_ballot_message(msg, peer)

        # 5) quorum‐threshold promotions
        bh = b.value.hash
        if bh in self.commit_ballot_state['accepted'] and self.check_Commit_Quorum_threshold(b):
            log.node.info('Node %s: quorum met for accepted commit %s', self.name, b)
            self.update_commit_balloting_state(b, "accepted")
            self.prepare_Externalize_msg()
        elif bh in self.commit_ballot_state['voted'] and self.check_Commit_Quorum_threshold(b):
            log.node.info('Node %s: quorum met for voted commit %s', self.name, b)
            self.update_commit_balloting_state(b, "voted")

        # 6) blocking‐threshold: abort any outstanding voted ballots v-blocked by b
        for old_hash, old_ballot in list(self.commit_ballot_state['voted'].items()):
            if old_hash != bh and self._is_v_blocking_commit(b):
                log.node.info('Node %s: %s v-blocks %s → aborting', self.name, b, old_ballot)
                # abort the stale ballot
                self.reset_commit_phase_state(old_ballot)
                # cast your own vote for the stronger ballot if not already
                if bh not in self.commit_ballot_state['voted']:
                    self.commit_ballot_state['voted'][bh] = b
                break
    """



    """ OLD RECEIVE_COMMIT_MSG FROM 24TH MAY
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
                    #log.node.info('Node %s ignored commit ballot %s as it has already been finalized.', self.name,ballot)

                    # Remove the finalized ballot from all balloting states
                    #for state in ['voted', 'accepted', 'confirmed']:
                    #    self.balloting_state[state] = {
                    #        k: v for k, v in self.balloting_state[state].items()
                    #        if v != ballot
                    #    }

                    #return  # Stop processing this ballot
                    self.reset_prepare_ballot_phase(ballot)
                    self.reset_commit_phase_state(ballot)

                self.process_commit_ballot_message(message, sending_node)
                log.node.info('Node %s retrieving messages from his peer Node %s!', self.name, sending_node.name)
                ballot = message.ballot  # message[0] is voted field
                if type(ballot) is SCPBallot and ballot.value.hash in self.commit_ballot_state[
                    'accepted'] and self.check_Commit_Quorum_threshold(ballot):
                    log.node.info('Quorum threshold met for accepted commit ballot %s at Node %s', ballot, self.name)
                    self.update_commit_balloting_state(ballot, "accepted")
                    self.prepare_Externalize_msg()
                elif type(ballot) is SCPBallot and ballot.value.hash in self.commit_ballot_state[
                    'voted'] and self.check_Commit_Quorum_threshold(ballot):
                    log.node.info('Quorum threshold met for voted commit ballot %s at Node %s', ballot, self.name)
                    self.update_commit_balloting_state(ballot, "voted")

            else:
                log.node.info('Node %s has no SCPCommit messages to retrieve from neighbor Node %s!', self.name,
                              sending_node.name)
    else:
        log.node.info('Node %s could not retrieve peer!', self.name)
    """



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
            """
            NEW CHANGE !!!!!!!!!
            """
            # FULL reset of nomination, not just pruning
            self.reset_nomination_state()
            #self.remove_all_finalized_nomination_transactions()

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


        """
        NEW CHANGE !!!!!!!!!
        """
        # FULL reset of nomination, not just pruning
        self.reset_nomination_state()
        self.last_nomination_start_time = Globals.simulation_time
        #self.nomination_state['confirmed'] = []
        #self.remove_all_finalized_nomination_transactions()

        self.reset_commit_phase_state(message.ballot)
        self.reset_prepare_ballot_phase(message.ballot)

        # REMOVE TXS FROM MEMPOOL
        self.remove_txs_from_mempool(message.ballot.value)

        self.slot += 1

        log.node.info('Node %s has finalized slot %d with value %s', self.name, slot_number, message.ballot.value)

    """
    TRY THIS TO GET MORE SLOTS FINALISED
    """
    def reset_nomination_state(self):
        """
        Completely clear out any prior nomination state so that
        the next slot starts fresh.
        """
        self.nomination_state['voted'].clear()
        self.nomination_state['accepted'].clear()
        self.nomination_state['confirmed'].clear()
        # Optionally reset nomination round or other per-slot counters:
        self.nomination_round = 1

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
