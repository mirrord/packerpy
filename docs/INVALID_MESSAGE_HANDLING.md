# Invalid and Incomplete Message Handling

## Overview

The Protocol class now provides robust handling for invalid and incomplete messages that it receives during decoding. This feature is essential for real-world network communication where data may arrive in chunks or be corrupted.

## Features

### 1. Incomplete Message Buffering

When a message arrives in multiple chunks (common in network communication), the Protocol automatically buffers incomplete data until the full message can be decoded.

**How it works:**
- Protocol maintains a per-source buffer for incomplete data
- When `decode()` returns `None`, the data has been buffered
- Subsequent calls with more data automatically prepend the buffered data
- Buffers are cleared automatically after successful decode

**Example:**
```python
from packerpy.protocols import Protocol, Message, protocol

# Create protocol and register message types
MyProtocol = Protocol()

@protocol(MyProtocol)
class MyMessage(Message):
    fields = {"value": {"type": "int(32)"}}

# Simulate receiving data in chunks
msg = MyMessage(value=42)
complete_data = MyProtocol.encode(msg)

# First chunk - incomplete
chunk1 = complete_data[:10]
result = MyProtocol.decode(chunk1, source_id="client_1")
# result is None - buffered for later

# Second chunk - completes the message
chunk2 = complete_data[10:]
result = MyProtocol.decode(chunk2, source_id="client_1")
# result is (MyMessage(value=42), b"")
```

### 2. Invalid Message Wrapping

When a message fails to decode (unknown type, corrupted data, etc.), it's wrapped in an `InvalidMessage` object that preserves:
- The raw bytes that failed to decode
- The exception that occurred
- Any partial data that was successfully extracted (like message type)

**Example:**
```python
from packerpy.protocols import Protocol, InvalidMessage

# Try to decode invalid data
invalid_data = b"\x00\x07Unknown\x00\x00\x00\x01"
result = MyProtocol.decode(invalid_data, source_id="client_2")

if result:
    message, remaining = result
    if isinstance(message, InvalidMessage):
        print(f"Invalid message: {message.error}")
        print(f"Raw data: {message.raw_data}")
        print(f"Partial type: {message.partial_type}")
```

### 3. Source-Based Buffer Management

The Protocol tracks incomplete buffers per source ID, allowing it to handle multiple concurrent connections without buffer corruption.

**Example:**
```python
# Different sources maintain separate buffers
MyProtocol.decode(chunk1, source_id="client_A")  # Buffered
MyProtocol.decode(chunk1, source_id="client_B")  # Buffered separately

# Each source's buffer is independent
MyProtocol.decode(chunk2, source_id="client_A")  # Completes client_A's message
MyProtocol.decode(chunk2, source_id="client_B")  # Completes client_B's message
```

## API Reference

### Protocol.decode()

```python
def decode(
    self, data: bytes, source_id: str = "default"
) -> Optional[Tuple[Union[Message, InvalidMessage], bytes]]
```

**New behavior:**
- Returns `None` if message is incomplete (data has been buffered)
- Returns `(message, remaining_bytes)` tuple on success
- Returns `(InvalidMessage, remaining_bytes)` for invalid data
- The `source_id` parameter tracks buffers per connection/client

**Parameters:**
- `data`: Bytes to decode
- `source_id`: Identifier for the message source (default: "default")

**Returns:**
- `None`: Message is incomplete, buffered for later
- `(Message, bytes)`: Successfully decoded message and any remaining bytes
- `(InvalidMessage, bytes)`: Invalid message wrapped with error details

### InvalidMessage Class

```python
class InvalidMessage:
    raw_data: bytes          # Original bytes that failed to decode
    error: Exception         # Exception that occurred
    partial_type: Optional[str]  # Message type if extracted
    partial_data: Dict[str, Any]  # Any partial data decoded
```

**Example:**
```python
if isinstance(message, InvalidMessage):
    print(f"Error: {message.error}")
    print(f"Type: {message.partial_type}")
    print(f"Raw: {message.raw_data[:50]}...")  # First 50 bytes
```

### Buffer Management Methods

#### clear_incomplete_buffer()

```python
def clear_incomplete_buffer(self, source_id: str = "default") -> bool
```

Clear incomplete message buffer for a specific source.

**Returns:** `True` if buffer was cleared, `False` if none existed

#### clear_all_incomplete_buffers()

```python
def clear_all_incomplete_buffers(self) -> int
```

Clear all incomplete message buffers across all sources.

**Returns:** Number of buffers cleared

#### get_incomplete_buffer_size()

```python
def get_incomplete_buffer_size(self, source_id: str = "default") -> int
```

Get size of incomplete buffer for a specific source.

**Returns:** Number of bytes buffered, or 0 if no buffer exists

## Server and Client Integration

The `Server` and `Client` classes automatically handle incomplete and invalid messages:

### Server Behavior

```python
# Server automatically:
# 1. Uses client address as source_id for buffer tracking
# 2. Puts InvalidMessage objects in the receive queue
# 3. Clears buffers after successful decode
# 4. Clears buffers after receiving invalid messages

server = Server(host="0.0.0.0", port=8080, protocol=MyProtocol)

msg, addr = server.receive()
if isinstance(msg, InvalidMessage):
    print(f"Invalid from {addr}: {msg.error}")
```

### Client Behavior

```python
# Client automatically:
# 1. Uses "client" as source_id
# 2. Puts InvalidMessage objects in the receive queue
# 3. Handles incomplete messages transparently

client = Client(host="localhost", port=8080, protocol=MyProtocol)

msg = client.receive()
if isinstance(msg, InvalidMessage):
    print(f"Invalid message: {msg.error}")
```

## Use Cases

### 1. Network Communication

Handle TCP packets that may arrive in multiple chunks:

```python
# Protocol automatically assembles fragmented messages
result = protocol.decode(tcp_chunk, source_id=client_addr)
if result is None:
    # Waiting for more data - normal for network I/O
    continue
message, remaining = result
```

### 2. Error Logging

Log and analyze invalid messages without crashing:

```python
result = protocol.decode(data, source_id=source)
if result:
    message, _ = result
    if isinstance(message, InvalidMessage):
        logger.error(f"Invalid message from {source}")
        logger.debug(f"Raw: {message.raw_data.hex()}")
        logger.debug(f"Error: {message.error}")
```

### 3. Protocol Debugging

Inspect problematic messages during development:

```python
if isinstance(message, InvalidMessage):
    print(f"Message type (if extracted): {message.partial_type}")
    print(f"First 100 bytes: {message.raw_data[:100].hex()}")
    print(f"Error details: {message.error}")
    # Can save to file for analysis
    with open("invalid_msg.bin", "wb") as f:
        f.write(message.raw_data)
```

### 4. Multi-Connection Servers

Handle multiple clients with independent buffers:

```python
def handle_client(data, address):
    source_id = f"{address[0]}:{address[1]}"
    result = protocol.decode(data, source_id=source_id)
    
    if result is None:
        return None  # Waiting for more data
    
    message, _ = result
    if isinstance(message, InvalidMessage):
        # Clear buffer to prevent corruption from bad data
        protocol.clear_incomplete_buffer(source_id)
        return None
    
    # Process valid message
    return process_message(message)
```

## Migration Guide

### Old Code (Before)

```python
# Old API - returned just the message or None
decoded = protocol.decode(data)
if decoded:
    process_message(decoded)
```

### New Code (After)

```python
# New API - returns tuple or None
result = protocol.decode(data, source_id="client")
if result:
    message, remaining = result
    if isinstance(message, InvalidMessage):
        handle_invalid(message)
    else:
        process_message(message)
```

### Using Legacy API

The `decode_message()` method still works for backward compatibility:

```python
# Legacy method - returns just message (no remaining bytes)
decoded = protocol.decode_message(data)
if decoded:
    if isinstance(decoded, InvalidMessage):
        handle_invalid(decoded)
    else:
        process_message(decoded)
```

## Best Practices

1. **Always check for InvalidMessage** when receiving messages:
   ```python
   result = protocol.decode(data, source_id)
   if result:
       msg, _ = result
       if isinstance(msg, InvalidMessage):
           # Handle error
   ```

2. **Use unique source_ids** for each connection to prevent buffer mixing:
   ```python
   source_id = f"{client_ip}:{client_port}"
   ```

3. **Clear buffers on connection close** to free memory:
   ```python
   def on_disconnect(client_id):
       protocol.clear_incomplete_buffer(client_id)
   ```

4. **Set buffer size limits** for security (prevent memory exhaustion):
   ```python
   MAX_BUFFER_SIZE = 1024 * 1024  # 1MB
   
   if protocol.get_incomplete_buffer_size(source_id) > MAX_BUFFER_SIZE:
       protocol.clear_incomplete_buffer(source_id)
       raise ValueError("Buffer overflow - possible DoS attack")
   ```

5. **Handle remaining bytes** when multiple messages are in one buffer:
   ```python
   data = received_bytes
   while data:
       result = protocol.decode(data, source_id)
       if result is None:
           break  # Incomplete - wait for more
       message, data = result  # data is now the remaining bytes
       process_message(message)
   ```

## Testing

See `tests/unit/test_invalid_messages.py` for comprehensive test examples.

Run the demo:
```bash
python examples/invalid_incomplete_messages_demo.py
```

## Performance Considerations

- **Memory**: Buffers are stored per source. Clear buffers for inactive connections.
- **Thread Safety**: Buffer operations are thread-safe (use internal locks).
- **Overhead**: Minimal - only activated when incomplete data is received.

## Troubleshooting

**Problem:** Buffers grow indefinitely

**Solution:** Implement buffer size limits and clear stale buffers:
```python
# Clear buffers older than timeout
for source_id in get_active_sources():
    if time.time() - last_activity[source_id] > TIMEOUT:
        protocol.clear_incomplete_buffer(source_id)
```

**Problem:** Getting InvalidMessage for valid data

**Solution:** Check that both sides use the same Protocol with same registered message types:
```python
# Both sides must register the same messages
@protocol(MyProtocol)
class MyMessage(Message):
    ...
```

**Problem:** Messages not being reassembled

**Solution:** Ensure you use consistent source_id for the same connection:
```python
# Use same source_id for all chunks from same source
source_id = f"{addr[0]}:{addr[1]}"  # Keep consistent
```
