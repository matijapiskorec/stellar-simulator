# `Event` Class Documentation  

## Overview  

The `Event` class represents a discrete event in the Stellar Consensus Protocol (SCP) simulation. Events are characterized by a name, simulation parameters, and optional event-specific data. These events are essential for driving the simulation, enabling asynchronous operations and decision-making processes.  

---

## Constructor  

### `__init__(self, name, **kvargs)`  

Initializes an `Event` instance with a name, simulation parameters, and optional event-specific parameters.  

#### Parameters:  
- **`name`** (`str`): The name of the event, used to identify and differentiate events.  
- **`simulation_params`** (`dict`, optional): Parameters governing the simulation behavior of the event, such as average waiting time or node-specific attributes.  
- **`event_params`** (`dict`, optional): Additional data for event handlers to determine how to process the event.  

#### Behavior:  
- Logs the initialization of the event, including its parameters.  

#### Example:  
```python
event = Event(
    name="TransactionProcessing",
    simulation_params={"tau": 5, "node_specific": True},
    event_params={"priority": "high"}
)
```

---

## Methods  

### `__repr__(self)`  

Returns a string representation of the event, including its name and simulation parameters.  

#### Returns:  
- **`str`**: A string representation of the event.  

#### Example:  
```python
print(event)  
# Output: [Event TransactionProcessing, simulation_params = {'tau': 5, 'node_specific': True}]
```

---

### `__eq__(self, name)`  

Compares the event's name with a given name to determine equality.  

#### Parameters:  
- **`name`** (`str`): The name to compare with the event's name.  

#### Returns:  
- **`bool`**: `True` if the names are equal, `False` otherwise.  

#### Example:  
```python
if event == "TransactionProcessing":
    logger.log(logging.INFO, "Event matches the name.")
```

---

## Attributes  

### `name`  
- **Description**: The unique name of the event.  
- **Type**: `str`  

### `simulation_params`  
- **Description**: Parameters governing the simulation behavior of the event.  
- **Type**: `dict` or `None`  

### `event_params`  
- **Description**: Additional data for handling the event.  
- **Type**: `dict` or `None`  

---

## Logging  

- **Initialization**: Logs the creation of the event, along with its name and parameters.  

#### Example Log Output:  
```
INFO: Initialized event TransactionProcessing, simulation_params = {'tau': 5, 'node_specific': True}, event_params = {'priority': 'high'}.
```

---

## Use Cases  

1. **Event Creation**  
   Create an event with specific simulation and event parameters.  
   ```python
   event = Event(
       name="LedgerFinalization",
       simulation_params={"tau": 10},
       event_params={"max_ledger_size": 100}
   )
   ```

2. **Event Handling**  
   Use the event's attributes to determine how to process it during the simulation.  
   ```python
   if event.name == "LedgerFinalization":
       process_ledger(event.event_params)
   ```

3. **Simulation Integration**  
   Integrate events into a simulation framework like the `Gillespie` algorithm for stochastic event handling.  

---

## Key Features  

- **Flexible Design**: Supports custom simulation and event parameters.  
- **Integration-Ready**: Can be used seamlessly with components like `Gillespie` for event-driven simulations.  
- **Logging**: Provides detailed logs for event initialization and inspection.  
