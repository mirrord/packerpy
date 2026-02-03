# Field References in PackerPy Messages

PackerPy now supports powerful field reference features that allow fields to automatically compute values from other fields during encoding/decoding. This enables declarative definitions of common protocol patterns like length prefixes, conditional fields, and computed checksums.

**New**: Cross-partial field references allow you to reference fields inside `MessagePartial` objects using dot notation (e.g., `"header.payload_size"`), making it easy to create protocol headers that contain information about payloads.

## Overview

Field references allow you to:
- **Automatic length prefixes**: Compute field lengths automatically
- **Byte size computation**: Calculate serialized byte sizes
- **Variable array sizes**: Array sizes determined by other fields
- **Conditional fields**: Include/exclude fields based on conditions
- **Computed values**: Calculate field values from other fields
- **Cross-partial references**: Reference fields inside MessagePartial objects using dot notation

## Field Reference Types

### 1. `length_of` - Automatic Length Computation

Automatically compute the length of another field. Works with strings, bytes, and lists.

```python
class LengthPrefixedMessage(Message):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "data_length": {"type": "uint(16)", "length_of": "data"},
        "data": {"type": "bytes"},
    }

# Usage
msg = LengthPrefixedMessage(data=b"Hello, World!")
# data_length is automatically set to 13 during serialization
```

**Behavior:**
- For `bytes` and `str`: Returns the length of the data
- For `list`: Returns the number of elements
- Computed during serialization
- Used during deserialization to validate/read data

### 2. `size_of` - Byte Size Computation

Calculate the serialized byte size of another field, including any encoding overhead (like length prefixes).

```python
class SizeAwareMessage(Message):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "value": {"type": "int(64)"},
        "value_size": {"type": "uint(8)", "size_of": "value"},
    }

# value_size will be 8 (the byte size of int(64))
```

**Behavior:**
- Returns the total serialized byte size
- Includes encoding overhead (e.g., length prefixes for strings/bytes)
- Useful for protocol headers indicating field sizes

### 3. `numlist` with Field Reference - Variable Array Sizes

Specify array sizes using values from other fields instead of hardcoded constants.

```python
class VariableSizeArray(Message):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "count": {"type": "uint(8)"},
        "items": {"type": "int(32)", "numlist": "count"},
    }

# Usage
msg = VariableSizeArray(count=5, items=[100, 200, 300, 400, 500])
# During deserialization, 'count' determines how many items to read
```

**Important:**
- The referenced field (e.g., `count`) must appear **before** the array field in the field dictionary
- Python 3.7+ maintains dictionary insertion order
- The count field is read first, then used to determine array size

### 4. `condition` - Conditional Field Inclusion

Include or exclude fields based on runtime conditions. Conditions are lambda functions that receive the message object.

```python
class ConditionalFieldMessage(Message):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "has_extended": {"type": "bool"},
        "basic_data": {"type": "int(32)"},
        "extended_data": {
            "type": "int(64)",
            "condition": lambda msg: hasattr(msg, 'has_extended') and msg.has_extended
        },
    }

# Usage - without extended data
msg1 = ConditionalFieldMessage(has_extended=False, basic_data=12345)
# extended_data is not serialized

# Usage - with extended data
msg2 = ConditionalFieldMessage(has_extended=True, basic_data=12345, extended_data=999)
# extended_data is serialized
```

**Behavior:**
- If condition returns `False`, field is skipped during serialization
- If condition returns `False` during deserialization, field is not added to the object
- Useful for optional fields, version-specific fields, or flag-based inclusion

**Common Patterns:**

```python
# Flag-based inclusion (single bit)
"field_a": {
    "type": "int(16)",
    "condition": lambda msg: hasattr(msg, 'flags') and (msg.flags & 0x01)
}

# Multiple flags
"field_b": {
    "type": "int(16)",
    "condition": lambda msg: hasattr(msg, 'flags') and (msg.flags & 0x02)
}

# Version-based
"new_field": {
    "type": "int(32)",
    "condition": lambda msg: hasattr(msg, 'version') and msg.version >= 2
}
```

### 5. `compute` - Computed Field Values

Calculate field values using custom functions. The function receives the message object and returns the computed value.

```python
class PacketWithChecksum(Message):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "data": {"type": "bytes"},
        "checksum": {
            "type": "uint(32)",
            "compute": lambda msg: sum(msg.data) & 0xFFFFFFFF
        },
    }

# Usage
msg = PacketWithChecksum(data=b"Test data")
# checksum is automatically computed during serialization
```

**Use Cases:**
- Checksums and CRCs
- Computed sums or products
- Flags derived from other fields
- Timestamps or sequence numbers

**Example - Boolean from flags:**
```python
"has_signature": {
    "type": "bool",
    "compute": lambda msg: (msg.flags & 0x80) != 0
}
```

### 6. `value_from` - Copy Field Values

Copy the value from another field. Useful for redundancy or compatibility.

```python
class RedundantMessage(Message):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "id": {"type": "uint(16)"},
        "id_copy": {"type": "uint(16)", "value_from": "id"},
    }
```

## Field Order and Dependencies

**Critical Rule:** Referenced fields must be defined **before** the fields that reference them in the field dictionary.

```python
# ✅ CORRECT - count comes before items
fields = {
    "count": {"type": "uint(8)"},
    "items": {"type": "int(32)", "numlist": "count"},
}

# ❌ WRONG - items references count which hasn't been parsed yet
fields = {
    "items": {"type": "int(32)", "numlist": "count"},
    "count": {"type": "uint(8)"},
}
```

During deserialization, fields are processed in order. If a field references another field, that other field must have already been parsed.

## Combining Features

You can combine multiple field reference features to create sophisticated protocols:

```python
class ComplexProtocol(Message):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "version": {"type": "uint(8)"},
        "flags": {"type": "uint(8)"},
        
        # Automatic payload length
        "payload_length": {"type": "uint(32)", "length_of": "payload"},
        "payload": {"type": "bytes"},
        
        # Computed boolean from flags
        "has_metadata": {
            "type": "bool",
            "compute": lambda msg: (msg.flags & 0x80) != 0
        },
        
        # Conditional field based on computed boolean
        "metadata": {
            "type": "str",
            "condition": lambda msg: hasattr(msg, 'has_metadata') and msg.has_metadata
        },
        
        # Variable array size from field
        "num_items": {"type": "uint(16)"},
        "items": {"type": "int(32)", "numlist": "num_items"},
        
        # Checksum over payload
        "checksum": {
            "type": "uint(32)",
            "compute": lambda msg: sum(msg.payload) & 0xFFFFFFFF
        },
    }
```

## Validation

The `validate()` method has been updated to handle field references:

- Fields with `compute`, `length_of`, `size_of`, or `value_from` are **not required** to be set initially
- Conditional fields are also **not required** to be set
- Only regular fields without any reference specifications must be present

```python
# This is valid - checksum will be computed
msg = PacketWithChecksum(data=b"Test")
assert msg.validate() == True  # Passes even though checksum not set

# This is also valid - extended_data is conditional
msg = ConditionalFieldMessage(has_extended=False, basic_data=100)
assert msg.validate() == True  # Passes even though extended_data not set
```

## Best Practices

### 1. Field Naming Conventions

Use clear, descriptive names for length/size fields:
- `data_length`, `payload_length` for lengths
- `data_size`, `header_size` for byte sizes
- `count`, `num_items`, `array_size` for array counts

### 2. Error Handling

Always use `hasattr()` in condition lambdas to avoid AttributeErrors:

```python
# ✅ CORRECT - checks if attribute exists
"field": {
    "condition": lambda msg: hasattr(msg, 'flag') and msg.flag
}

# ❌ WRONG - will raise AttributeError if flag doesn't exist
"field": {
    "condition": lambda msg: msg.flag
}
```

### 3. Computed Fields Should Be Deterministic

Ensure computed functions are deterministic and don't rely on external state:

```python
# ✅ CORRECT - deterministic based on message data
"checksum": {
    "compute": lambda msg: sum(msg.data) & 0xFFFFFFFF
}

# ❌ WRONG - depends on external state
import time
"timestamp": {
    "compute": lambda msg: int(time.time())  # Will differ each call
}
```

### 4. Complex Conditions

For complex conditions, consider extracting to a named function:

```python
def should_include_metadata(msg):
    """Determine if metadata field should be included."""
    if not hasattr(msg, 'version') or not hasattr(msg, 'flags'):
        return False
    return msg.version >= 2 and (msg.flags & 0x80) != 0

class Message(Message):
    fields = {
        "metadata": {
            "type": "str",
            "condition": should_include_metadata
        }
    }
```

## Cross-Partial Field References

**New Feature**: Field references now support referencing fields inside `MessagePartial` objects using dot notation. This is particularly useful for protocol headers that need to contain information about payloads.

### Basic Cross-Partial References

Use dot notation to reference fields within MessagePartial objects:

```python
class PayloadData(MessagePartial):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "data": {"type": "bytes"},
    }

class PacketWithHeader(Message):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "version": {"type": "uint(8)"},
        "payload_length": {
            "type": "uint(32)",
            "length_of": "payload.data"  # Cross-partial reference
        },
        "payload": {"type": PayloadData},
    }

# Usage
payload = PayloadData(data=b"Hello, World!")
packet = PacketWithHeader(version=1, payload_length=0, payload=payload)
# payload_length is automatically computed to 13 during serialization
```

### Supported Field Reference Types

Cross-partial references work with all field reference types:

**1. `length_of` with Cross-Partial:**
```python
class Header(MessagePartial):
    fields = {"info": {"type": "str"}}

class Message(Message):
    fields = {
        "header": {"type": Header},
        "info_length": {"type": "uint(16)", "length_of": "header.info"}
    }
```

**2. `size_of` with Cross-Partial:**
```python
class Config(MessagePartial):
    fields = {"timestamp": {"type": "uint(64)"}}

class Message(Message):
    fields = {
        "config": {"type": Config},
        "timestamp_size": {"type": "uint(8)", "size_of": "config.timestamp"}
        # Will be 8 (bytes)
    }
```

**3. `numlist` with Cross-Partial:**
```python
class ArrayHeader(MessagePartial):
    fields = {
        "item_count": {"type": "uint(8)"}
    }

class Message(Message):
    fields = {
        "header": {"type": ArrayHeader},
        "items": {"type": "int(32)", "numlist": "header.item_count"}
    }
```

**4. `condition` with Cross-Partial:**
```python
class Flags(MessagePartial):
    fields = {
        "has_extended": {"type": "bool"}
    }

class Message(Message):
    fields = {
        "flags": {"type": Flags},
        "extended_data": {
            "type": "int(64)",
            "condition": lambda msg: hasattr(msg, "flags") and msg.flags.has_extended
        }
    }
```

**5. `compute` with Cross-Partial:**
```python
class Config(MessagePartial):
    fields = {
        "multiplier": {"type": "uint(16)"},
        "offset": {"type": "int(16)"}
    }

class Message(Message):
    fields = {
        "config": {"type": Config},
        "base_value": {"type": "int(32)"},
        "computed": {
            "type": "int(32)",
            "compute": lambda msg: msg.base_value * msg.config.multiplier + msg.config.offset
        }
    }
```

### Nested MessagePartial References

Cross-partial references support multiple levels of nesting:

```python
class InnerData(MessagePartial):
    fields = {"value": {"type": "bytes"}}

class MiddleLayer(MessagePartial):
    fields = {"inner": {"type": InnerData}}

class NestedPacket(Message):
    fields = {
        "middle": {"type": MiddleLayer},
        "value_length": {
            "type": "uint(32)",
            "length_of": "middle.inner.value"  # Deep nested reference
        }
    }
```

### Real-World Use Case: Protocol Headers

A common use case is protocol packets where the header contains metadata about the payload:

```python
class PacketHeader(MessagePartial):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "version": {"type": "uint(8)"},
        "payload_size": {"type": "uint(32)"},
        "checksum": {"type": "uint(32)"},
    }

class Payload(MessagePartial):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "data": {"type": "bytes"},
    }

class ProtocolPacket(Message):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "header": {"type": PacketHeader},
        "payload": {"type": Payload},
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Automatically compute header fields from payload
        if hasattr(self, "payload") and hasattr(self, "header"):
            payload_bytes = self.payload.serialize_bytes()
            self.header.payload_size = len(payload_bytes)
            self.header.checksum = sum(payload_bytes) & 0xFFFFFFFF
```

### Field Order Requirements

For deserialization to work correctly:
- The MessagePartial containing the referenced field must appear **before** the field that references it
- For `numlist` references: The count field must be deserialized before the array

**Correct Order:**
```python
fields = {
    "header": {"type": HeaderPartial},           # Parsed first
    "item_count": {"type": "uint(8)", "length_of": "header.items"},  # Can reference header
}
```

**Incorrect Order:**
```python
fields = {
    "item_count": {"type": "uint(8)", "length_of": "header.items"},  # Error!
    "header": {"type": HeaderPartial},           # Parsed after
}
```

## Performance Considerations

- **Computed fields** are evaluated during serialization, adding minimal overhead
- **Conditional checks** are evaluated for each field, but are typically very fast
- **Field references** require dictionary lookups but are cached during execution
- Overall performance impact is negligible for most use cases

## Limitations

1. **Forward references not supported**: Fields can only reference earlier fields in the field dictionary order
2. **Circular references**: Not supported and will cause infinite loops or stack overflow
3. **Deep field access requires correct types**: Cross-partial references require the intermediate fields to be MessagePartial types
4. **Condition complexity**: Very complex conditions might impact readability and maintainability

## Examples

See the following examples for comprehensive working demonstrations:
- [examples/field_references_demo.py](../examples/field_references_demo.py) - Basic field reference features
- [examples/cross_partial_references_demo.py](../examples/cross_partial_references_demo.py) - Cross-partial field references with nested MessagePartials

## Migration Guide

If you have existing code that manually handles length prefixes or conditional fields:

**Before:**
```python
class OldMessage(Message):
    fields = {
        "data_length": {"type": "uint(16)"},
        "data": {"type": "bytes"},
    }

# Manual length calculation
msg = OldMessage(data_length=len(my_data), data=my_data)
```

**After:**
```python
class NewMessage(Message):
    fields = {
        "data_length": {"type": "uint(16)", "length_of": "data"},
        "data": {"type": "bytes"},
    }

# Automatic length calculation
msg = NewMessage(data=my_data)  # length computed automatically
```

## Troubleshooting

### "Referenced field 'X' does not exist"
The field you're referencing doesn't exist in the message. Check spelling and ensure the field is defined.

### "Referenced field 'X.Y' does not exist: 'Y' not found"
When using cross-partial references with dot notation, the nested field 'Y' doesn't exist in the MessagePartial 'X'. Verify the field name and structure.

### "Field 'X' is not a MessagePartial, cannot reference nested fields"
You're trying to use dot notation on a field that isn't a MessagePartial. Only MessagePartial fields support nested field references.

### "Field 'X' references 'Y' which hasn't been parsed yet"
During deserialization, field X needs field Y's value, but Y comes after X in the field order. Reorder your fields so Y comes before X.

### Conditional field is always included/excluded
Ensure your condition lambda uses `hasattr()` and checks for the correct attributes. Enable debug logging to see condition evaluation.

### Computed value is None
Make sure the compute lambda doesn't rely on fields that haven't been set yet. The compute function runs during serialization, so all non-computed fields should be set.
