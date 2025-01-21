# `Mempool` Class Documentation  

## Overview  

The `Mempool` class serves as a proxy for incoming transactions, acting as an intermediary between transaction generation and node processing in the Stellar Consensus Protocol (SCP) simulation. Nodes retrieve and validate transactions from the mempool during the consensus process.  

---

## Constructor  

### `__init__(self)`  

Initializes the `Mempool` instance.  

#### Behavior:  
- Creates empty lists for storing transactions and messages.  
- Automatically mines 5 transactions into the mempool for quicker initialization of the simulation.  
- Logs the initialization of the mempool.  

#### Example:  
```python
mempool = Mempool()
```

---

## Methods  

### `mine(self)`  

Creates a new transaction and adds it to the mempool.  

#### Returns:  
- **`Transaction`**: The newly mined transaction.  

#### Behavior:  
- Generates a `Transaction` object with the current simulation time.  
- Logs the creation and addition of the transaction to the mempool.  

#### Example:  
```python
transaction = mempool.mine()
print(transaction)
```

---

### `get_transaction(self)`  

Retrieves a random transaction from the mempool without removing it.  

#### Returns:  
- **`Transaction`**: A randomly selected transaction from the mempool, or `None` if the mempool is empty.  

#### Behavior:  
- Chooses a random transaction from the list of transactions.  
- Logs the retrieval of the transaction or logs if no transactions are available.  

#### Example:  
```python
transaction = mempool.get_transaction()
if transaction:
    print(f"Transaction retrieved: {transaction}")
else:
    print("No transactions in the mempool.")
```

---

## Attributes  

### `transactions`  
- **Description**: A list of transactions currently in the mempool.  
- **Type**: `list[Transaction]`  

### `messages`  
- **Description**: A list of messages stored in the mempool (currently not used).  
- **Type**: `list`  

---

## Logging  

- **Initialization**: Logs when the mempool is initialized.  
- **Mining**: Logs when a transaction is mined and added to the mempool.  
- **Retrieval**: Logs when a transaction is retrieved from the mempool or if the mempool is empty.  

#### Example Log Output:  
```
INFO: Initialized mempool!
INFO: Transaction [Transaction a1b2c3 time = 1672534567.1234] mined to the mempool!
INFO: Transaction [Transaction a1b2c3 time = 1672534567.1234] retrieved from the mempool!
```

---

## Use Cases  

1. **Transaction Mining**  
   Generate new transactions and add them to the mempool for use by nodes.  
   ```python
   mempool.mine()
   ```

2. **Transaction Retrieval**  
   Retrieve transactions for processing by nodes during the consensus process.  
   ```python
   transaction = mempool.get_transaction()
   ```

3. **Simulation Initialization**  
   Automatically populate the mempool with transactions at the start of the simulation.  

---

## Key Features  

- **Transaction Generation**: Automatically mines transactions into the mempool.  
- **Random Retrieval**: Supports random selection of transactions for simulation flexibility.  
- **Integration with Simulation**: Designed to work seamlessly with nodes and the consensus process.  
