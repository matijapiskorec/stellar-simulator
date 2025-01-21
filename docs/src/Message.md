# `Message` Class Documentation  

## Overview  

The `Message` class is a base class designed for representing messages in the Stellar Consensus Protocol (SCP) simulation. It provides fundamental properties such as a unique message ID and a broadcast status. Subclasses, such as `SCPNominate` and `SCPPrepare`, inherit from this class to define specific message types.  

---

## Constructor  

### `__new__(cls, **kwargs)`  

Creates a new `Message` instance, generating a unique message ID and initializing the broadcast status.  

#### Parameters:  
- **`broadcasted`** (`bool`, optional): Indicates whether the message has been broadcasted. Defaults to `False`.  

#### Behavior:  
- Generates a unique message ID of length `UUID_LENGTH` (default is `10`).  
- Sets the `broadcasted` status based on the input or defaults to `False`.  

#### Example:  
```python
message = Message(broadcasted=True)
logger.log(message.message_id)  # Example Output: '123abc456d'
```

---

## Properties  

### `message_id`  
- **Description**: Returns the unique ID of the message.  
- **Type**: `str`  

#### Example:  
```python
logger.log(message.message_id)  # Output: Unique message ID (e.g., '123abc456d')
```

---

### `broadcasted`  
- **Description**: Indicates whether the message has been broadcasted.  
- **Type**: `bool`  

#### Example:  
```python
logger.log(message.broadcasted)  # Output: True or False
```

---

## Methods  

### `__repr__(self)`  
Returns a string representation of the message, including its type and data.  

#### Returns:  
- A string representation of the message.  

#### Example:  
```python
logger.log(message)  
# Output: [Message message, data = {'_message_id': '123abc456d', '_broadcasted': False}]
```

---

### `__eq__(self, other)`  
Checks equality between two `Message` instances based on their unique message IDs.  

#### Parameters:  
- **`other`** (`Message`): The message to compare with.  

#### Returns:  
- `True` if the message IDs are the same, `False` otherwise.  

#### Example:  
```python
message1 = Message()
message2 = Message()
logger.log(message1 == message2)  # Output: False (different IDs)
```

---

## Use Cases  

1. **Base Class for SCP Messages**  
   Use the `Message` class as a foundation for specific SCP message types like `SCPNominate` or `SCPPrepare`.  
   ```python
   class SCPNominate(Message):
       pass
   nominate_message = SCPNominate()
   ```

2. **Unique Message Identification**  
   Leverage the `message_id` property to uniquely identify and compare messages.  
   ```python
   if message1.message_id == message2.message_id:
       logger.log("Messages are the same.")
   ```

3. **Tracking Broadcast Status**  
   Use the `broadcasted` property to determine whether a message has been broadcasted in the simulation.  
   ```python
   if not message.broadcasted:
       logger.log("Message has not been broadcasted yet.")
   ```

---

## Key Features  

- **Unique Identification**: Each message is assigned a unique ID for easy tracking and comparison.  
- **Broadcast Status**: Tracks whether the message has been broadcasted.  
- **Reusable Design**: Serves as a base class for all SCP-related messages, allowing consistent behavior across message types.  

---

## TODO:

1. **Serialization**: Add methods for serializing and deserializing messages for network communication.  
2. **Validation**: Implement validation mechanisms to ensure the integrity of message properties.  
3. **Broadcast Management**: Enhance the `broadcasted` property to include timestamps or broadcast metadata.  
