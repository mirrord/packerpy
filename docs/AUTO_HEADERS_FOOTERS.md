# Automatic Headers and Footers

PackerPy now supports **automatic headers and footers** that can be added to every message encoded/decoded by a Protocol. This feature allows you to declaratively define fields that are automatically computed and added before (headers) or after (footers) each message body, with full support for deep field references.

## Overview

Automatic headers and footers enable powerful protocol features such as:
- **Message validation**: CRC checksums, magic numbers, protocol versions
- **Metadata**: Field counts, message sizes, timestamps
- **Length prefixes**: Automatic size calculation for routing/buffering
- **Reference fields**: Copy values from message fields to headers/footers
- **Computed values**: Dynamic calculations based on message content

## Key Features

- **Full field reference support**: Use `length_of`, `size_of`, `value_from`, `compute`, and `static`
- **Deep field references**: Reference nested fields using dot notation (e.g., `"header.version"`)
- **Automatic validation**: Headers and footers are validated during decoding
- **CRC support**: Built-in CRC-32 checksum calculation
- **Helper functions**: Convenient helpers for common operations
- **Thread-safe**: Headers and footers are protected by locks

## Basic Usage

### Setting Headers

Headers are added **before** the message body during encoding:

```python
from packerpy.protocols.protocol import Protocol, protocol
from packerpy.protocols.message import Message
from packerpy.protocols.message_partial import Encoding

MyProtocol = Protocol()

@protocol(MyProtocol)
class DataMessage(Message):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "data": {"type": "str"},
    }

# Set headers
MyProtocol.set_headers({
    "protocol_version": {
        "type": "uint(8)",
        "static": 1  # Always 1
    },
    "message_size": {
        "type": "uint(32)",
        "size_of": "body"  # Size of entire message body
    }
})

# Encode - headers are automatically added
msg = DataMessage(data="Hello World")
encoded = MyProtocol.encode(msg)

# Decode - headers are automatically validated
decoded, _ = MyProtocol.decode(encoded)
```

### Setting Footers

Footers are added **after** the message body during encoding:

```python
# Set footers
MyProtocol.set_footers({
    "checksum": {
        "type": "uint(32)",
        "compute": lambda msg: Protocol.crc32(msg.serialize_bytes())
    },
    "end_marker": {
        "type": "uint(16)",
        "static": 0xFFFF
    }
})

# Encode - footers are automatically added
msg = DataMessage(data="Protected")
encoded = MyProtocol.encode(msg)

# Decode - footers are automatically validated (including CRC!)
decoded, _ = MyProtocol.decode(encoded)
```

## Field Specification Types

Automatic header/footer fields support the same specifications as regular message fields, plus special computation types:

### 1. Static Values

Fixed constant values that never change:

```python
MyProtocol.set_headers({
    "magic_number": {
        "type": "uint(32)",
        "static": 0x12345678
    }
})
```

### 2. `length_of` - Element Count

Count the number of elements in a field (string length, bytes length, or list size):

```python
MyProtocol.set_headers({
    "data_length": {
        "type": "uint(32)",
        "length_of": "data"  # Length of 'data' field
    }
})
```

Works with:
- `str` - returns string length
- `bytes` - returns byte length
- `list` - returns number of elements

### 3. `size_of` - Byte Size

Calculate the serialized byte size of a field:

```python
MyProtocol.set_headers({
    "payload_size": {
        "type": "uint(32)",
        "size_of": "payload"  # Byte size when serialized
    }
})
```

Special keywords:
- `"body"`, `"message"`, or `"payload"` - refers to entire message body

### 4. `value_from` - Copy Field Value

Copy a value from a message field:

```python
MyProtocol.set_headers({
    "message_id": {
        "type": "uint(32)",
        "value_from": "id"  # Copy value from 'id' field
    }
})
```

### 5. `compute` - Custom Function

Use a custom function to compute the value:

```python
def compute_field_count(msg):
    return Protocol.count_fields(msg.message)

MyProtocol.set_headers({
    "field_count": {
        "type": "uint(8)",
        "compute": compute_field_count
    }
})
```

The compute function receives a context object with:
- `msg.message` - the original message instance
- `msg.serialize_bytes()` - the serialized message bytes
- All message fields as attributes

## Deep Field References

Headers and footers support **deep field references** using dot notation to access nested MessagePartial fields:

```python
from packerpy.protocols.message_partial import MessagePartial

class HeaderPartial(MessagePartial):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "version": {"type": "uint(8)"},
        "flags": {"type": "uint(8)"},
    }

@protocol(MyProtocol)
class PacketMessage(Message):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "header": {"type": HeaderPartial},
        "payload": {"type": "bytes"},
    }

# Reference nested field in automatic header
MyProtocol.set_headers({
    "protocol_version": {
        "type": "uint(8)",
        "value_from": "header.version"  # Access nested field
    }
})
```

## Helper Functions

PackerPy provides convenient helper functions for common operations:

### `Protocol.crc32(data, initial=0)`

Calculate CRC-32 checksum of bytes:

```python
data = b"Hello World"
checksum = Protocol.crc32(data)  # Returns uint32
```

Use in footers for message validation:

```python
MyProtocol.set_footers({
    "crc": {
        "type": "uint(32)",
        "compute": lambda msg: Protocol.crc32(msg.serialize_bytes())
    }
})
```

### `Protocol.count_fields(message)`

Count the number of non-None fields in a message:

```python
count = Protocol.count_fields(my_message)

# Use in headers
MyProtocol.set_headers({
    "field_count": {
        "type": "uint(8)",
        "compute": lambda msg: Protocol.count_fields(msg.message)
    }
})
```

### `Protocol.list_length(message, field_name)`

Get the length of a list field:

```python
length = Protocol.list_length(my_message, "items")

# Use in headers
MyProtocol.set_headers({
    "num_items": {
        "type": "uint(8)",
        "compute": lambda msg: Protocol.list_length(msg.message, "items")
    }
})
```

## Advanced Examples

### Example 1: CRC Over Subset of Message

Calculate CRC only over critical fields:

```python
@protocol(MyProtocol)
class DataMessage(Message):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "critical_data": {"type": "int(32)", "numlist": 10},
        "non_critical_notes": {"type": "str"},
    }

def compute_critical_crc(msg):
    """CRC only over critical_data field."""
    data_bytes = b""
    for value in msg.message.critical_data:
        data_bytes += value.to_bytes(4, "big", signed=True)
    return Protocol.crc32(data_bytes)

MyProtocol.set_footers({
    "crc": {
        "type": "uint(32)",
        "compute": compute_critical_crc
    }
})
```

### Example 2: Complete Protocol Protection

Combine multiple headers and footers for robust validation:

```python
MyProtocol.set_headers({
    "protocol_version": {"type": "uint(8)", "static": 1},
    "field_count": {
        "type": "uint(8)",
        "compute": lambda msg: Protocol.count_fields(msg.message)
    },
    "message_size": {
        "type": "uint(32)",
        "size_of": "body"
    }
})

MyProtocol.set_footers({
    "crc32": {
        "type": "uint(32)",
        "compute": lambda msg: Protocol.crc32(msg.serialize_bytes())
    },
    "end_marker": {"type": "uint(16)", "static": 0xFFFF}
})

# All fields are automatically validated during decode!
```

### Example 3: Nested Field References

Access deeply nested fields:

```python
class InnerPartial(MessagePartial):
    fields = {
        "value": {"type": "uint(16)"},
    }

class OuterPartial(MessagePartial):
    fields = {
        "inner": {"type": InnerPartial},
    }

@protocol(MyProtocol)
class NestedMessage(Message):
    fields = {
        "outer": {"type": OuterPartial},
        "data": {"type": "str"},
    }

# Reference deeply nested field
MyProtocol.set_headers({
    "nested_value": {
        "type": "uint(16)",
        "value_from": "outer.inner.value"  # Multi-level nesting
    }
})
```

## Validation

During **decoding**, headers and footers are automatically validated:

1. **Static fields** - verified to match expected values
2. **Computed fields** - recalculated and compared to received values
3. **Validation failures** - message is marked as `InvalidMessage`

Example of tamper detection:

```python
MyProtocol.set_footers({
    "crc": {
        "type": "uint(32)",
        "compute": lambda msg: Protocol.crc32(msg.serialize_bytes())
    }
})

msg = DataMessage(data="Test")
encoded = MyProtocol.encode(msg)

# Tamper with the message
tampered = bytearray(encoded)
tampered[20] ^= 0xFF  # Flip bits

# Decoding detects tampering
result = MyProtocol.decode(bytes(tampered))
if result:
    decoded, _ = result
    if isinstance(decoded, InvalidMessage):
        print(f"Tampering detected: {decoded.error}")
```

## Managing Headers and Footers

### Clear Headers/Footers

Remove all automatic headers or footers:

```python
MyProtocol.clear_headers()  # Remove all headers
MyProtocol.clear_footers()  # Remove all footers
```

### Update Headers/Footers

Call `set_headers()` or `set_footers()` again to replace:

```python
# Set initial headers
MyProtocol.set_headers({"version": {"type": "uint(8)", "static": 1}})

# Replace with new headers
MyProtocol.set_headers({"version": {"type": "uint(8)", "static": 2}})
```

## Supported Field Types

Automatic header/footer fields must use **fixed-size types** for proper encoding/decoding:

**Supported:**
- `uint(8)`, `uint(16)`, `uint(32)`, `uint(64)`
- `int(8)`, `int(16)`, `int(32)`, `int(64)`
- `float`, `double`
- `bool`
- Custom encoders with a `size` attribute

**Not Supported:**
- Variable-length types (`str`, `bytes`) without explicit size
- MessagePartial types (use in message body instead)

## Performance Considerations

- Headers/footers are computed during **every encode operation**
- CRC calculations can be expensive for large messages
- Consider computing CRC over subsets of data if performance is critical
- Headers/footers are validated during **every decode operation**

## Best Practices

### 1. Use Static Values for Protocol Identification

```python
MyProtocol.set_headers({
    "magic": {"type": "uint(32)", "static": 0x50434B52},  # "PCKR"
    "version": {"type": "uint(8)", "static": 1}
})
```

### 2. Always Include CRC for Critical Data

```python
MyProtocol.set_footers({
    "crc": {
        "type": "uint(32)",
        "compute": lambda msg: Protocol.crc32(msg.serialize_bytes())
    }
})
```

### 3. Add End Markers for Stream Parsing

```python
MyProtocol.set_footers({
    "end_marker": {"type": "uint(16)", "static": 0xFFFF}
})
```

### 4. Include Message Size for Efficient Buffering

```python
MyProtocol.set_headers({
    "payload_size": {
        "type": "uint(32)",
        "size_of": "body"
    }
})
```

### 5. Use Field Counts for Validation

```python
MyProtocol.set_headers({
    "field_count": {
        "type": "uint(8)",
        "compute": lambda msg: Protocol.count_fields(msg.message)
    }
})
```

## Error Handling

Automatic header/footer validation errors result in `InvalidMessage`:

```python
result = MyProtocol.decode(data)
if result:
    decoded, remaining = result
    if isinstance(decoded, InvalidMessage):
        print(f"Validation failed: {decoded.error}")
        print(f"Partial type: {decoded.partial_type}")
        print(f"Raw data: {decoded.raw_data.hex()}")
    else:
        # Valid message
        process_message(decoded)
```

## Thread Safety

Headers and footers are protected by internal locks, making them thread-safe for concurrent access across multiple threads encoding/decoding messages.

## Compatibility

Automatic headers and footers are fully compatible with all existing PackerPy features:
- Field references (`length_of`, `size_of`, etc.)
- MessagePartials and nesting
- Mixed serialization (JSON/Binary)
- Static fields
- Auto-replies
- Message scheduling

## Example: Complete Protocol Implementation

```python
from packerpy.protocols.protocol import Protocol, protocol
from packerpy.protocols.message import Message
from packerpy.protocols.message_partial import MessagePartial, Encoding

# Define protocol with full protection
SecureProtocol = Protocol()

class Header(MessagePartial):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "version": {"type": "uint(8)"},
        "flags": {"type": "uint(8)"},
    }

@protocol(SecureProtocol)
class SecureMessage(Message):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "header": {"type": Header},
        "data": {"type": "bytes"},
    }

# Configure protocol-level protection
SecureProtocol.set_headers({
    "magic": {"type": "uint(32)", "static": 0x53454355},  # "SECU"
    "protocol_version": {"type": "uint(8)", "static": 1},
    "message_version": {
        "type": "uint(8)",
        "value_from": "header.version"
    },
    "payload_size": {
        "type": "uint(32)",
        "size_of": "body"
    }
})

SecureProtocol.set_footers({
    "crc32": {
        "type": "uint(32)",
        "compute": lambda msg: Protocol.crc32(msg.serialize_bytes())
    },
    "end_marker": {"type": "uint(16)", "static": 0xFFFF}
})

# Use the protocol
header = Header(version=2, flags=0x01)
msg = SecureMessage(header=header, data=b"Sensitive data")

encoded = SecureProtocol.encode(msg)
decoded, _ = SecureProtocol.decode(encoded)

# All validation happens automatically!
```

## See Also

- [FIELD_REFERENCES.md](FIELD_REFERENCES.md) - Field reference documentation
- [examples/auto_headers_footers_demo.py](../examples/auto_headers_footers_demo.py) - Complete demonstrations
- [tests/unit/test_auto_headers_footers.py](../tests/unit/test_auto_headers_footers.py) - Test examples
