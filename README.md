# packerpy

A rapid protocol prototyping library that provides convenient message specification syntax and server/client interfaces.

## Architecture: Network Communications

Structured template for implementing network communication protocols over TCP/UDP with sync/async support.

## Configuration

- **Protocol:** TCP
- **Async Mode:** Enabled (asyncio)
- **Default Port:** 8080

## Features

- **High-Level API:** Simple `Server` and `Client` classes exposed at module level
- **Message Abstraction:** Work with `Message` objects instead of raw bytes
- **Protocol Implementation:** Built-in Protocol class handles encoding/decoding
- **Field References:** Declarative field definitions with automatic length prefixes, conditional fields, and computed values
- **JSON Serializer:** Human-readable JSON serialization for debugging and APIs
- **Mixed Serialization:** Use different serializers (binary/JSON) for different fields in the same message
- **Transport Layer:** Low-level TCP/UDP transports for custom implementations
- **Flexible Configuration:** Sync/async support based on configuration
- **Clean Architecture:** Separation of concerns between protocol and transport

## Installation

```bash
uv sync
```

## Project Structure

```
extidd_py/
├── server.py          # High-level Server implementation
├── client.py          # High-level Client implementation
├── protocols/         # Protocol and Message definitions
│   ├── message.py    # Message abstraction
│   ├── protocol.py   # Protocol implementation
│   └── base.py       # Legacy base protocol interface
├── transports/        # Transport layer implementations
│   ├── tcp/          # TCP client and server (sync/async)
│   └── udp/          # UDP sockets (sync/async)
├── handlers/         # Message handlers
├── serialization/    # Data serialization
└── config/           # Configuration management
```

## Quick Start - High-Level API (Recommended)

The easiest way to use this package is through the high-level `Server` and `Client` classes:

### Server

```python
import asyncio
from extidd_py import Server
from extidd_py.protocols.message import Message


def handle_message(message: Message, address) -> Message:
    """Handle incoming messages."""
    print(f"Received: {message}")
    return Message(
        message_type="response",
        payload={"status": "ok"},
        message_id=message.message_id
    )


async def main():
    server = Server(
        host="127.0.0.1",
        port=8080,
        message_handler=handle_message
    )
    await server.start()


if __name__ == "__main__":
    asyncio.run(main())
```

### Client

```python
import asyncio
from extidd_py import Client
from extidd_py.protocols.message import Message


async def main():
    async with Client("127.0.0.1", 8080) as client:
        # Create and send a message
        message = Message(
            message_type="greeting",
            payload={"text": "Hello, Server!"},
            message_id="msg-001"
        )
        
        response = await client.send_message(message)
        print(f"Response: {response}")


if __name__ == "__main__":
    asyncio.run(main())
```

## Low-Level Transport API

For more control, you can use the transport layer directly:

### TCP Server (Async)

```python
from extidd_py.transports.tcp.async_server import AsyncTCPServer

def echo_handler(data: bytes, address) -> bytes:
    return data

server = AsyncTCPServer("127.0.0.1", 8888, echo_handler)
await server.start()
```

### TCP Client (Async)

```python
from extidd_py.transports.tcp.async_client import AsyncTCPClient

async with AsyncTCPClient("127.0.0.1", 8888) as client:
    await client.send(b"Hello!")
    response = await client.receive()
    print(response)
```

## Examples

See the `examples/` directory for complete working examples:
- `message_echo.py` - High-level message-based server and client (recommended)
- `field_references_demo.py` - Declarative message definitions with field references
- `protocol_registry_demo.py` - Protocol registration and type discrimination
- `tcp_echo_sync.py` - Low-level synchronous TCP echo server and client
- `udp_echo_sync.py` - Low-level synchronous UDP echo server and client

## Advanced Features

### Field References

PackerPy supports powerful declarative field definitions that can reference other fields. This enables common protocol patterns like:

- **Automatic length prefixes** - Compute field lengths automatically
- **Variable array sizes** - Array sizes determined by other fields  
- **Conditional fields** - Include/exclude fields based on runtime conditions
- **Computed values** - Calculate checksums, flags, and other derived values

```python
class ProtocolMessage(Message):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        # Automatic length prefix
        "payload_length": {"type": "uint(32)", "length_of": "payload"},
        "payload": {"type": "bytes"},
        
        # Variable array size
        "count": {"type": "uint(8)"},
        "items": {"type": "int(32)", "numlist": "count"},
        
        # Conditional field
        "has_metadata": {"type": "bool"},
        "metadata": {
            "type": "str",
            "condition": lambda msg: hasattr(msg, 'has_metadata') and msg.has_metadata
        },
        
        # Computed checksum
        "checksum": {
            "type": "uint(32)",
            "compute": lambda msg: sum(msg.payload) & 0xFFFFFFFF
        }
    }
```

See [FIELD_REFERENCES.md](FIELD_REFERENCES.md) for complete documentation and examples.

## Serialization Options

PackerPy supports multiple serialization formats that can be mixed within the same message:

### JSON Serializer

Use human-readable JSON for debugging, APIs, or when interoperability matters:

```python
from packerpy.protocols.serializer import JSONSerializer

# Serialize to JSON
serializer = JSONSerializer(indent=2)
json_bytes = serializer.serialize(message)

# Pretty-print for debugging
print(serializer.serialize_to_string(message, indent=2))

# Deserialize from JSON
restored = serializer.deserialize(json_bytes, MessageClass)
```

### Mixed Serialization

Optimize different parts of your message independently - binary for speed, JSON for flexibility:

```python
from packerpy.protocols.serializer import BytesSerializer, JSONSerializer

class OptimizedMessage(Message):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        # Compact binary header for efficiency
        "header": {"type": HeaderPartial, "serializer": BytesSerializer()},
        
        # JSON payload for human-readability
        "payload": {"type": PayloadPartial, "serializer": JSONSerializer()},
        
        # Binary footer for checksums
        "footer": {"type": FooterPartial, "serializer": BytesSerializer()},
    }
```

**Benefits:**
- **Performance:** Binary where speed matters
- **Debugging:** JSON where you need visibility
- **Compatibility:** Match external system requirements
- **Flexibility:** Choose the right tool for each field

See [JSON_SERIALIZATION.md](JSON_SERIALIZATION.md) for complete documentation and examples.

## Architecture Overview

This project follows a layered architecture:

1. **Application Layer:** `Server` and `Client` classes provide the main API
2. **Protocol Layer:** `Protocol` and `Message` classes handle encoding/decoding
3. **Transport Layer:** TCP/UDP transports handle network communication

The architecture allows you to:
- Use the high-level API for most use cases
- Drop down to the protocol layer for custom message handling
- Access the transport layer for maximum control

## Development

This project follows the Network Communications pattern.
See the source code for implementation details.

## License

MIT
