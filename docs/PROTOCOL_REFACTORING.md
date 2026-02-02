# Protocol Registry Refactoring

## Overview

The Protocol class has been refactored to support a message type registry system with decorator-based registration. This enables automatic type discrimination during message decoding.

## Key Changes

### 1. Protocol Registry

The `Protocol` class now maintains a registry of `Message` subclasses:

```python
protocol = Protocol()

# Register messages using the decorator
@protocol(protocol)
class MyMessage(Message):
    fields = {"value": {"type": "int(32)"}}
```

### 2. Automatic Type Discrimination

When decoding, the Protocol automatically instantiates the correct Message subclass:

```python
# Encoding includes type information
encoded = protocol.encode(msg)

# Decoding returns the correct subclass
decoded = protocol.decode(encoded)  # Returns MyMessage instance
```

### 3. Type Header

Messages are now serialized with a type header:
- 2 bytes: length of message type name (big-endian)
- N bytes: UTF-8 encoded message type name
- Remaining bytes: serialized message data

## API Changes

### New Methods

- `Protocol.register(message_class)` - Register a Message subclass
- `Protocol.encode(message)` - Encode with type header (preferred over encode_message)
- `Protocol.decode(data)` - Decode with automatic type detection (preferred over decode_message)

### New Decorator

- `@protocol(protocol_instance)` - Decorator to register Message classes

### Legacy Methods (Maintained for Compatibility)

- `Protocol.encode_message()` - Alias for `encode()`
- `Protocol.decode_message()` - Alias for `decode()`

### Removed Methods

- `Protocol.create_message()` - No longer needed; create Message instances directly

## Updated Client/Server

Both `Client` and `Server` now accept an optional `protocol` parameter:

```python
# Create shared protocol
MyProtocol = Protocol()

@protocol(MyProtocol)
class PingMessage(Message):
    fields = {...}

@protocol(MyProtocol)
class PongMessage(Message):
    fields = {...}

# Pass protocol to client and server
server = Server(host="0.0.0.0", port=8080, protocol=MyProtocol)
client = Client(host="127.0.0.1", port=8080, protocol=MyProtocol)
```

## Migration Guide

### Before

```python
protocol = Protocol()
msg = Message(...)
data = protocol.encode_message(msg)
decoded = protocol.decode_message(data)  # Returns generic Message
```

### After

```python
MyProtocol = Protocol()

@protocol(MyProtocol)
class MyMessage(Message):
    fields = {...}

msg = MyMessage(...)
data = MyProtocol.encode(msg)
decoded = MyProtocol.decode(data)  # Returns MyMessage instance
```

## Examples

See the following examples:
- `examples/protocol_registry_demo.py` - Basic protocol registry usage
- `examples/client_server_registry_demo.py` - Client/Server with protocol registry

## Benefits

1. **Type Safety**: Automatic instantiation of correct Message subclass
2. **Flexibility**: Multiple protocols can coexist independently  
3. **Extensibility**: Easy to add new message types via decorator
4. **Backward Compatibility**: Legacy methods still work
5. **Clear Contracts**: Protocol explicitly knows which messages it supports

## Testing

All existing tests have been updated. New tests cover:
- Message registration
- Decorator usage
- Type discrimination during decode
- Multiple protocol independence
- Legacy method compatibility

Run tests with:
```bash
python -m pytest tests/unit/test_protocol.py -v
```
