# WARNING: RUN TESTS IN CASE OF USE

# `QuorumSet` Class Documentation  

## Overview  

The `QuorumSet` class represents a quorum set within the Stellar Consensus Protocol (SCP). A quorum set consists of nodes and optional inner quorum sets, with a specified threshold for consensus. The class provides functionality for managing nodes, checking thresholds, and interacting with other components during the consensus process.  

---

## Constructor  

### `__init__(self, node, **kvargs)`  

Initializes a `QuorumSet` object for a given node.  

#### Parameters:  
- `node`: The node to which this quorum set belongs.  
- `threshold` (optional): A percentage value (float or int) representing the threshold for consensus. Defaults to `10%`.  

#### Behavior:  
- Initializes empty lists for nodes and inner sets.  
- Logs the creation of the quorum set.  

#### Example:  
```python
node = Node(name="Node1")  # Assuming a Node class exists
quorum_set = QuorumSet(node=node, threshold=20)
```

---

## Methods  

### **Node and Set Management**

#### `is_inside(self, node)`  
Checks if a node is part of the quorum set.  

- **Parameters**:  
  - `node`: The node to check.  
- **Returns**:  
  - `True` if the node is in the quorum set, `False` otherwise.  
- **Example**:  
  ```python
  is_member = quorum_set.is_inside(node)
  ```

#### `remove(self, node)`  
Removes a node from the quorum set.  

- **Parameters**:  
  - `node`: The node to remove.  
- **Example**:  
  ```python
  quorum_set.remove(node)
  ```

#### `set(self, nodes, inner_sets)`  
Sets the nodes and inner sets of the quorum.  

- **Parameters**:  
  - `nodes`: A list of nodes to include in the quorum set.  
  - `inner_sets`: A list of inner sets to include in the quorum set (optional).  
- **Example**:  
  ```python
  quorum_set.set(nodes=[node1, node2], inner_sets=[[inner_node1]])
  ```

---

### **Node Retrieval**

#### `get_node(self)`  
Retrieves a random node from the quorum set, excluding the owning node.  

- **Returns**:  
  - A random node or `None` if the quorum set is empty.  
- **Example**:  
  ```python
  random_node = quorum_set.get_node()
  ```

#### `get_nodes(self)`  
Returns a copy of the list of nodes in the quorum set.  

- **Returns**:  
  - A list of nodes.  
- **Example**:  
  ```python
  nodes = quorum_set.get_nodes()
  ```

#### `get_inner_sets(self)`  
Returns a copy of the list of inner sets in the quorum set.  

- **Returns**:  
  - A list of inner sets.  
- **Example**:  
  ```python
  inner_sets = quorum_set.get_inner_sets()
  ```

#### `retrieve_random_peer(self, calling_node)`  
Retrieves a random peer from the quorum set, excluding the calling node.  

- **Parameters**:  
  - `calling_node`: The node to exclude from the selection.  
- **Returns**:  
  - A random peer or `None` if no peers are available.  
- **Example**:  
  ```python
  random_peer = quorum_set.retrieve_random_peer(calling_node=node)
  ```

---

### **Threshold and Quorum Checks**

#### `minimum_quorum(self)`  
Calculates the minimum number of nodes required to meet the threshold.  

- **Returns**:  
  - The minimum number of nodes as an integer.  
- **Example**:  
  ```python
  min_quorum = quorum_set.minimum_quorum
  ```

#### `check_threshold(self, val, quorum, threshold, node_statement_counter)`  
Checks if the quorum meets the specified threshold for a given value.  

- **Parameters**:  
  - `val`: The value to check.  
  - `quorum`: The quorum set to evaluate.  
  - `threshold`: The threshold value.  
  - `node_statement_counter`: A counter tracking node statements.  
- **Returns**:  
  - `True` if the threshold is met, `False` otherwise.  

---

#### `check_prepare_threshold(self, ballot, quorum, threshold, prepare_statement_counter)`  
Checks if the prepare threshold is met for a given ballot.  

- **Parameters**:  
  - `ballot`: The ballot to check.  
  - `quorum`: The quorum set to evaluate.  
  - `threshold`: The threshold value.  
  - `prepare_statement_counter`: A counter tracking prepare statements.  
- **Returns**:  
  - `True` if the threshold is met, `False` otherwise.  

---

### **Broadcast and Inner Set Checks**

#### `get_nodes_with_broadcast_prepare_msgs(self, calling_node, quorum)`  
Retrieves nodes in the quorum that have broadcast prepare messages.  

- **Parameters**:  
  - `calling_node`: The calling node to exclude.  
  - `quorum`: The quorum set to evaluate.  
- **Returns**:  
  - A list of nodes with broadcast prepare messages.  

#### `check_inner_set_blocking_threshold(self, calling_node, val, quorum)`  
Checks if any nodes in the inner set block a given value.  

- **Parameters**:  
  - `calling_node`: The calling node.  
  - `val`: The value to check.  
  - `quorum`: The quorum set to evaluate.  
- **Returns**:  
  - The count of nodes blocking the value.  

---

## Properties  

### `minimum_quorum`  
- **Description**: Returns the minimum number of nodes required to meet the quorum threshold.  
- **Type**: `int`  

---

## Use Cases  

1. **Quorum Management**  
   Set and manage nodes and inner sets for quorum evaluation.  
   ```python
   quorum_set.set(nodes=[node1, node2], inner_sets=[[inner_node1]])
   ```

2. **Threshold Evaluation**  
   Check if a quorum meets the required threshold for consensus.  
   ```python
   is_threshold_met = quorum_set.check_threshold(val=value, quorum=quorum, threshold=10, node_statement_counter=counter)
   ```

3. **Node Retrieval**  
   Retrieve random nodes or peers for consensus operations.  
   ```python
   random_peer = quorum_set.retrieve_random_peer(calling_node=node)
   ```

---

## Key Features  

- **Node and Set Management**: Flexible methods for adding, removing, and managing quorum members.  
- **Threshold Evaluation**: Supports detailed checks for SCP threshold rules.  
- **Random Selection**: Includes methods for retrieving random nodes or peers for simulation purposes.  
