# Deep Assignment Feature Implementation Summary

## Overview

This feature adds support for **deep assignments** - the ability to automatically set nested fields within MessagePartial objects directly from the parent Message's field specification. This eliminates the need to manually set header fields after creating messages.

## What Was Implemented

### 1. Core Implementation (message.py)

**New `_apply_deep_assignments()` method:**
- Scans field specifications for keys matching pattern `"field.nested.path"`
- Extracts deep assignment specifications
- Computes values using existing field reference mechanisms
- Applies values to nested fields before serialization
- Supports multiple levels of nesting

**Enhanced `_compute_field_value()` method:**
- Updated `length_of` to handle MessagePartial instances
- Checks for custom serializers when computing lengths
- Returns serialized byte size for MessagePartials

**Integration in `serialize_bytes()`:**
- Calls `_apply_deep_assignments()` for MessagePartial fields before serialization
- Ensures deep assignments are applied after regular field computation

### 2. Comprehensive Test Suite (test_deep_assignment.py)

**Test Coverage:**
- Basic deep assignment with `length_of`, `size_of`, `compute`
- Length computation for entire MessagePartial objects
- Multiple deep assignments in one field spec
- Deeply nested assignments (2+ levels)
- Cross-partial references in deep assignments
- Deep assignments with custom serializers (JSON, Bytes)
- Real-world protocol packet scenarios
- Error handling for invalid assignments

**Test Statistics:**
- 12 test cases in the new test file
- All existing tests still pass (416 total unit tests)

### 3. Demonstration Example (deep_assignment_demo.py)

**Examples Included:**
1. Basic deep assignment matching user's exact syntax
2. Multiple deep assignments in one field
3. Deeply nested deep assignments
4. Deep assignment with cross-partial references
5. Real-world protocol with mixed serialization

### 4. Documentation Updates (FIELD_REFERENCES.md)

**New Section:** "Deep Assignment to Nested Fields"
- Comprehensive explanation of the feature
- Syntax examples for all assignment types
- Multiple and nested assignments
- Combination with cross-partial references
- Integration with custom serializers
- Real-world protocol example

**Updated Sections:**
- Overview: Added deep assignments to feature list
- Examples: Added reference to deep_assignment_demo.py
- Troubleshooting: Added deep assignment specific errors

## Syntax

Deep assignments use the field name followed by a dot and the nested path as a key:

```python
class Header(MessagePartial):
    fields = {
        "payload_length": {"type": "uint(32)"},
        "checksum": {"type": "uint(32)"},
    }

class Message(Message):
    fields = {
        "header": {
            "type": Header,
            "header.payload_length": {"length_of": "payload"},
            "header.checksum": {"compute": lambda msg: sum(msg.payload) & 0xFFFFFFFF}
        },
        "payload": {"type": "bytes"}
    }
```

### Supported Patterns

1. **Single-level assignment:**
   ```python
   "header.field": {"length_of": "data"}
   ```

2. **Multi-level assignment:**
   ```python
   "outer.inner.field": {"length_of": "data"}
   ```

3. **Cross-partial references:**
   ```python
   "header.data_len": {"length_of": "payload.data"}
   ```

4. **Multiple assignments:**
   ```python
   "header": {
       "type": Header,
       "header.field1": {"length_of": "data"},
       "header.field2": {"compute": lambda msg: ...}
   }
   ```

5. **With serializers:**
   ```python
   "header": {
       "type": Header,
       "serializer": BytesSerializer(),
       "header.payload_length": {"length_of": "payload"}  # Respects payload's serializer
   }
   ```

## User's Exact Example

The implementation fully supports the user's requested syntax:

```python
class HelloHeader(MessagePartial):
    fields = {
        "id": {"type": "int(8)"},
        "payload_length": {"type": "int(16)"}
    }

class HelloPayload(MessagePartial):
    fields = {
        "greeting": {"type": "str"},
        "target": {"type": "str"}
    }

class HelloMessage(Message):
    fields = {
        "header": {
            "type": HelloHeader,
            "header.payload_length": {"length_of": "payload"},
            "serializer": BytesSerializer()
        },
        "payload": {
            "type": HelloPayload,
            "serializer": JSONSerializer()
        }
    }
```

This automatically computes `header.payload_length` as the byte size of the JSON-serialized payload.

## Key Design Decisions

1. **Dot Notation in Keys**: Using the field name as a prefix in the key (e.g., `"header.payload_length"`) is intuitive and clearly indicates the assignment target

2. **Declarative**: All assignments are declared in the field specification, making the protocol structure self-documenting

3. **Execution Order**: Deep assignments are applied after regular field value computation but before serialization of the MessagePartial

4. **Serializer Awareness**: When computing lengths of MessagePartials, the system checks if a custom serializer is used and applies it

5. **Multiple Assignments**: Supports multiple deep assignments to different nested fields in a single MessagePartial

6. **Nested Support**: Handles arbitrary nesting depth (e.g., `"outer.middle.inner.field"`)

7. **Error Handling**: Provides clear error messages for invalid nested paths, non-existent fields, and type mismatches

## Use Cases

This feature is particularly valuable for:

1. **Protocol Headers**: Headers that need metadata computed from payloads
2. **Automatic Checksums**: Computing checksums/CRCs from payload data
3. **Length Fields**: Setting length fields without manual calculation
4. **Mixed Serialization**: Headers in binary, payloads in JSON
5. **Complex Protocols**: Multi-level nested structures with interdependencies

## Benefits

1. **Eliminates Manual Updates**: No need to manually set header fields after creating messages
2. **Type Safety**: Values are computed and validated during serialization
3. **Declarative**: Protocol structure is clear from field definitions
4. **Maintainable**: Changes to payload automatically reflected in header
5. **Flexible**: Works with all field reference types and custom serializers

## Testing Results

- ✅ All 12 new tests pass
- ✅ All 416 existing unit tests pass
- ✅ Demo runs successfully with expected output
- ✅ No regressions in existing functionality
- ✅ User's exact syntax works as requested

## Files Modified

1. `src/packerpy/protocols/message.py` - Core implementation
2. `tests/unit/test_deep_assignment.py` - New test file
3. `examples/deep_assignment_demo.py` - New demo file
4. `docs/FIELD_REFERENCES.md` - Documentation updates

## Comparison: Before and After

**Before (Manual):**
```python
header = Header(version=1, payload_length=0, checksum=0)
payload = Payload(data=b"Important data")
packet = Packet(header=header, payload=payload)

# Manual computation required
payload_bytes = payload.serialize_bytes()
packet.header.payload_length = len(payload_bytes)
packet.header.checksum = sum(payload_bytes) & 0xFFFFFFFF

serialized = packet.serialize_bytes()
```

**After (Automatic):**
```python
header = Header(version=1, payload_length=0, checksum=0)
payload = Payload(data=b"Important data")
packet = Packet(header=header, payload=payload)

# Deep assignments handle everything automatically
serialized = packet.serialize_bytes()
# header.payload_length and header.checksum are computed automatically
```

## Future Enhancements

Potential improvements:
1. Support for value_from in deep assignments
2. Conditional deep assignments based on flags
3. Validation helpers to ensure consistency
4. Performance optimizations for repeated serialization
5. Support for deep assignments in MessagePartial definitions themselves
