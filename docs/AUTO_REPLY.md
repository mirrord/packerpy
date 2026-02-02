# Automatic Reply Feature

The Protocol class supports automatic replies, allowing you to register response handlers that automatically send reply messages when specific conditions are met. This is useful for implementing request-response patterns, acknowledgments, and reactive message handling.

## Overview

The automatic reply feature enables you to:
- Register reply handlers that trigger based on incoming messages
- Define custom conditions for when replies should be sent
- Update reply messages dynamically based on incoming message content
- Handle multiple auto-replies for the same message type
- Manage and unregister reply handlers

## API Reference

### `register_auto_reply(condition_callback, reply_msg, send_callback, update_callback=None)`

Register an automatic reply that sends when a condition is met.

**Parameters:**
- `condition_callback` (Callable[[Message], bool]): Function that takes an incoming message and returns True if the reply should be sent
- `reply_msg` (Message): Message instance to send as reply
- `send_callback` (Callable[[bytes], None]): Function that takes encoded bytes and sends them
- `update_callback` (Optional[Callable[[Message, Message], None]]): Optional function that updates the reply message before sending. Called with (incoming_msg, reply_msg) and should modify reply_msg in place based on incoming_msg

**Returns:**
- `int`: Reply ID that can be used to unregister the auto-reply

**Raises:**
- `ValueError`: If reply message is invalid

**Example:**
```python
from packerpy.protocols.protocol import Protocol, protocol
from packerpy.protocols.message import Message
from packerpy.protocols.message_partial import Encoding

MyProtocol = Protocol()

@protocol(MyProtocol)
class PingMessage(Message):
    encoding = Encoding.BIG_ENDIAN
    fields = {"seq": {"type": "int(32)"}}

@protocol(MyProtocol)
class PongMessage(Message):
    encoding = Encoding.BIG_ENDIAN
    fields = {"seq": {"type": "int(32)"}}

# Create reply template
pong = PongMessage(seq=0)

# Define condition
def is_ping(msg):
    return isinstance(msg, PingMessage)

# Define send callback
def send_func(data: bytes):
    socket.sendall(data)

# Define update callback to copy sequence number
def update_pong(ping, pong):
    pong.seq = ping.seq

# Register auto-reply
reply_id = MyProtocol.register_auto_reply(
    is_ping, pong, send_func, update_pong
)

# Later, when receiving messages
incoming = MyProtocol.decode(received_data)
if incoming:
    MyProtocol.check_auto_replies(incoming)
```

### `check_auto_replies(incoming_msg)`

Check all registered auto-replies against an incoming message.

For each registered auto-reply, if the condition callback returns True, the reply message is sent.

**Parameters:**
- `incoming_msg` (Message): The incoming message to check against

**Returns:**
- `int`: Number of replies that were sent

**Example:**
```python
# After receiving and decoding a message
incoming = MyProtocol.decode(received_data)
if incoming:
    num_replies = MyProtocol.check_auto_replies(incoming)
    print(f"Sent {num_replies} auto-replies")
```

### `unregister_auto_reply(reply_id)`

Unregister an automatic reply.

**Parameters:**
- `reply_id` (int): The ID returned by `register_auto_reply()`

**Returns:**
- `bool`: True if reply was unregistered, False if reply_id not found

**Example:**
```python
if MyProtocol.unregister_auto_reply(reply_id):
    print("Auto-reply unregistered")
else:
    print("Reply ID not found")
```

### `unregister_all_auto_replies()`

Unregister all automatic replies.

**Example:**
```python
MyProtocol.unregister_all_auto_replies()
```

### `get_auto_replies()`

Get information about currently registered auto-replies.

**Returns:**
- `Dict[int, Dict[str, Any]]`: Dictionary mapping reply IDs to info dicts containing:
  - `reply_msg`: The Message instance that will be sent

**Example:**
```python
auto_replies = MyProtocol.get_auto_replies()
for reply_id, info in auto_replies.items():
    print(f"ID {reply_id}: {info['reply_msg'].__class__.__name__}")
```

## Usage Examples

### Simple Ping-Pong

```python
from packerpy.protocols.protocol import Protocol, protocol
from packerpy.protocols.message import Message
from packerpy.protocols.message_partial import Encoding

MyProtocol = Protocol()

@protocol(MyProtocol)
class PingMessage(Message):
    encoding = Encoding.BIG_ENDIAN
    fields = {"seq": {"type": "int(32)"}}

@protocol(MyProtocol)
class PongMessage(Message):
    encoding = Encoding.BIG_ENDIAN
    fields = {"seq": {"type": "int(32)"}}

# Create pong template
pong = PongMessage(seq=0)

def send_callback(data):
    # Send the reply
    transport.send(data)

# Update callback copies sequence from ping to pong
def update_pong(ping, pong):
    pong.seq = ping.seq

# Register auto-reply
MyProtocol.register_auto_reply(
    condition_callback=lambda msg: isinstance(msg, PingMessage),
    reply_msg=pong,
    send_callback=send_callback,
    update_callback=update_pong
)

# Process incoming messages
while True:
    data = transport.receive()
    incoming = MyProtocol.decode(data)
    if incoming:
        MyProtocol.check_auto_replies(incoming)
```

### Command Acknowledgment

```python
from packerpy.protocols.protocol import Protocol, protocol
from packerpy.protocols.message import Message
from packerpy.protocols.message_partial import Encoding

MyProtocol = Protocol()

@protocol(MyProtocol)
class CommandMessage(Message):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "cmd_id": {"type": "int(32)"},
        "command": {"type": "int(32)"}
    }

@protocol(MyProtocol)
class AckMessage(Message):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "cmd_id": {"type": "int(32)"},
        "status": {"type": "int(32)"}
    }

ack = AckMessage(cmd_id=0, status=0)

def send_ack(data):
    transport.send(data)

# Set status based on command validity
def update_ack(cmd, ack):
    ack.cmd_id = cmd.cmd_id
    if 1 <= cmd.command <= 100:
        ack.status = 200  # OK
    else:
        ack.status = 400  # Invalid

MyProtocol.register_auto_reply(
    lambda msg: isinstance(msg, CommandMessage),
    ack,
    send_ack,
    update_ack
)
```

### Conditional Reply Based on Content

```python
from packerpy.protocols.protocol import Protocol, protocol
from packerpy.protocols.message import Message
from packerpy.protocols.message_partial import Encoding

MyProtocol = Protocol()

@protocol(MyProtocol)
class RequestMessage(Message):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "req_id": {"type": "int(32)"},
        "priority": {"type": "int(32)"}
    }

@protocol(MyProtocol)
class ResponseMessage(Message):
    encoding = Encoding.BIG_ENDIAN
    fields = {"req_id": {"type": "int(32)"}}

response = ResponseMessage(req_id=0)

# Only reply to high-priority requests (priority > 5)
def is_high_priority(msg):
    return isinstance(msg, RequestMessage) and msg.priority > 5

def update_response(request, response):
    response.req_id = request.req_id

MyProtocol.register_auto_reply(
    is_high_priority,
    response,
    lambda data: transport.send(data),
    update_response
)
```

### Data Query with Computed Response

```python
from packerpy.protocols.protocol import Protocol, protocol
from packerpy.protocols.message import Message
from packerpy.protocols.message_partial import Encoding

MyProtocol = Protocol()

@protocol(MyProtocol)
class QueryMessage(Message):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "query_id": {"type": "int(32)"},
        "value": {"type": "int(32)"}
    }

@protocol(MyProtocol)
class ResultMessage(Message):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "query_id": {"type": "int(32)"},
        "result": {"type": "int(32)"}
    }

result = ResultMessage(query_id=0, result=0)

def send_result(data):
    transport.send(data)

# Compute result based on incoming query value
def compute_result(query, result):
    result.query_id = query.query_id
    result.result = query.value * 2  # Example computation

MyProtocol.register_auto_reply(
    lambda msg: isinstance(msg, QueryMessage),
    result,
    send_result,
    compute_result
)
```

### Multiple Auto-Replies for Same Message

```python
from packerpy.protocols.protocol import Protocol, protocol
from packerpy.protocols.message import Message
from packerpy.protocols.message_partial import Encoding

MyProtocol = Protocol()

@protocol(MyProtocol)
class EventMessage(Message):
    encoding = Encoding.BIG_ENDIAN
    fields = {"event_type": {"type": "int(32)"}}

# Multiple handlers for the same event

# Handler 1: Log the event
def log_handler(data):
    print(f"Event logged: {len(data)} bytes")

# Handler 2: Send notification
def notify_handler(data):
    notification_service.send(data)

# Handler 3: Update metrics
def metrics_handler(data):
    metrics.increment("events_received")

dummy_msg = EventMessage(event_type=0)

# Register multiple auto-replies
MyProtocol.register_auto_reply(
    lambda msg: isinstance(msg, EventMessage),
    dummy_msg, log_handler
)
MyProtocol.register_auto_reply(
    lambda msg: isinstance(msg, EventMessage),
    dummy_msg, notify_handler
)
MyProtocol.register_auto_reply(
    lambda msg: isinstance(msg, EventMessage),
    dummy_msg, metrics_handler
)

# All three handlers will be called for each EventMessage
```

## Implementation Details

### Thread Safety

The auto-reply implementation is thread-safe. Multiple threads can register, unregister, and check auto-replies concurrently without issues. All operations use internal locking to protect shared state.

### Execution Model

When `check_auto_replies()` is called:
1. A snapshot of all registered auto-replies is taken
2. For each auto-reply:
   - The condition callback is invoked with the incoming message
   - If it returns True:
     - The update callback (if provided) is called to modify the reply message
     - The reply message is encoded
     - The send callback is invoked with the encoded bytes
3. The number of replies sent is returned

### Message Updates

When an `update_callback` is provided:
- The callback receives both the incoming message and the reply message
- It can read data from the incoming message and modify the reply message
- The reply message is re-encoded after each update
- This allows dynamic replies based on request content

When no `update_callback` is provided:
- The reply message is sent as-is
- More efficient for static replies

### Error Handling

If a condition callback raises an exception:
- The error is printed to stdout
- That auto-reply is skipped
- Other auto-replies continue to be checked

If an update callback raises an exception:
- The error is printed to stdout
- That reply is not sent
- Other auto-replies continue to be checked

If a send callback raises an exception:
- The error is printed to stdout
- That reply is considered not sent
- Other auto-replies continue to be checked

### Performance Considerations

- Condition callbacks should be fast, as they're checked for every incoming message
- Update callbacks should avoid heavy computation
- Multiple auto-replies for the same message are all processed
- Auto-replies are checked synchronously - consider the impact on message processing latency

## Best Practices

1. **Keep condition callbacks simple**: They're evaluated for every incoming message. Use simple type checks and basic field comparisons.

2. **Use type checking first**: Start your condition with `isinstance(msg, TargetType)` to avoid attribute errors on different message types.

3. **Handle edge cases in update callbacks**: The incoming message might have unexpected values. Validate data before using it.

4. **Avoid blocking in callbacks**: Send callbacks should be non-blocking or very fast. For async operations, consider queuing the send.

5. **Clean up when done**: Unregister auto-replies when they're no longer needed to avoid unnecessary processing.

6. **Use multiple specific auto-replies**: Instead of one complex condition callback, register multiple simple ones for clarity.

7. **Test exception handling**: Ensure your callbacks handle errors gracefully.

8. **Document conditions**: Complex condition logic should be well-commented.

## Comparison with Message Scheduling

| Feature | Message Scheduling | Automatic Replies |
|---------|-------------------|-------------------|
| Trigger | Time-based (intervals) | Event-based (incoming messages) |
| Send timing | Periodic | On demand |
| Update callback | Takes message only | Takes both incoming and reply |
| Use case | Heartbeats, monitoring | Request-response, acknowledgments |
| Lifecycle | Start/stop scheduling | Register/unregister handlers |

## Testing

The feature includes comprehensive tests covering:
- Basic registration and unregistration
- Condition evaluation
- Multiple auto-replies
- Update callbacks with various patterns
- Exception handling in all callbacks
- Content-based conditions
- Different message types

Run tests with:
```bash
pytest tests/unit/test_auto_reply.py -v
```

## Demo

A complete working demo is available at `examples/auto_reply_demo.py`:

```bash
python examples/auto_reply_demo.py
```

This demo shows:
- Simple ping-pong auto-reply
- Command acknowledgment with status codes
- Conditional replies based on message content
- Data queries with computed responses
- Multiple auto-replies for the same message
