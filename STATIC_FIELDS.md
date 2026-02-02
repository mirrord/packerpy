# Static Fields in Protocol Messages

## Overview

Static fields are field definitions in protocol messages that have fixed, constant values. These fields are automatically initialized with their declared values and are always serialized with those values, regardless of instance attribute modifications. They are ideal for:

- **Protocol headers and magic numbers**: Identify message format
- **Protocol version identifiers**: Track protocol evolution
- **Message type discriminators**: Distinguish between message types
- **Sync patterns**: Bit-level synchronization markers
- **Fixed constants**: Any field that should always have the same value

## Basic Usage

### Declaring Static Fields

Add the `"static"` key to a field specification:

```python
from packerpy.protocols.protocol import Protocol, protocol
from packerpy.protocols.message import Message

proto = Protocol()

@protocol(proto)
class MyMessage(Message):
    fields = {
        "magic": {"type": "uint(16)", "static": 0xCAFE},  # Static field
        "version": {"type": "uint(8)", "static": 1},       # Static field
        "payload": {"type": "int(32)"},                    # Regular field
    }
```

### Automatic Initialization

Static fields are automatically set when creating message instances:

```python
msg = MyMessage(payload=42)

# Static fields are automatically set
print(msg.magic)    # 0xCAFE
print(msg.version)  # 1
print(msg.payload)  # 42
```

You cannot override static values through the constructor:

```python
# This has no effect - static value is always used
msg = MyMessage(magic=0x1234, payload=42)
print(msg.magic)  # Still 0xCAFE
```

## Serialization Behavior

### Always Uses Static Value

During serialization, the static value from the field specification is always used, **not** the instance attribute value:

```python
msg = MyMessage(payload=100)
msg.magic = 0x9999  # Manually change instance attribute (not recommended)

# Serialization uses static value 0xCAFE, not 0x9999
encoded = proto.encode(msg)
decoded, _ = proto.decode(encoded)
print(decoded.magic)  # 0xCAFE (static value)
```

This ensures protocol consistency even if instance attributes are accidentally modified.

### Works in All Serialization Modes

Static fields work correctly in both serialization modes:

**Byte-aligned mode** (default):
```python
@protocol(proto)
class ByteAligned(Message):
    fields = {
        "header": {"type": "uint(32)", "static": 0xDEADBEEF},
        "data": {"type": "uint(16)"},
    }
```

**Bitwise-packed mode**:
```python
@protocol(proto)
class BitwisePacked(Message):
    fields = {
        "sync": {"type": "uint(4)", "static": 0b1010},  # 4 bits
        "version": {"type": "uint(4)", "static": 2},     # 4 bits
        "flags": {"type": "uint(8)"},                    # 8 bits
    }
```

## Deserialization Validation

When deserializing, PackerPy verifies that the decoded value matches the static field's expected value. If the values don't match, a `ValueError` is raised:

```python
# This would only happen with corrupted data or protocol mismatch
# ValueError: Field 'magic' has static value 0xCAFE, but got 0x1234
```

This automatic validation ensures:
- Messages conform to the protocol specification
- Protocol version mismatches are detected
- Data corruption is caught early
- Message type verification (when using static type fields)

## Use Cases

### 1. Protocol Identification

Use static fields to identify your protocol and version:

```python
@protocol(proto)
class MyProtocolMessage(Message):
    fields = {
        "protocol_id": {"type": "uint(32)", "static": 0x50415242},  # "PARB"
        "version": {"type": "uint(16)", "static": 1},
        # ... rest of message fields
    }
```

### 2. Message Type Discrimination

Create different message types with unique static identifiers:

```python
@protocol(proto)
class RequestMessage(Message):
    fields = {
        "msg_type": {"type": "uint(8)", "static": 0x01},
        "request_id": {"type": "uint(32)"},
        "data": {"type": "bytes(64)"},
    }

@protocol(proto)
class ResponseMessage(Message):
    fields = {
        "msg_type": {"type": "uint(8)", "static": 0x02},
        "request_id": {"type": "uint(32)"},
        "status": {"type": "uint(16)"},
        "result": {"type": "bytes(64)"},
    }
```

Now you can check the decoded message type:

```python
decoded, _ = proto.decode(data)

if isinstance(decoded, RequestMessage):
    assert decoded.msg_type == 0x01
    handle_request(decoded)
elif isinstance(decoded, ResponseMessage):
    assert decoded.msg_type == 0x02
    handle_response(decoded)
```

### 3. Sync Patterns in Bitwise Protocols

Use static fields for bit-level synchronization patterns:

```python
@protocol(proto)
class ControlFrame(Message):
    fields = {
        "sync": {"type": "uint(8)", "static": 0b10101010},  # Alternating pattern
        "frame_type": {"type": "uint(4)", "static": 0b1100},
        "control_flags": {"type": "uint(4)"},
        "payload": {"type": "uint(16)"},
    }
```

### 4. Header Magic Numbers

Standard practice for binary protocols:

```python
@protocol(proto)
class FileHeader(Message):
    fields = {
        "magic": {"type": "bytes(4)", "static": b"FILE"},
        "version": {"type": "uint(16)", "static": 100},
        "flags": {"type": "uint(16)"},
        "file_size": {"type": "uint(64)"},
    }
```

## Field Type Support

Static values work with all field types:

- **Integers**: `uint(n)`, `int(n)` - use integer literals
- **Floats**: `float(32)`, `float(64)` - use float literals
- **Bytes**: `bytes(n)` - use bytes literals (`b"..."`)
- **Strings**: `str(n)` - use string literals (`"..."`)

### Type Matching

The static value must match the field's type:

```python
# Correct
{"type": "uint(16)", "static": 0xABCD}        # int for int type
{"type": "bytes(4)", "static": b"DATA"}       # bytes for bytes type
{"type": "str(8)", "static": "HEADER"}        # str for str type
{"type": "float(32)", "static": 3.14159}      # float for float type

# These will cause errors during message creation
{"type": "uint(16)", "static": b"\xAB\xCD"}   # Wrong: bytes for int type
{"type": "bytes(4)", "static": "DATA"}        # Wrong: str for bytes type
```

## Best Practices

### 1. Use for Protocol Constants

Static fields are perfect for values that should never change in a protocol:

```python
@protocol(proto)
class ProtocolMessage(Message):
    fields = {
        # Good: Protocol constants
        "protocol_version": {"type": "uint(8)", "static": 2},
        "max_payload_size": {"type": "uint(16)", "static": 1024},
        
        # Bad: Don't use static for dynamic data
        # "timestamp": {"type": "uint(64)", "static": 1234567890},  # Wrong!
    }
```

### 2. Document Static Values

Always document why a field is static and what the value means:

```python
fields = {
    # Protocol magic number - identifies messages as part of MyProtocol v2
    "magic": {"type": "uint(32)", "static": 0x4D50524F},  # "MPRO"
    
    # Message type identifier - 0x01 for Request, 0x02 for Response
    "msg_type": {"type": "uint(8)", "static": 0x01},
}
```

### 3. Don't Modify Instance Attributes

While you *can* modify static field instance attributes, you shouldn't:

```python
msg = MyMessage(payload=42)

# Don't do this!
msg.magic = 0x9999  # Has no effect on serialization anyway

# If you need different values, they shouldn't be static fields
```

### 4. Use for Validation

Static fields provide automatic validation during deserialization. Use them to catch:

- Protocol version mismatches
- Message format errors
- Data corruption
- Incorrect message types

## Implementation Details

### Initialization (`__init__`)

When a message instance is created, static fields are set automatically:

```python
# In Message.__init__
for field_name, field_spec in self.fields.items():
    if isinstance(field_spec, dict) and "static" in field_spec:
        setattr(self, field_name, field_spec["static"])
```

### Serialization

Static fields always serialize their declared static value:

```python
# Simplified from Message.serialize_bytes
if "static" in field_spec:
    value = field_spec["static"]  # Use static value, not instance attribute
else:
    value = getattr(self, field_name)
```

### Deserialization

After deserializing a value, it's validated against the static specification:

```python
# Simplified from Message.deserialize_bytes
if "static" in field_spec:
    expected = field_spec["static"]
    if deserialized_value != expected:
        raise ValueError(
            f"Field '{field_name}' has static value {expected}, "
            f"but got {deserialized_value}"
        )
```

## Testing

To test static field behavior:

```python
def test_static_fields():
    proto = Protocol()
    
    @protocol(proto)
    class TestMessage(Message):
        fields = {
            "header": {"type": "uint(16)", "static": 0xABCD},
            "data": {"type": "int(32)"},
        }
    
    # Test automatic initialization
    msg = TestMessage(data=123)
    assert msg.header == 0xABCD
    
    # Test serialization preserves static value
    encoded = proto.encode(msg)
    msg.header = 0x9999  # Manually change
    encoded2 = proto.encode(msg)
    assert encoded == encoded2  # Same encoding despite attribute change
    
    # Test deserialization validation
    decoded, _ = proto.decode(encoded)
    assert decoded.header == 0xABCD
    assert decoded.data == 123
```

## See Also

- [examples/static_fields_demo.py](examples/static_fields_demo.py) - Complete working examples
- [FIELD_REFERENCES.md](FIELD_REFERENCES.md) - Field reference syntax
- [JSON_SERIALIZATION.md](JSON_SERIALIZATION.md) - JSON serialization with static fields
