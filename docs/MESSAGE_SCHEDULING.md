# Message Scheduling Feature

The Protocol class supports automatic message scheduling, allowing you to send messages at regular intervals without manually managing timers or loops. It also supports dynamic message updates before each send.

## Overview

The message scheduling feature enables you to:
- Schedule messages to be sent automatically at defined intervals
- Update message content dynamically before each send (e.g., timestamps, counters)
- Manage multiple scheduled messages simultaneously
- Cancel individual or all scheduled messages
- Handle callback exceptions gracefully

## API Reference

### `schedule_message(msg, interval, send_callback, update_callback=None)`

Schedule a message to be sent automatically at regular intervals.

**Parameters:**
- `msg` (Message): The message instance to send periodically
- `interval` (float): Time interval in seconds between sends (must be > 0)
- `send_callback` (Callable[[bytes], None]): Function that takes encoded bytes and sends them
- `update_callback` (Optional[Callable[[Message], None]]): Optional function that updates the message before each send. Called with the message instance and should modify it in place

**Returns:**
- `int`: Schedule ID that can be used to cancel the scheduled message

**Raises:**
- `ValueError`: If interval is not positive or message is invalid

**Example:**
```python
from packerpy.protocols.protocol import Protocol, protocol
from packerpy.protocols.message import Message
from packerpy.protocols.message_partial import Encoding
import time

MyProtocol = Protocol()

@protocol(MyProtocol)
class HeartbeatMessage(Message):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "timestamp": {"type": "int(64)"},
        "sequence": {"type": "int(32)"}
    }

# Create message
heartbeat = HeartbeatMessage(timestamp=0, sequence=0)

# Define send callback
def send_func(data: bytes):
    socket.sendall(data)

# Define update callback to refresh timestamp and increment sequence
def update_heartbeat(msg):
    msg.timestamp = int(time.time() * 1000)
    msg.sequence += 1

# Schedule the message with updates
schedule_id = MyProtocol.schedule_message(
    heartbeat, 1.0, send_func, update_heartbeat
)

# Or schedule without updates (static message)
schedule_id = MyProtocol.schedule_message(heartbeat, 1.0, send_func)
```

### `cancel_scheduled_message(schedule_id)`

Cancel a scheduled message.

**Parameters:**
- `schedule_id` (int): The ID returned by `schedule_message()`

**Returns:**
- `bool`: True if message was cancelled, False if schedule_id not found

**Example:**
```python
# Cancel the scheduled message
if MyProtocol.cancel_scheduled_message(schedule_id):
    print("Message scheduling cancelled")
else:
    print("Schedule ID not found")
```

### `cancel_all_scheduled_messages()`

Cancel all scheduled messages at once.

**Example:**
```python
# Stop all scheduled messages
MyProtocol.cancel_all_scheduled_messages()
```

### `get_scheduled_messages()`

Get information about currently scheduled messages.

**Returns:**
- `Dict[int, Dict[str, Any]]`: Dictionary mapping schedule IDs to info dicts containing:
  - `message`: The Message instance
  - `interval`: The send interval in seconds

**Example:**
```python
scheduled = MyProtocol.get_scheduled_messages()
for schedule_id, info in scheduled.items():
    print(f"ID {schedule_id}: {info['message'].__class__.__name__} every {info['interval']}s")
```

## Usage Examples

### Basic Static Message

```python
import time
from packerpy.protocols.protocol import Protocol, protocol
from packerpy.protocols.message import Message
from packerpy.protocols.message_partial import Encoding

MyProtocol = Protocol()

@protocol(MyProtocol)
class Heartbeat(Message):
    encoding = Encoding.BIG_ENDIAN
    fields = {"timestamp": {"type": "int(64)"}}

# Create message
heartbeat = Heartbeat(timestamp=int(time.time()))

# Schedule it (no update callback - message stays static)
def send_callback(data):
    print(f"Sending heartbeat: {len(data)} bytes")

schedule_id = MyProtocol.schedule_message(heartbeat, 1.0, send_callback)

# Let it run for 5 seconds
time.sleep(5)

# Cancel it
MyProtocol.cancel_scheduled_message(schedule_id)
```

### Dynamic Message with Timestamp Updates

```python
import time
from packerpy.protocols.protocol import Protocol, protocol
from packerpy.protocols.message import Message
from packerpy.protocols.message_partial import Encoding

MyProtocol = Protocol()

@protocol(MyProtocol)
class Heartbeat(Message):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "timestamp": {"type": "int(64)"},
        "sequence": {"type": "int(32)"}
    }

# Create message
heartbeat = Heartbeat(timestamp=0, sequence=0)

def send_callback(data):
    decoded = MyProtocol.decode(data)
    print(f"Sent seq={decoded.sequence}, ts={decoded.timestamp}")

# Update callback refreshes timestamp and increments sequence
def update_heartbeat(msg):
    msg.timestamp = int(time.time() * 1000)
    msg.sequence += 1

schedule_id = MyProtocol.schedule_message(
    heartbeat, 1.0, send_callback, update_heartbeat
)

time.sleep(5)
MyProtocol.cancel_scheduled_message(schedule_id)
print(f"Final sequence: {heartbeat.sequence}")
```

### Counter with Compound Logic

```python
from packerpy.protocols.protocol import Protocol, protocol
from packerpy.protocols.message import Message
from packerpy.protocols.message_partial import Encoding

MyProtocol = Protocol()

@protocol(MyProtocol)
class StatusUpdate(Message):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "counter": {"type": "int(32)"},
        "value": {"type": "int(32)"}
    }

status = StatusUpdate(counter=0, value=100)

def send_callback(data):
    decoded = MyProtocol.decode(data)
    print(f"Counter: {decoded.counter}, Value: {decoded.value}")

# Complex update logic
def update_status(msg):
    msg.counter += 1
    msg.value = 100 + (msg.counter * 10)  # Value grows with counter

schedule_id = MyProtocol.schedule_message(
    status, 0.5, send_callback, update_status
)
```

### Multiple Scheduled Messages

```python
from packerpy.protocols.protocol import Protocol, protocol
from packerpy.protocols.message import Message
from packerpy.protocols.message_partial import Encoding

MyProtocol = Protocol()

@protocol(MyProtocol)
class StatusUpdate(Message):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "cpu": {"type": "float"},
        "memory": {"type": "float"}
    }

@protocol(MyProtocol)
class KeepAlive(Message):
    encoding = Encoding.BIG_ENDIAN
    fields = {"seq": {"type": "int(32)"}}

def send_callback(data):
    # Send via socket, transport, etc.
    pass

# Schedule multiple messages with different intervals
status_id = MyProtocol.schedule_message(
    StatusUpdate(cpu=25.0, memory=60.0), 
    interval=5.0,  # Every 5 seconds
    send_callback=send_callback
)

keepalive_id = MyProtocol.schedule_message(
    KeepAlive(seq=1),
    interval=1.0,  # Every 1 second
    send_callback=send_callback
)

# Later, cancel individual messages
MyProtocol.cancel_scheduled_message(status_id)

# Or cancel all at once
MyProtocol.cancel_all_scheduled_messages()
```

### Integration with TCP Client

```python
import asyncio
from packerpy.protocols.protocol import Protocol, protocol
from packerpy.protocols.message import Message
from packerpy.protocols.message_partial import Encoding
from packerpy.transports.tcp.async_client import AsyncTCPClient

MyProtocol = Protocol()

@protocol(MyProtocol)
class Ping(Message):
    encoding = Encoding.BIG_ENDIAN
    fields = {"timestamp": {"type": "int(64)"}}

async def main():
    # Connect to server
    client = AsyncTCPClient("localhost", 8080)
    await client.connect()
    
    # Define callback that sends via the client
    def send_ping(data: bytes):
        # Note: This runs in a background thread, so we can't use await
        # For async send, consider using asyncio.run_coroutine_threadsafe
        try:
            asyncio.create_task(client.send(data))
        except Exception as e:
            print(f"Send error: {e}")
    
    # Schedule ping every 2 seconds
    ping = Ping(timestamp=0)
    schedule_id = MyProtocol.schedule_message(ping, 2.0, send_ping)
    
    # Run for a while
    await asyncio.sleep(10)
    
    # Cleanup
    MyProtocol.cancel_scheduled_message(schedule_id)
    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
```

## Implementation Details

### Thread Safety

The scheduling implementation is thread-safe. Multiple threads can schedule, cancel, and query scheduled messages concurrently without issues. All operations use internal locking to protect shared state.

### Background Execution

Scheduled messages run in daemon threads. Each scheduled message gets its own thread that:
1. Calls the update callback (if provided) to modify the message
2. Encodes the message
3. Calls the send callback with the encoded bytes
4. Handles exceptions gracefully (prints errors but continues)
5. Waits for the specified interval
6. Repeats until cancelled or the program exits

### Message Updates

When an `update_callback` is provided:
- The callback is invoked **before each send**
- The callback receives the message instance and should modify it in place
- The message is re-encoded after each update
- This allows for dynamic content like timestamps, counters, or calculated values

When no `update_callback` is provided:
- The message is encoded once before the first send
- The same encoded bytes are sent each time (more efficient for static messages)

### Error Handling

If a send callback raises an exception:
- The error is printed to stdout
- The scheduler continues running and will try again at the next interval
- The exception does not crash the scheduler thread

If an update callback raises an exception:
- The error is printed to stdout
- The message is **not** sent for that iteration
- The scheduler continues and will try again at the next interval

### Resource Cleanup

When cancelling a scheduled message:
- The thread is signaled to stop
- A 1-second timeout is used to wait for thread completion
- Resources are cleaned up automatically

When your program exits:
- Daemon threads are automatically terminated
- No explicit cleanup is required (but calling `cancel_all_scheduled_messages()` is good practice)

## Best Practices

1. **Use update callbacks for dynamic content**: When messages need changing data (timestamps, sequence numbers, counters), use the update callback rather than trying to manage this externally.

2. **Keep update callbacks fast**: The update callback runs in the scheduler thread. Avoid heavy computation or blocking operations.

3. **Validate messages before scheduling**: The system validates messages at schedule time, but it's good practice to check beforehand.

4. **Use reasonable intervals**: Very short intervals (< 0.01 seconds) may consume excessive resources, especially with update callbacks that require re-encoding.

5. **Handle callback exceptions**: Make your send and update callbacks robust and handle exceptions appropriately.

6. **Clean up on exit**: Call `cancel_all_scheduled_messages()` when shutting down for clean resource management.

7. **For async code**: Be careful when using async send methods in the callback, as callbacks run in background threads. Consider using `asyncio.run_coroutine_threadsafe()` or similar patterns.

8. **Static vs Dynamic**: If your message never changes, omit the update callback to avoid unnecessary re-encoding on each send.

## Testing

The feature includes comprehensive tests covering:
- Basic scheduling and cancellation
- Multiple scheduled messages
- Different intervals
- Thread safety
- Exception handling in send callbacks
- Exception handling in update callbacks
- Invalid inputs
- Message updates with various patterns (counters, timestamps, compound logic)

Run tests with:
```bash
pytest tests/unit/test_message_scheduling.py -v
```

## Demos

Two complete working demos are available:

### Basic Demo
`examples/message_scheduling_demo.py` - Shows basic scheduling without updates:
```bash
python examples/message_scheduling_demo.py
```

### Update Callback Demo
`examples/message_scheduling_with_updates_demo.py` - Demonstrates dynamic message updates:
```bash
python examples/message_scheduling_with_updates_demo.py
```

This demo shows:
- Timestamp and sequence updates
- Counter with compound logic
- Static messages (no updates)
- Multiple messages with different update patterns
