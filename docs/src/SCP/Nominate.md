# `SCPNominate` Class Documentation  

## Overview  

The `SCPNominate` class represents the "Nominate" message in the Stellar Consensus Protocol (SCP). This message type is used during the nomination phase to propose values for agreement among nodes. The class maintains two key properties:
- **Voted Values**: Values the node has voted to include in the consensus.
- **Accepted Values**: Values the node has accepted as part of the consensus.

This class inherits from the `Message` superclass and integrates with other SCP components such as `Value`.  

---

## Constructor  

### `__init__(self, **kwargs)`  

Initializes an `SCPNominate` message with voted and accepted values.  

#### Parameters:  
- `voted` (`list[Value]`): A list of `Value` objects that have been voted on by the node.  
- `accepted` (`list[Value]`): A list of `Value` objects that have been accepted by the node.  

#### Behavior:  
- Ensures all `voted` and `accepted` values are instances of the `Value` class.  
- Logs the creation of the `SCPNominate` message.  

#### Example:  
```python
from Value import Value

value1 = Value(transactions=[])
value2 = Value(transactions=[])

scp_nominate = SCPNominate(voted=[value1], accepted=[value2])
```

---

## Properties  

### `voted`  
- **Description**: Returns the list of voted values.  
- **Type**: `list[Value]`  

#### Example:  
```python
voted_values = scp_nominate.voted
```

---

### `accepted`  
- **Description**: Returns the list of accepted values.  
- **Type**: `list[Value]`  

#### Example:  
```python
accepted_values = scp_nominate.accepted
```

---

## Methods  

### `parse_message_state(self, message)`  
Parses the state of an SCPNominate message, combining voted and accepted values into unified sets.

#### Parameters:  
- `message` (`SCPNominate`): The `SCPNominate` message to parse.  

#### Returns:  
- A list containing two elements:  
  1. A combined `Value` object of all voted values, or an empty list if none exist.  
  2. A combined `Value` object of all accepted values, or an empty list if none exist.  

#### Behavior:  
- Combines voted and accepted values using the `Value.combine` method.  

#### Example:  
```python
combined_voted, combined_accepted = scp_nominate.parse_message_state(scp_nominate)
```

---

## Logging  

- Logs the creation of an `SCPNominate` message with details about its voted and accepted values.  

---

## Use Cases  

1. **Nomination in SCP**  
   Use the `SCPNominate` class to represent and handle messages during the nomination phase of SCP.  
   ```python
   scp_nominate = SCPNominate(voted=[value1], accepted=[value2])
   ```

2. **Parsing Message State**  
   Parse and combine voted and accepted values to analyze the message state.  
   ```python
   combined_voted, combined_accepted = scp_nominate.parse_message_state(scp_nominate)
   ```

3. **Logging and Debugging**  
   Use the class's logging to debug or track the creation and state of SCPNominate messages.  
   ```python
   print(scp_nominate)
   ```

---

## Key Features  

- **Integration with SCP**: Works seamlessly within the SCP framework to represent nomination messages.  
- **State Parsing**: Provides a utility to parse and combine voted and accepted values.  
- **Validation**: Ensures that only valid `Value` objects are included in the message.  
