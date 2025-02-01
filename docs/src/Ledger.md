# `Ledger` Class Documentation  

## Overview  

The `Ledger` class represents the ledger for a node in the Stellar Consensus Protocol (SCP) simulation. It maintains a record of transactions that have been added and validated by the node. The ledger is crucial for tracking the state of transactions that have been accepted into the blockchain through the consensus process.

---

## Constructor  

### `__init__(self, node)`  

Initializes a `Ledger` instance associated with a specific node.

#### Parameters:  
- **`node`** (`Node`): The node to which this ledger belongs.

#### Behavior:  
- Initializes an empty list to store transactions.
- Associates the ledger with the given node.
- Logs the initialization of the ledger.

#### Example:  
```python
from Node import Node
from Ledger import Ledger

node = Node(name="Node1")
ledger = Ledger(node=node)
```

---

## Methods  

### `add(self, transaction)`  

Adds a transaction to the ledger if it is not already present.

#### Parameters:  
- **`transaction`** (`Transaction`): The transaction to add to the ledger.

#### Behavior:  
- Checks if the transaction is already in the ledger.
- If not, appends the transaction to the ledger's transaction list.
- Logs whether the transaction was added or if it already exists.

#### Example:  
```python
from Transaction import Transaction

transaction = Transaction()
ledger.add(transaction)
```

---

### `get_transaction(self)`  

Retrieves a random transaction from the ledger.

#### Returns:  
- **`Transaction`**: A randomly selected transaction from the ledger, or `None` if the ledger is empty.

#### Behavior:  
- Uses NumPy's `random.choice` to select a transaction.
- If the ledger is empty, returns `None`.

#### Example:  
```python
transaction = ledger.get_transaction()
if transaction:
    print(f"Retrieved transaction: {transaction}")
else:
    print("Ledger is empty.")
```

---

## Properties  

### `transactions`  

- **Description**: Returns the list of transactions in the ledger.
- **Type**: `list[Transaction]`

#### Note:  
Currently, the `transactions` property returns a reference to the internal transaction list. To prevent external modifications, consider returning a copy in future implementations.

#### Example:  
```python
all_transactions = ledger.transactions
```

---

## Logging  

- **Initialization**: Logs when the ledger is initialized for a node.
- **Transaction Addition**: Logs when a transaction is added or if it already exists in the ledger.

#### Example Log Output:  
```
INFO: Initialized ledger for node Node1!
INFO: Node Node1: transaction [Transaction a1b2c3 time = 1672534567.1234] added!
```

---

## Use Cases  

1. **Transaction Management for a Node**  
   Store and manage transactions that have been accepted by a node during the consensus process.
   ```python
   transaction = Transaction()
   ledger.add(transaction)
   ```

2. **Random Transaction Retrieval**  
   Retrieve a random transaction from the ledger for processing or analysis.
   ```python
   random_transaction = ledger.get_transaction()
   ```

3. **Ledger Inspection**  
   Access all transactions in the ledger to audit or display the node's transaction history.
   ```python
   for tx in ledger.transactions:
       print(tx)
   ```

---

## Key Features  

- **Association with Node**: Each ledger is linked to a specific node, ensuring clarity in transaction management.
- **Duplicate Prevention**: Ensures that duplicate transactions are not added to the ledger.
- **Logging**: Provides informative logs for key actions, aiding in debugging and tracking.

---

## Future Improvements  

1. **Transaction Validation**: Incorporate mechanisms to validate transactions before adding them to the ledger.
2. **Immutable Transactions**: Return copies of transactions to prevent external modification of the ledger's state.
3. **Persistence**: Implement functionality to persist the ledger's state between simulation runs or to external storage.
4. **Concurrency Handling**: If the simulation becomes multi-threaded, ensure thread-safe operations on the ledger.

---

## Examples  

### Adding and Retrieving Transactions  

```python
from Node import Node
from Ledger import Ledger
from Transaction import Transaction

# Initialize a node and its ledger
node = Node(name="Node1")
ledger = Ledger(node=node)

# Create and add transactions
tx1 = Transaction()
tx2 = Transaction()
ledger.add(tx1)
ledger.add(tx2)

# Attempt to add a duplicate transaction
ledger.add(tx1)  # Will log that the transaction already exists

# Retrieve a random transaction
random_tx = ledger.get_transaction()
print(f"Random Transaction: {random_tx}")
```
