# Cross-Partial Field References Implementation Summary

## Overview

This feature adds support for referencing fields inside MessagePartial objects using dot notation in the declarative field syntax. This is particularly useful for protocol headers that need to contain information about payloads.

## What Was Implemented

### 1. Core Implementation (message.py)

**Enhanced `_resolve_field_reference()` method:**
- Added support for dot notation (e.g., `"header.payload_size"`)
- Supports multiple levels of nesting (e.g., `"outer.middle.inner.value"`)
- Validates that intermediate fields are MessagePartial types
- Provides clear error messages for invalid references

**Enhanced `_compute_field_value()` method:**
- Extended `size_of` computation to handle cross-partial references
- Navigates through nested MessagePartial structures
- Uses the correct serialization context for each level

**Enhanced Deserialization:**
- Updated `numlist` parameter resolution to support cross-partial references
- Updated `size` parameter resolution to support cross-partial references
- Added proper error handling with descriptive messages

### 2. Comprehensive Test Suite (test_cross_partial_field_references.py)

**Test Coverage:**
- `length_of` with cross-partial references (bytes, strings, lists)
- `size_of` with cross-partial references (integers, bytes with length prefix)
- Nested MessagePartial references (multi-level dot notation)
- `compute` functions accessing cross-partial fields
- Conditional fields based on cross-partial flags
- Variable-sized arrays using cross-partial count fields
- Complex real-world protocol scenarios
- Error handling for invalid references

**Test Statistics:**
- 15 test cases in the new test file
- All existing tests still pass (404 total unit tests)

### 3. Demonstration Example (cross_partial_references_demo.py)

**Examples Included:**
1. Basic cross-partial reference with `length_of`
2. Array size determined by header field
3. Complex sensor packet with auto-computed header
4. Conditional fields based on partial flags
5. Deeply nested cross-partial references

### 4. Documentation Updates (FIELD_REFERENCES.md)

**New Section:** "Cross-Partial Field References"
- Comprehensive explanation of the feature
- Code examples for all reference types
- Real-world use case examples
- Field order requirements
- Troubleshooting guide

**Updated Sections:**
- Overview: Added cross-partial references to feature list
- Limitations: Removed limitation about not supporting nested field access
- Examples: Added reference to new demo file
- Troubleshooting: Added cross-partial specific error scenarios

## Supported Syntax

All field reference types now support cross-partial references:

```python
# length_of
"field_name": {"type": "uint(32)", "length_of": "partial.field"}

# size_of
"field_name": {"type": "uint(32)", "size_of": "partial.field"}

# numlist (variable array size)
"array_field": {"type": "int(32)", "numlist": "partial.count"}

# condition
"field_name": {
    "type": "int(32)",
    "condition": lambda msg: msg.partial.flag
}

# compute
"field_name": {
    "type": "int(32)",
    "compute": lambda msg: msg.value * msg.partial.multiplier
}

# Nested references
"field_name": {"type": "uint(32)", "length_of": "outer.middle.inner.data"}
```

## Key Design Decisions

1. **Dot Notation**: Using dot notation (`.`) is intuitive and aligns with Python's attribute access syntax

2. **Validation**: The implementation validates that intermediate fields are MessagePartial types, providing clear error messages

3. **Field Order**: Maintains the existing requirement that referenced fields must appear before fields that reference them

4. **Backward Compatibility**: All existing code continues to work without modification

5. **Performance**: Minimal overhead - only adds attribute traversal when dot notation is used

## Use Cases

This feature is particularly valuable for:

1. **Protocol Headers**: Headers that contain metadata about payloads (length, checksum, etc.)
2. **Nested Structures**: Complex message formats with hierarchical data
3. **Dynamic Arrays**: Array sizes determined by fields in separate message partials
4. **Conditional Fields**: Field inclusion based on flags in header structures
5. **Computed Values**: Calculations involving fields from multiple message partials

## Example: Real-World Protocol Packet

```python
class PacketHeader(MessagePartial):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "version": {"type": "uint(8)"},
        "flags": {"type": "uint(8)"},
        "payload_length": {"type": "uint(32)"},
        "checksum": {"type": "uint(32)"},
    }

class PacketPayload(MessagePartial):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "data": {"type": "bytes"},
    }

class ProtocolPacket(Message):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "header": {"type": PacketHeader},
        "payload": {"type": PacketPayload},
    }
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Automatically compute header fields from payload
        if hasattr(self, "payload") and hasattr(self, "header"):
            payload_bytes = self.payload.serialize_bytes()
            self.header.payload_length = len(payload_bytes)
            self.header.checksum = sum(payload_bytes) & 0xFFFFFFFF
```

## Testing Results

- ✅ All 15 new tests pass
- ✅ All 404 existing unit tests pass
- ✅ Demo runs successfully with expected output
- ✅ No regressions in existing functionality

## Files Modified

1. `src/packerpy/protocols/message.py` - Core implementation
2. `tests/unit/test_cross_partial_field_references.py` - New test file
3. `examples/cross_partial_references_demo.py` - New demo file
4. `docs/FIELD_REFERENCES.md` - Documentation updates

## Future Enhancements

Potential future improvements:
1. Support for computed values in MessagePartial definitions themselves
2. Automatic header computation as a built-in feature
3. Validation helpers to ensure header fields match payload
4. Performance optimizations for deeply nested references
