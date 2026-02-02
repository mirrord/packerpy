# JSON Serialization Quick Reference

## Import

```python
from packerpy.protocols.serializer import BytesSerializer, JSONSerializer
from packerpy.protocols.message import Message
from packerpy.protocols.message_partial import MessagePartial, Encoding
```

## Basic JSON Serialization

```python
# Create serializer
json_serializer = JSONSerializer(indent=2)  # Pretty-print
json_compact = JSONSerializer()  # Compact

# Serialize
json_bytes = json_serializer.serialize(message)
json_string = json_serializer.serialize_to_string(message)

# Deserialize
message = json_serializer.deserialize(json_bytes, MessageClass)
message = json_serializer.deserialize_from_string(json_string, MessageClass)
```

## Mixed Serialization

```python
class MixedMessage(Message):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "field1": {"type": Type1, "serializer": BytesSerializer()},
        "field2": {"type": Type2, "serializer": JSONSerializer()},
    }

# Use normally
msg = MixedMessage(field1=..., field2=...)
data = msg.serialize_bytes()
restored, consumed = MixedMessage.deserialize_bytes(data)
```

## Serializer Options

```python
# Pretty-printed JSON with 2-space indent
JSONSerializer(indent=2)

# Compact JSON (no whitespace)
JSONSerializer()

# Escape non-ASCII characters
JSONSerializer(ensure_ascii=True)

# Binary serialization
BytesSerializer()
```

## When to Use What

| Use Case | Serializer | Why |
|----------|------------|-----|
| Headers/footers | BytesSerializer | Compact, fixed-size |
| Metadata | BytesSerializer | Efficient for simple data |
| Complex payload | JSONSerializer | Flexible, human-readable |
| Debugging | JSONSerializer | Easy to inspect |
| APIs/REST | JSONSerializer | Standard interchange format |
| Performance-critical | BytesSerializer | Fastest, most compact |

## Size Comparison Example

```python
# Same data, different formats
message = DataMessage(x=100, y=200, z=300)

binary = BytesSerializer().serialize(message)   # ~12 bytes
json_compact = JSONSerializer().serialize(message)  # ~40 bytes
json_pretty = JSONSerializer(indent=2).serialize(message)  # ~60 bytes
```

## Complete Example

```python
from packerpy.protocols.serializer import BytesSerializer, JSONSerializer
from packerpy.protocols.message import Message
from packerpy.protocols.message_partial import MessagePartial, Encoding

# Define header (compact binary)
class Header(MessagePartial):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "version": {"type": "uint(8)"},
        "msg_id": {"type": "uint(32)"},
    }

# Define payload (flexible JSON)
class Payload(MessagePartial):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "sensor": {"type": "str"},
        "value": {"type": "float"},
        "unit": {"type": "str"},
    }

# Combine with mixed serialization
class TelemetryMessage(Message):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "header": {"type": Header, "serializer": BytesSerializer()},
        "payload": {"type": Payload, "serializer": JSONSerializer()},
    }

# Use it
msg = TelemetryMessage(
    header=Header(version=1, msg_id=12345),
    payload=Payload(sensor="TEMP-01", value=22.5, unit="celsius")
)

# Serialize (header binary, payload JSON)
data = msg.serialize_bytes()

# Deserialize
restored, consumed = TelemetryMessage.deserialize_bytes(data)

# Debug: Print JSON part
json_ser = JSONSerializer(indent=2)
print(json_ser.serialize_to_string(msg.payload))
```

## Tips

1. **Start with binary** - Use BytesSerializer for everything initially
2. **Add JSON selectively** - Switch to JSON only where needed
3. **Profile performance** - Measure actual impact before optimizing
4. **Use pretty-print for development** - `indent=2` makes debugging easier
5. **Test round-trips** - Always verify serialize → deserialize works

## Documentation

- [JSON_SERIALIZATION.md](JSON_SERIALIZATION.md) - Complete guide
- [JSON_SERIALIZER_IMPLEMENTATION.md](JSON_SERIALIZER_IMPLEMENTATION.md) - Implementation details
- [examples/mixed_serialization_demo.py](examples/mixed_serialization_demo.py) - Working examples
- [tests/unit/test_json_serializer.py](tests/unit/test_json_serializer.py) - Test cases
