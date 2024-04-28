"""
=========================
Node
=========================

Author: Matija Piskorec, Jaime de Vivero Woods
Last update: April 2024

Node class.

Documentation:

[2] Nicolas Barry and Giuliano Losa and David Mazieres and Jed McCaleb and Stanislas Polu, The Stellar Consensus Protocol (SCP) - technical implementation draft, https://datatracker.ietf.org/doc/draft-mazieres-dinrg-scp/05/
"""

from Log import log
from Event import Event
from FBAConsensus import FBAConsensus
from Ledger import Ledger
from QuorumSet import QuorumSet
from SCPNominate import SCPNominate
from Value import Value
from Storage import Storage
from Globals import Globals
import copy

import random
import xdrlib3
import hashlib

# class Node(FBAConsensus):
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

        # TODO: Consider making a special structure to store messages on nodes!
        # self.messages = []
        self.storage = storage if storage is not None else Storage(self)
        default_state = {'voted': [], 'accepted': [], 'confirmed': []}
        self.nomination_state = copy.deepcopy(default_state)
        self.balloting_state = copy.deepcopy(default_state)
        self.statement_counter = {} # This hashmap (or dictionary) keeps track of all Values added and how many times unique nodes have made statements on it
        # This dictionary looks like this {Value_hash: {'voted': {node_id: count,...}}, {'accepted': {node_id:count}}}

        # From the documentation [1]:
        # A node always begins nomination in round "1".  Round "n" lasts for
        # "1+n" seconds, after which, if no value has been confirmed nominated,
        # the node proceeds to round "n+1".  A node continues to echo votes
        # from the highest priority neighbor in prior rounds as well as the
        # current round.  In particular, until any value is confirmed
        # nominated, a node continues expanding its "voted" field with values
        # nominated by highest priority neighbors from prior rounds even when
        # the values appeared after the end of those prior rounds.
        self.nomination_round = 1

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
        transaction = self.mempool.get_transaction()
        if transaction is not None:
            # TODO: Check the validity of the transaction in the retrieve_transactions_from_mempool() in Node!
            log.node.info('Node %s retrieved %s from mempool.',self.name,transaction)
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
    def set_quorum(self, nodes):
        self.quorum_set.set(nodes)
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
        priority_node = self.get_highest_priority_neighbor()
        self.send_message_to_all_peers(priority_node)
        # TODO: nominate function should update nominations from peers until the quorum threshold is met
        # TODO: the respective function should be implemented and called here
        return

    def send_message_to_all_peers(self, priority_node):
        message = priority_node.storage.get_combined_messages() # returns a tuple of Values [0] is voted and [1] is accepted
        if message is not None and len(message) > 0:
            for peer in self.get_neighbors():
                if peer != priority_node:
                    peer.receive_message(priority_node, message)
        else:
            log.node.info('Priority node has no message to echo!')

    def receive_message(self, other_node, message):
        if message is not None and len(message) > 0:
            self.process_received_message(message)
            self.update_statement_count(other_node, message)
            log.node.info('Node %s retrieving messages from his highest priority neighbor Node %s!', self.name,other_node.name)
        else:
            log.node.info('Node %s has no messages to retrieve from his highest priority neighbor Node %s!', self.name, other_node.name)

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

        self.retrieve_transaction_from_mempool() # Retrieve transactions from mempool and adds it to the Node's Ledger
        if len(self.ledger.transactions) > 0:
            voted_vals.append(Value(transactions=self.ledger.transactions.copy()))
            message = SCPNominate(voted=voted_vals,accepted=[],broadcasted=True) # No accepted as node is initalised

            self.nomination_state['voted'].extend(voted_vals)
            self.storage.add_messages(message)

            log.node.info('Node %s appended SCPNominate message to its storage and state, message = %s', self.name, message)
        else:
            log.node.info('Node %s has no transactions in its ledger so it cannot nominate!', self.name)

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
                    if other_node.name in self.statement_counter[incoming_accepted.hash]['accepted']:
                        # Update the count by 1
                        self.statement_counter[incoming_accepted.hash]['accepted'][other_node.name] += 1
                    else:
                        # As value has a dictionary but this node isn't in it, simpy set the node counter to 1
                        self.statement_counter[incoming_accepted.hash]['accepted'][other_node.name] = 1
            else:
                # Initiate dictionary for value & accepted for the value and then add the count for the node
                self.statement_counter[incoming_accepted.hash] = {"voted": {}, "accepted": {}}
                self.statement_counter[incoming_accepted.hash]['accepted'][other_node.name] = 1

        if type(incoming_voted) == Value:
                if incoming_voted.hash in self.statement_counter:
                        if other_node.name in self.statement_counter[incoming_voted.hash]['voted']:
                            self.statement_counter[incoming_voted.hash]['voted'][other_node.name] += 1
                        else:
                            self.statement_counter[incoming_voted.hash]['voted'][other_node.name] = 1
                else:
                    self.statement_counter[incoming_voted.hash] = {"voted": {}, "accepted": {}}
                    self.statement_counter[incoming_voted.hash]['voted'] = {other_node.name: 1}

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

    # TODO: Because our QuorumSet only has a single slice, all peers in it are neighbors!
    def get_neighbors(self):
        return [node for node in self.quorum_set.get_nodes()
                if self.Gi([1,self.nomination_round,node.name]) < (2**256 * self.weight(node))]

    # - Define "priority(n, v)" as "Gi(2 || n || v)", where "2" and "n"
    #   are both 32-bit XDR "int" values.
    def priority(self,v):
        return self.Gi([2,self.nomination_round,v.name])

    def get_highest_priority_neighbor(self):
        return max(self.get_neighbors(),key=self.priority)

    def is_duplicate_value(self, other_val, current_vals):
        for val in current_vals:
            if other_val == val:
                return True
        return False
