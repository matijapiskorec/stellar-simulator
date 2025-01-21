# `Node` Class Documentation  

## Overview  

The `Node` class represents a node in the Stellar Consensus Protocol (SCP) simulation. A node is a fundamental building block in the consensus process, responsible for managing transactions, interacting with quorum sets, broadcasting messages, and handling the nomination and ballot phases of SCP.  

---

## Constructor  

### `__init__(self, name, quorum_set=None, ledger=None, storage=None)`  

Initializes a `Node` with a given name and optional components.  

#### Parameters:  
- `name` (`str`): The unique identifier for the node.  
- `quorum_set` (`QuorumSet`, optional): The quorum set associated with the node. Defaults to a new `QuorumSet` instance.  
- `ledger` (`Ledger`, optional): The ledger for the node. Defaults to a new `Ledger` instance.  
- `storage` (`Storage`, optional): The storage for the node. Defaults to a new `Storage` instance.  

#### Behavior:  
- Initializes various states for nomination, balloting, and message tracking.  
- Logs the creation of the node and its associated components.  

#### Example:  
```python
node = Node(name="Node1")
```

---

## Key Attributes  

### Core Components  
- **`name`** (`str`): The name of the node.  
- **`quorum_set`** (`QuorumSet`): The quorum set associated with the node.  
- **`ledger`** (`Ledger`): The ledger for managing transactions.  
- **`storage`** (`Storage`): The storage for managing messages.  
- **`mempool`**: The mempool for storing pending transactions.  

### State Management  
- **`nomination_state`** (`dict`): Tracks the nomination state (`voted`, `accepted`, `confirmed`).  
- **`balloting_state`** (`dict`): Tracks the balloting state (`voted`, `accepted`, `confirmed`, `aborted`).  
- **`statement_counter`** (`dict`): Tracks statements made by nodes for specific values.  

---

## Methods  

### General  

#### `__repr__(self)`  
Returns a string representation of the node.  

#### `__hash__(self)`  
Makes the `Node` class hashable, allowing instances to be used in sets or as dictionary keys.  

#### `__eq__(self, name)`  
Compares the node with a given name for equality.  

---

### Quorum Management  

#### `add_to_quorum(self, nodes)`  
Adds nodes to the quorum set.  

#### `set_quorum(self, nodes, inner_sets)`  
Sets the quorum set with specified nodes and inner sets.  

#### `get_neighbors(self)`  
Determines the set of neighbors for the node based on quorum slices and weights.  

#### `get_highest_priority_neighbor(self)`  
Returns the neighbor with the highest priority based on the SCP priority function.  

---

### Transaction and Ledger Management  

#### `attach_mempool(self, mempool)`  
Attaches a mempool to the node.  

#### `retrieve_transaction_from_mempool(self)`  
Retrieves a transaction from the mempool and adds it to the ledger.  

---

### SCP Nomination Phase  

#### `nominate(self)`  
Initiates the nomination process by preparing and broadcasting `SCPNominate` messages.  

#### `prepare_nomination_msg(self)`  
Prepares an `SCPNominate` message based on the node's current transactions and accepted values.  

#### `retrieve_confirmed_value(self)`  
Retrieves a confirmed value from the nomination state.  

#### `update_nomination_state(self, val, field)`  
Updates the nomination state by moving a value between states (`voted`, `accepted`, `confirmed`).  

---

### SCP Ballot Phase  

#### `prepare_ballot_msg(self)`  
Prepares an `SCPBallot` for the prepare balloting phase.  

#### `process_prepare_ballot_message(self, message)`  
Processes a received prepare ballot message, updating the node's balloting state.  

#### `abort_ballots(self, received_ballot)`  
Aborts ballots in the `voted` or `accepted` state with a lower counter than the received ballot.  

#### `check_Prepare_Quorum_threshold(self, ballot)`  
Checks if the prepare quorum threshold is met for a given ballot.  

#### `update_prepare_balloting_state(self, ballot, field)`  
Updates the prepare balloting state by moving a ballot between states (`voted`, `accepted`, `confirmed`).  

---

### Message Management  

#### `retrieve_broadcast_message(self, requesting_node)`  
Retrieves a broadcasted message for a specific requesting node.  

#### `process_received_message(self, message)`  
Processes a received message, updating the nomination state.  

#### `retrieve_message_from_peer(self)`  
Retrieves a message from a random peer.  

#### `retrieve_ballot_prepare_message(self, requesting_node)`  
Retrieves a prepare message for a specific requesting node.  

---

### SCP Utility Functions  

#### `Gi(self, values)`  
Calculates a hash-based priority value for SCP.  

#### `priority(self, v)`  
Determines the priority of a neighbor node based on the SCP priority function.  

#### `check_Quorum_threshold(self, val)`  
Checks if the quorum threshold is met for a specific value.  

#### `check_Blocking_threshold(self, val)`  
Checks if the blocking threshold is met for a specific value.  

---

## Use Cases  

1. **Node Initialization**  
   Create and configure a node for SCP participation.  
   ```python
   node = Node(name="Node1")
   node.set_quorum(nodes=[node2, node3], inner_sets=[[node4]])
   ```

2. **Transaction Handling**  
   Attach a mempool and retrieve transactions for the ledger.  
   ```python
   node.attach_mempool(mempool)
   node.retrieve_transaction_from_mempool()
   ```

3. **Nomination and Balloting**  
   Handle nomination and prepare balloting phases in SCP.  
   ```python
   node.nominate()
   node.prepare_ballot_msg()
   ```

4. **Message Broadcasting and Retrieval**  
   Broadcast and retrieve SCP messages for consensus.  
   ```python
   message = node.retrieve_broadcast_message(requesting_node=node2)
   node.process_received_message(message)
   ```

---

## Key Features  

- **Consensus Protocol Integration**: Implements key phases of SCP, including nomination and balloting.  
- **Transaction Management**: Manages transactions through a ledger and mempool.  
- **Flexible Quorum Handling**: Integrates with quorum sets for node interactions and threshold evaluations.  
- **Message Handling**: Facilitates message broadcasting, retrieval, and processing in SCP.  

---

## TODOs:

1. **Optimize Threshold Checks**: Refactor and optimize threshold evaluation for large quorum sets.  
2. **Enhanced Logging**: Provide more detailed logs for debugging and simulation analysis.  
3. **Event-Driven Nomination**: Implement event-driven mechanisms to advance nomination rounds based on simulation time.  
4. **Duplicate Checks**: Ensure efficient handling of duplicate transactions and messages.  
