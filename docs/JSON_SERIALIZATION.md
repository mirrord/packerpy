# JSON Serializer and Mixed Serialization

This document describes the JSON serializer and mixed serialization feature in PackerPy, which allows messages to contain fields with different serialization formats.

## Overview

PackerPy now supports:
1. **JSON Serializer** - Human-readable JSON serialization for messages
2. **Mixed Serialization** - Different fields in the same message can use different serializers (binary, JSON, etc.)

## JSON Serializer

The `JSONSerializer` class provides text-based encoding/decoding of messages with UTF-8 encoding.

### Features

- **Human-readable** format for debugging and inspection
- **Interoperable** with JSON-based systems and APIs
- **Configurable** output (compact or pretty-printed)
- **Unicode support** for international characters
- Compatible with existing Message and MessagePartial classes

### Usage

```python
from packerpy.protocols.serializer import JSONSerializer
from packerpy.protocols.message_partial import MessagePartial, Encoding

# Define a message
class SensorData(MessagePartial):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "sensor_id": {"type": "str"},
        "temperature": {"type": "float"},
        "unit": {"type": "str"},
    }

# Create instance
sensor = SensorData(
    sensor_id="TEMP-001",
    temperature=23.5,
    unit="celsius"
)

# Serialize to JSON
json_serializer = JSONSerializer(indent=2)
json_bytes = json_serializer.serialize(sensor)

# Deserialize from JSON
restored = json_serializer.deserialize(json_bytes, SensorData)
```

### JSONSerializer Options

```python
JSONSerializer(
    ensure_ascii=False,  # If True, escape non-ASCII chars (default: False)
    indent=None          # Pretty-print indentation (default: None for compact)
)
```

### Methods

- `serialize(message)` - Returns UTF-8 encoded JSON bytes
- `serialize_to_string(message, indent=None)` - Returns JSON string
- `deserialize(data, message_class)` - Deserializes from JSON bytes
- `deserialize_from_string(json_str, message_class)` - Deserializes from JSON string

## Mixed Serialization

Messages can now specify different serializers for different fields, allowing you to optimize each field independently.

### Use Cases

- **Binary headers with JSON payloads** - Compact metadata with flexible data
- **Performance optimization** - Binary for speed, JSON for debugging
- **Protocol compatibility** - Match existing systems' requirements
- **Selective human-readability** - JSON only where needed

### Usage

```python
from packerpy.protocols.message import Message
from packerpy.protocols.message_partial import MessagePartial, Encoding
from packerpy.protocols.serializer import BytesSerializer, JSONSerializer

# Define components
class PacketHeader(MessagePartial):
    """Compact binary header."""
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "version": {"type": "uint(8)"},
        "packet_id": {"type": "uint(32)"},
        "flags": {"type": "uint(8)"},
    }

class DataPayload(MessagePartial):
    """Human-readable JSON payload."""
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "sensor_name": {"type": "str"},
        "temperature": {"type": "float"},
        "humidity": {"type": "float"},
        "location": {"type": "str"},
    }

# Message with mixed serialization
class MixedMessage(Message):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "header": {"type": PacketHeader, "serializer": BytesSerializer()},
        "payload": {"type": DataPayload, "serializer": JSONSerializer()},
    }

# Use it
message = MixedMessage(
    header=PacketHeader(version=1, packet_id=12345, flags=3),
    payload=DataPayload(
        sensor_name="WeatherStation-Alpha",
        temperature=22.5,
        humidity=65.3,
        location="Building A, Floor 3"
    )
)

# Serialize (header as binary, payload as JSON)
data = message.serialize_bytes()

# Deserialize
restored, consumed = MixedMessage.deserialize_bytes(data)
```

## Field-Level Serializer Specification

Add the `serializer` key to field specifications:

```python
fields = {
    "field_name": {
        "type": FieldType,
        "serializer": SerializerInstance()  # BytesSerializer or JSONSerializer
    }
}
```

### Serializer Protocol

Any serializer used in field specifications must implement:

```python
class CustomSerializer:
    def serialize(self, message) -> bytes:
        """Convert message to bytes."""
        pass
    
    def deserialize(self, data: bytes, message_class: type) -> Optional[Message]:
        """Convert bytes back to message."""
        pass
```

## Performance Considerations

### Binary vs JSON Size Comparison

For typical data structures:
- **Binary**: Most compact (e.g., 59 bytes)
- **JSON Compact**: ~2-3x larger (e.g., 157 bytes, +166%)
- **JSON Pretty**: ~3-4x larger (e.g., 171 bytes, +190%)

### When to Use Each

**Use Binary (BytesSerializer) for:**
- Fixed-size headers and footers
- Frequently transmitted data
- Performance-critical fields
- Numeric data and flags
- Network bandwidth optimization

**Use JSON (JSONSerializer) for:**
- Complex, variable-size data
- Human-readable debugging
- API compatibility
- Flexible schema evolution
- Occasional transmission

**Use Mixed for:**
- Best of both worlds
- Optimized protocol design
- Incremental migration
- Domain-specific requirements

## Examples

See the following files for complete examples:
- `examples/mixed_serialization_demo.py` - Comprehensive demonstrations
- `tests/unit/test_json_serializer.py` - Test cases and usage patterns

## Implementation Details

### Serialization Format

When using per-field serializers, each field is stored with a 4-byte length prefix followed by the serialized data:

```
[4 bytes: length] [N bytes: serialized data]
```

This allows the deserializer to:
1. Read the length prefix
2. Extract exactly that many bytes
3. Pass them to the field's serializer

### Compatibility

- Works with all existing Message and MessagePartial types
- Compatible with other features (field references, computed fields, etc.)
- Can be mixed with custom encoders and encode/decode functions
- Supports nested MessagePartials with serializers

## Best Practices

1. **Profile before optimizing** - Measure actual performance impact
2. **Use binary for headers** - Keep metadata compact
3. **Use JSON for payloads** - When flexibility matters
4. **Document your choices** - Explain serialization strategy
5. **Test round-trips** - Verify serialize → deserialize correctness
6. **Consider versioning** - JSON allows easier schema evolution

## Migration Guide

### From Full Binary

```python
# Before: All binary
class MyMessage(Message):
    fields = {
        "header": {"type": Header},
        "payload": {"type": Payload},
    }

# After: Mixed serialization
class MyMessage(Message):
    fields = {
        "header": {"type": Header, "serializer": BytesSerializer()},
        "payload": {"type": Payload, "serializer": JSONSerializer()},
    }
```

### From Full JSON

If you were using `to_dict()`/`from_dict()` externally:

```python
# Before: Manual JSON handling
import json
data = json.dumps(message.to_dict())

# After: Built-in JSON serializer
serializer = JSONSerializer()
data = serializer.serialize(message)
```

## Limitations

1. Serializers add a 4-byte length prefix per field
2. JSON is less efficient than binary for numeric data
3. Per-field serialization is not available for bitwise fields
4. Serializers cannot be mixed with custom encode/decode functions on the same field

## Future Enhancements

Potential future additions:
- XML serializer
- MessagePack serializer
- Protobuf serializer
- Custom compression per field
- Encryption per field
