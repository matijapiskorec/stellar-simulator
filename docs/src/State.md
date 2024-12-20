# `State` Class Documentation  

## Overview  

The `State` class is an enumeration (`enum.Enum`) that defines the various states used in the Stellar simulator. It includes utility methods for transitioning between states, retrieving states by value or name, and comparing states based on their order.  

### Defined States  
1. `none`: Represents the absence of a state.  
2. `init`: Represents the initial state.  
3. `vote`: Represents the voting state.  
4. `accept`: Represents the acceptance state.  
5. `confirm`: Represents the confirmation state.  

---

## Constructor  

### `State`  
The `State` class does not require explicit instantiation as it is an enumeration. States are accessed as class attributes (e.g., `State.init`).  

#### Example:  
```python
current_state = State.init
```

---

## Methods  

### `from_value(cls, value)`  
Returns the `State` corresponding to the given value.  

#### Parameters:  
- `value` (`int`): The value of the desired state.  

#### Returns:  
- The `State` with the specified value, or `None` if no match is found.  

#### Example:  
```python
state = State.from_value(2)  # Returns State.vote
```

---

### `from_name(cls, name)`  
Returns the `State` corresponding to the given name.  

#### Parameters:  
- `name` (`str`): The name of the desired state.  

#### Returns:  
- The `State` with the specified name.  

#### Example:  
```python
state = State.from_name("accept")  # Returns State.accept
```

---

### `get_from_value(cls, v)`  
(Deprecated - Use `from_value` instead)  
Returns the `State` corresponding to the given value.  

---

### `get_next(self)`  
Returns the next state in the sequence based on the current state.  

#### Returns:  
- The next `State` in sequence, or `None` if there is no next state.  

#### Example:  
```python
current_state = State.vote
next_state = current_state.get_next()  # Returns State.accept
```

---

### `is_next(self, state)`  
Checks if the given state is the next state in sequence.  

#### Parameters:  
- `state` (`State`): The state to compare.  

#### Returns:  
- `True` if the given state is the next state, `False` otherwise.  

#### Example:  
```python
current_state = State.vote
is_next = current_state.is_next(State.accept)  # Returns True
```

---

### Comparison Methods  

The `State` class supports comparison operators to determine the order of states:  

1. `__gt__(self, state)`: Checks if the current state is greater than the given state.  
2. `__lt__(self, state)`: Checks if the current state is less than the given state.  
3. `__ge__(self, state)`: Checks if the current state is greater than or equal to the given state.  
4. `__le__(self, state)`: Checks if the current state is less than or equal to the given state.  
5. `__eq__(self, state)`: Checks if the current state is equal to the given state.  

#### Examples:  
```python
state1 = State.init
state2 = State.vote

print(state1 < state2)  # True
print(state2 > state1)  # True
print(state1 == State.init)  # True
```

---

## Use Cases  

1. **State Management**  
   Use the `State` class to track the current state of a process or transaction in the simulator.  
   ```python
   current_state = State.init
   next_state = current_state.get_next()
   ```

2. **State Comparisons**  
   Compare states to enforce order or define transitions.  
   ```python
   if current_state < State.confirm:
       print("State has not reached confirmation.")
   ```

3. **Dynamic State Retrieval**  
   Retrieve states dynamically by their value or name.  
   ```python
   state = State.from_value(3)  # State.accept
   state_by_name = State.from_name("confirm")
   ```

---

## Key Features  

- **Ordered States**: States have an intrinsic order, allowing comparisons and transitions.  
- **Utility Methods**: Provides methods to retrieve states dynamically and navigate between them.  
- **Enumeration**: Ensures well-defined, immutable states for consistent usage across the simulator.  
