# `SCPPrepare` Class Documentation  

## Overview  

The `SCPPrepare` class represents the "Prepare" phase in the Stellar Consensus Protocol (SCP). This phase tracks the state of a ballot during the consensus process and manages associated counters that measure the progress and state of the protocol. The class is typically used in the context of quorum sets for validating and reaching agreement on transactions.  

---

## Constructor  

### `__init__(self, ballot: SCPBallot, prepared: Optional[SCPBallot] = None, aCounter: int = 0, hCounter: int = 0, cCounter: int = 0)`  

Initializes an `SCPPrepare` object with a ballot and optional counters.

#### Parameters:  
- **`ballot`** (`SCPBallot`): The current ballot in the Prepare phase.  
- **`prepared`** (`Optional[SCPBallot]`): The ballot that has been prepared (if any). Defaults to `None`.  
- **`aCounter`** (`int`): The counter for the number of times the current ballot has been accepted (`A`). Defaults to `0`.  
- **`hCounter`** (`int`): The counter for the number of times the current ballot has been confirmed as fully accepted (`H`). Defaults to `0`.  
- **`cCounter`** (`int`): The counter for the number of times the current ballot has been committed (`C`). Defaults to `0`.  

#### Behavior:  
- Initializes the `SCPPrepare` object with the provided ballot, counters, and optionally a prepared ballot.  

#### Example:  
```python
from SCPBallot import SCPBallot

ballot = SCPBallot(counter=1, value="Transaction_1")
prepare_phase = SCPPrepare(ballot=ballot, aCounter=2, hCounter=1)
```

---

## Methods  

### `__repr__(self)`  
Returns a string representation of the `SCPPrepare` object, including its ballot, prepared ballot, and counters.

#### Example:  
```python
print(prepare_phase)
# Output: SCPPrepare(ballot=SCPBallot(counter=1, value="Transaction_1"), prepared=None, aCounter=2, hCounter=1, cCounter=0)
```

---

## Attributes  

### `ballot`  
- **Description**: The current ballot in the Prepare phase.  
- **Type**: `SCPBallot`

### `prepared`  
- **Description**: The prepared ballot, representing a state of partial agreement in the quorum.  
- **Type**: `Optional[SCPBallot]`  
- **Default**: `None`

### `aCounter`  
- **Description**: Tracks the number of times the ballot has been accepted (`A`).  
- **Type**: `int`  
- **Default**: `0`

### `hCounter`  
- **Description**: Tracks the number of times the ballot has been fully accepted (`H`).  
- **Type**: `int`  
- **Default**: `0`

### `cCounter`  
- **Description**: Tracks the number of times the ballot has been committed (`C`).  
- **Type**: `int`  
- **Default**: `0`

---

## Use Cases  

1. **Tracking Consensus State**  
   Use the `SCPPrepare` class to monitor the state of the ballot during the Prepare phase of the SCP protocol.  
   ```python
   prepare_phase = SCPPrepare(ballot=ballot, aCounter=1)
   print(prepare_phase.aCounter)  # Output: 1
   ```

2. **Integration with SCP**  
   The `SCPPrepare` class integrates with other SCP components (e.g., `SCPBallot`) to manage consensus processes.  
   ```python
   prepare_phase.prepared = SCPBallot(counter=2, value="Transaction_2")
   ```

3. **Logging and Debugging**  
   Leverage the `__repr__` method to debug or log the current state of the Prepare phase.  
   ```python
   print(prepare_phase)
   ```

---

## Key Features  

- **Flexible Initialization**: Allows optional configuration of prepared ballots and counters.  
- **Protocol Support**: Tracks the progress of the SCP Prepare phase with dedicated counters.  
- **Integration Ready**: Designed to interact seamlessly with other SCP-related classes like `SCPBallot`.  
