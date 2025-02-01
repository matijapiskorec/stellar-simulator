# `Network` Class Documentation  

## Overview  

The `Network` class is responsible for setting up a Stellar validator network by initializing nodes and configuring their quorum sets based on predefined topologies. It supports generating networks with two topologies:  
1. **FULL**: Fully connected network where every node is part of every other node's quorum set.  
2. **ER**: Erdős-Rényi random graph topology where connections between nodes are randomized, and inner sets are distributed based on connectivity.  

---

## Class Attributes  

### `topologies`  
- **Description**: List of supported network topologies.  
- **Type**: `list[str]`  
- **Values**:  
  - `'FULL'`: Fully connected topology.  
  - `'ER'`: Erdős-Rényi random graph topology.  

---

## Methods  

### `generate_nodes(cls, n_nodes=2, topology='FULL')`  

Generates a set of nodes and configures their quorum sets based on the specified topology.  

#### Parameters:  
- **`n_nodes`** (`int`, default=`2`): The number of nodes to create. Must be greater than `0`.  
- **`topology`** (`str`, default=`'FULL'`): The topology to use for the network. Must be one of the values in `topologies`.  

#### Returns:  
- **`list[Node]`**: A list of `Node` objects representing the network.  

#### Behavior:  
- Creates `Node` instances and assigns quorum sets based on the specified topology.  
- Logs the creation of nodes and their quorum sets for debugging and analysis.  

#### Example:  
```python
from Network import Network

nodes = Network.generate_nodes(n_nodes=5, topology='FULL')
```

---

### Supported Topologies  

#### **FULL**  
- Every node is added to the quorum set of every other node, including itself.  
- Ensures a fully connected network where all nodes participate in each other's quorum.  

#### **ER (Erdős-Rényi)**  
- Generates a random graph where nodes are connected with a probability of 0.5.  
- Nodes may belong to both quorum sets and inner sets, based on their connectivity in the random graph.  
- Nodes that are not part of the largest connected component (LCC) are excluded from quorum sets.  

---

### Logging and Debugging  

- **Node Creation**: Logs when a node is created.  
- **Quorum Configuration**: Logs the nodes added to each node's quorum set and inner sets.  
- **Exclusion**: Logs nodes excluded from quorum sets in the ER topology.  

#### Example Log Output:  
```
Node created: [Node: 0]
Calculating quorum sets based on the network topology=FULL
Adding nodes [Node: 0, Node: 1] to the quorum set of Node [Node: 0]
...
```

---

## Use Cases  

1. **Generate Fully Connected Network**  
   Create a network where every node participates in every other's quorum set.  
   ```python
   nodes = Network.generate_nodes(n_nodes=5, topology='FULL')
   ```

2. **Generate Randomized Network**  
   Create a network with randomized connections using the Erdős-Rényi topology.  
   ```python
   nodes = Network.generate_nodes(n_nodes=10, topology='ER')
   ```

3. **Simulate Connectivity and Failure**  
   Use the generated network to simulate the impact of node failures or connectivity changes in the Stellar Consensus Protocol.  

---

## Key Features  

- **Flexible Topology Generation**: Supports fully connected and randomized graph-based topologies.  
- **Dynamic Inner Sets**: Configures inner sets based on graph connectivity, providing realistic quorum configurations.  
- **Node Exclusion Handling**: Identifies and logs nodes that are not part of any quorum set in the ER topology.  

---

## Future Improvements  

1. **Dynamic Topologies**: Extend support for additional topologies such as scale-free networks or small-world networks.  
2. **Node Removal**: Automatically remove nodes excluded from all quorum sets in the ER topology.  
3. **Threshold Configuration**: Allow dynamic adjustment of quorum thresholds during network setup.  
4. **Custom Graph Parameters**: Provide more flexibility in specifying graph parameters for the ER topology (e.g., connectivity probability).  
