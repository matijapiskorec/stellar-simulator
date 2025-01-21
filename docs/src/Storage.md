# `Storage` Class Documentation  

## Overview  

The `Storage` class manages the storage of messages within a node in the Stellar simulator. It ensures messages are uniquely stored, facilitates retrieval, and allows for the combination of messages into values for further processing. The class is designed to interact with the `Node` and `Value` components of the simulator.  

---

## Constructor  

### `__init__(self, node)`  
Initializes the `Storage` object for a specific node.

#### Parameters:  
- `node`: The node for which this storage is initialized.  

#### Behavior:  
- Creates an empty storage for messages.  
- Logs the initialization of the storage.  

#### Example:  
```python
node = Node(name="Node1")  # Assuming a Node class exists
storage = Storage(node=node)
```

---

## Properties  

### `messages`  
- **Description**: Returns the list of stored messages.  
- **Type**: `list`  

#### Note:  
This property currently returns a reference to the stored messages, but future updates might include returning a copy for better encapsulation.  

#### Example:  
```python
stored_messages = storage.messages
```

---

## Methods  

### `add_messages(self, messages)`  
Adds new messages to the storage.  

#### Parameters:  
- `messages`: A single message or a list of messages to add.  

#### Behavior:  
- Converts single message input into a list for uniform handling.  
- Adds messages to the storage only if they are not already present.  
- Logs each addition or detection of duplicate messages.  

#### Example:  
```python
message1 = Message(...)
message2 = Message(...)
storage.add_messages([message1, message2])
```

---

### `get_message(self)`  
Retrieves a random message from the storage.  

#### Returns:  
- A random message from the stored messages, or `None` if the storage is empty.  

#### Example:  
```python
random_message = storage.get_message()
```

---

### `get_combined_messages(self)`  
Combines the stored messages into voted and accepted values.  

#### Returns:  
- A tuple of combined values:  
  1. `voted_values` (`Value`): A combined `Value` object representing all voted values.  
  2. `accepted_values` (`Value` or empty list): A combined `Value` object representing all accepted values, or an empty list if none exist.  

#### Behavior:  
- Extracts voted and accepted values from all messages in storage.  
- Combines these values using the `Value.combine` method.  

#### Example:  
```python
voted_values, accepted_values = storage.get_combined_messages()
```

---

## Logging  

- **Initialization**: Logs the creation of storage for a specific node.  
- **Message Addition**: Logs whether a message is added or detected as a duplicate.  

---

## Use Cases  

1. **Message Management for Nodes**  
   Store and manage unique messages associated with a node.  
   ```python
   storage.add_messages([message1, message2])
   ```

2. **Random Message Retrieval**  
   Retrieve a random message from the node's storage for processing or analysis.  
   ```python
   random_message = storage.get_message()
   ```

3. **Combining Stored Messages**  
   Aggregate stored messages into unified `Value` objects for further operations.  
   ```python
   voted, accepted = storage.get_combined_messages()
   ```

---

## Key Features  

- **Unique Storage**: Ensures no duplicate messages are added.  
- **Message Combination**: Combines messages into structured `Value` objects.  
- **Random Access**: Allows retrieval of random messages from storage.  

---

## Future Improvements  

1. **Circular Import Handling**: Address potential circular imports between `Node` and `Storage`.  
2. **Encapsulation**: Modify the `messages` property to return a copy instead of a reference.  
3. **Integration**: Consider merging the `Storage` and `Ledger` classes into a single superclass to streamline message and ledger management.  
