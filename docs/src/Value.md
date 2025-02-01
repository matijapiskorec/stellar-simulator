# `Value` Class Documentation

## Overview

The `Value` class represents a set of transactions and associated state information. It is designed to manage and combine transactions in a consistent and structured way. Each `Value` object is uniquely identified by a hash, calculated from its set of transactions.

### Key Features
- **Transaction Management**: Stores a set of `Transaction` objects, ensuring all entries are valid instances of the `Transaction` class.
- **State Association**: Tracks the current state of the `Value` using the `State` class.
- **Hashing and Equality**: Implements custom hashing and equality methods to enable consistent comparison and use in hash-based collections.
- **Combining Values**: Provides a utility method to merge multiple `Value` instances into a single `Value`.

---

## Constructor

### `__init__(self, **kwargs)`
Initializes a `Value` object.

#### Parameters:
- `transactions` (optional): A list of `Transaction` objects to initialize the value. Defaults to an empty list if not provided.
- `state` (optional): The state of the `Value` as defined by the `State` class. Defaults to `State.init`.

#### Exceptions:
- Asserts that all entries in the `transactions` list are instances of the `Transaction` class.

#### Example:
```python
from Transaction import Transaction
from State import State

tx1 = Transaction(...)
tx2 = Transaction(...)
value = Value(transactions=[tx1, tx2], state=State.valid)
```

---

## Properties

### `transactions`
- **Description**: Returns the list of transactions associated with the `Value`.
- **Type**: `list[Transaction]`

### `state`
- **Description**: Returns the current state of the `Value`.
- **Type**: `State`

### `hash`
- **Description**: Returns the hash of the `Value`, calculated from its transactions.
- **Type**: `int`

---

## Methods

### `__repr__(self)`
Returns a string representation of the `Value` object, including its hash, state, and transactions.

#### Example:
```python
print(value)
# Output: [Value, hash = 123456, state = State.valid, transactions = [tx1, tx2]]
```

---

### `__eq__(self, other)`
Checks equality between two `Value` objects. Two `Value` objects are considered equal if:
- Their hashes match.
- Their states are identical.
- Their transactions are identical.

#### Example:
```python
value1 = Value(transactions=[tx1, tx2], state=State.valid)
value2 = Value(transactions=[tx1, tx2], state=State.valid)
assert value1 == value2
```

---

### `__hash__(self)`
Returns the hash of the `Value` object, allowing it to be used in hash-based collections like dictionaries and sets.

#### Example:
```python
value_set = {value1, value2}
```

---

### `combine(cls, values)`
Class method to combine multiple `Value` instances into a single `Value`.

#### Parameters:
- `values` (`list[Value]`): A list of `Value` objects to combine.

#### Returns:
- `Value`: A new `Value` object containing the union of all transactions from the provided values.

#### Example:
```python
value1 = Value(transactions=[tx1], state=State.valid)
value2 = Value(transactions=[tx2], state=State.valid)
combined_value = Value.combine([value1, value2])
```

---

## Use Cases

1. **Creating a New Value**
   Use the `Value` class to group a set of transactions with a specific state.
   ```python
   value = Value(transactions=[tx1, tx2], state=State.valid)
   ```

2. **Combining Multiple Values**
   Merge the transactions of multiple `Value` instances into one.
   ```python
   combined_value = Value.combine([value1, value2, value3])
   ```

3. **Tracking Ledger States**
   Use the `Value` class in a simulation to maintain state information and transaction sets for each ledger.

4. **Hash-Based Operations**
   Use the `Value` objects in sets or as dictionary keys, leveraging the implemented hashing and equality methods.


WARNING: In case of practical usage, run tests in `Value_test.py`
