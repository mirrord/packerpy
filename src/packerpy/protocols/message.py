"""Message abstraction for protocol communication."""

from abc import ABC
from typing import Any, Dict, List, Optional, Tuple, Union, Type

from packerpy.protocols.message_partial import (
    MessagePartial,
    Encoding,
    EnumEncoder,
    BitPackingContext,
    BitUnpackingContext,
)


class Message(ABC):
    """
    Base class for protocol messages with declarative field definitions.

    Supports arbitrary encoding schemes through custom encoders.

    Subclasses define fields using class attributes:
    - encoding: Encoding.LITTLE_ENDIAN or Encoding.BIG_ENDIAN
    - fields: Dict mapping field names to type definitions

    Field specification options:
    - type: Built-in type string or MessagePartial class
    - encoder: Custom FieldEncoder instance
    - encode/decode: Custom encode/decode functions
    - enum: Enum class for enum types
    - size: Size parameter for certain encoders
    - numlist: Fixed array size
    - serializer: Serializer instance (BytesSerializer/JSONSerializer) for this field
    - static: Static/constant value for this field (always this value)

    Supported built-in types:
    - Native Python: "int", "str", "float", "double", "bool", "bytes"
    - Sized integers: "int(8)", "int(16)", "int(32)", "int(64)"
    - Unsigned: "uint(8)", "uint(16)", "uint(32)", "uint(64)"
    - MessagePartial subclass instances

    Examples:
        # Basic types
        class TemperatureMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "sensor_id": {"type": "str"},
                "temperature": {"type": "float"},
                "timestamp": {"type": "int(64)"}
            }

        # Custom encoder
        class FixedPointMessage(Message):
            fields = {
                "price": {"type": "custom", "encoder": FixedPointEncoder(16, 16)}
            }

        # Enum type
        class StatusMessage(Message):
            fields = {
                "status": {"type": "enum", "enum": StatusEnum, "size": 1}
            }

        # Nested MessagePartials with arrays
        class SensorArrayMessage(Message):
            fields = {
                "device_name": {"type": "str"},
                "sensors": {"type": SensorDataPartial, "numlist": 4}
            }

        # Mixed serialization - binary header with JSON payload
        from packerpy.protocols.serializer import BytesSerializer, JSONSerializer

        class MixedMessage(Message):
            fields = {
                "header": {"type": HeaderPartial, "serializer": BytesSerializer()},
                "payload": {"type": PayloadPartial, "serializer": JSONSerializer()}
            }

        # Static field values (constants)
        class ProtocolMessage(Message):
            fields = {
                "magic_number": {"type": "int(32)", "static": 0x12345678},
                "version": {"type": "int(16)", "static": 1},
                "data": {"type": "str"}
            }
    """

    encoding: Encoding = Encoding.BIG_ENDIAN
    fields: Dict[str, Dict[str, Any]] = {}
    bitwise: bool = False  # Set to True to enable bitwise packing

    def __init__(self, **kwargs):
        """Initialize with field values."""
        for field_name, field_spec in self.fields.items():
            # Check if field has a static value
            if "static" in field_spec:
                # Always use the static value, ignore kwargs
                setattr(self, field_name, field_spec["static"])
            # Only set attributes that are provided in kwargs
            elif field_name in kwargs:
                setattr(self, field_name, kwargs.get(field_name))

    def _resolve_field_reference(self, field_ref: str) -> Any:
        """
        Resolve a field reference to get its value.

        Args:
            field_ref: Field name to resolve (e.g., "data_length")

        Returns:
            The value of the referenced field
        """
        if not hasattr(self, field_ref):
            raise ValueError(f"Referenced field '{field_ref}' does not exist")
        return getattr(self, field_ref)

    def _compute_field_value(self, field_name: str, field_spec: Dict[str, Any]) -> Any:
        """
        Compute a field's value based on its specification.

        Supports:
        - length_of: Compute length of another field's data
        - size_of: Compute byte size of another field's serialized data
        - value_from: Use value from another field
        - compute: Custom function to compute value

        Args:
            field_name: Name of the field
            field_spec: Field specification

        Returns:
            Computed value for the field
        """
        byteorder = self.encoding.value

        # Compute length of another field
        if "length_of" in field_spec:
            target_field = field_spec["length_of"]
            target_value = self._resolve_field_reference(target_field)

            if isinstance(target_value, (list, tuple)):
                return len(target_value)
            elif isinstance(target_value, (str, bytes)):
                return len(target_value)
            else:
                raise ValueError(
                    f"Cannot compute length of field '{target_field}' with type {type(target_value)}"
                )

        # Compute byte size of another field's serialized data
        elif "size_of" in field_spec:
            target_field = field_spec["size_of"]
            target_value = self._resolve_field_reference(target_field)
            target_spec = self.fields.get(target_field)

            if target_spec is None:
                raise ValueError(
                    f"Target field '{target_field}' not found in field definitions"
                )

            # Serialize target field to get byte size
            serialized = self._serialize_value(target_value, target_spec, byteorder)
            return len(serialized)

        # Use value from another field
        elif "value_from" in field_spec:
            source_field = field_spec["value_from"]
            return self._resolve_field_reference(source_field)

        # Custom compute function
        elif "compute" in field_spec:
            compute_fn = field_spec["compute"]
            if not callable(compute_fn):
                raise ValueError(f"Field '{field_name}': 'compute' must be callable")
            return compute_fn(self)

        # No computation needed, return existing value
        return getattr(self, field_name, None)

    def serialize_bytes(self) -> bytes:
        """
        Serialize this message to bytes based on field definitions.

        Supports both byte-aligned and bitwise encoding modes.
        Supports field references for automatic length/size computation.

        Returns:
            Byte representation
        """
        byteorder = self.encoding.value

        # Check if this message uses bitwise encoding
        if self.bitwise or self._has_bitwise_fields():
            return self._serialize_bitwise(byteorder)

        # Standard byte-aligned serialization
        result = b""

        for field_name, field_spec in self.fields.items():
            # Check if this field should be conditionally included
            if "condition" in field_spec:
                condition_fn = field_spec["condition"]
                if not callable(condition_fn):
                    raise ValueError(
                        f"Field '{field_name}': 'condition' must be callable"
                    )
                if not condition_fn(self):
                    # Skip this field
                    continue

            # Use static value if specified
            if "static" in field_spec:
                value = field_spec["static"]
            # Compute field value if needed (for auto-computed fields)
            elif any(
                k in field_spec
                for k in ["length_of", "size_of", "value_from", "compute"]
            ):
                value = self._compute_field_value(field_name, field_spec)
                # Update the field value for consistency
                setattr(self, field_name, value)
            else:
                value = getattr(self, field_name)

            # Handle fixed-size arrays
            if "numlist" in field_spec:
                # Resolve field reference if numlist refers to another field
                numlist_param = field_spec["numlist"]
                if isinstance(numlist_param, str) and not str(numlist_param).isdigit():
                    # It's a field reference
                    numlist_param = self._resolve_field_reference(numlist_param)

                if not isinstance(value, list):
                    raise ValueError(f"{field_name} must be a list")
                if len(value) != numlist_param:
                    raise ValueError(f"{field_name} must have {numlist_param} elements")
                for item in value:
                    result += self._serialize_value(item, field_spec, byteorder)
            # Handle dynamic arrays with length prefix
            elif field_spec.get("dynamic_array"):
                if not isinstance(value, list):
                    raise ValueError(f"{field_name} must be a list")
                # Write array length
                length = len(value)
                result += length.to_bytes(4, byteorder)
                # Write each element
                for item in value:
                    result += self._serialize_value(item, field_spec, byteorder)
            # Handle dynamic arrays with delimiter
            elif "delimiter" in field_spec:
                if not isinstance(value, list):
                    raise ValueError(f"{field_name} must be a list")
                delimiter = field_spec["delimiter"]
                if not isinstance(delimiter, bytes):
                    raise ValueError(f"Delimiter must be bytes")
                # Write elements separated by delimiter
                for i, item in enumerate(value):
                    if i > 0:
                        result += delimiter
                    result += self._serialize_value(item, field_spec, byteorder)
                # Write final delimiter to mark end
                result += delimiter
            else:
                result += self._serialize_value(value, field_spec, byteorder)

        return result

    def _serialize_value(
        self, value: Any, field_spec: Dict[str, Any], byteorder: str
    ) -> bytes:
        """Serialize a single value based on field specification."""
        field_type = field_spec.get("type")

        # Resolve size parameter if it references another field
        if "size" in field_spec:
            size_param = field_spec["size"]
            if isinstance(size_param, str) and not size_param.isdigit():
                # It's a field reference
                size_param = self._resolve_field_reference(size_param)
                # Create modified spec with resolved size
                field_spec = dict(field_spec)
                field_spec["size"] = size_param

        # Per-field serializer (for mixed serialization)
        if "serializer" in field_spec:
            serializer = field_spec["serializer"]
            # Serialize using the specified serializer
            serialized_data = serializer.serialize(value)
            # Prepend length for deserialization
            length = len(serialized_data)
            return length.to_bytes(4, byteorder) + serialized_data

        # Custom encoder instance
        if "encoder" in field_spec:
            encoder = field_spec["encoder"]
            if isinstance(encoder, FieldEncoder):
                return encoder.encode(value, byteorder)
            raise ValueError(f"Encoder must be a FieldEncoder instance")

        # Custom encode function
        if "encode" in field_spec:
            encode_fn = field_spec["encode"]
            if callable(encode_fn):
                return encode_fn(value, byteorder)
            raise ValueError(f"encode must be callable")

        # Enum type
        if field_type == "enum":
            enum_class = field_spec.get("enum")
            size = field_spec.get("size", 1)
            if enum_class is None:
                raise ValueError("enum field must specify 'enum' class")
            encoder = EnumEncoder(enum_class, size)
            return encoder.encode(value, byteorder)

        # Handle MessagePartial
        if isinstance(field_type, type) and issubclass(field_type, MessagePartial):
            if not isinstance(value, field_type):
                raise ValueError(
                    f"Expected {field_type.__name__}, got {type(value).__name__}"
                )
            return value.serialize_bytes()

        # Handle string types
        if not isinstance(field_type, str):
            raise ValueError(
                f"Field type must be str or MessagePartial subclass, got {type(field_type)}"
            )

        # Sized integers
        if field_type.startswith("int("):
            bits = int(field_type[4:-1])
            byte_size = bits // 8
            return value.to_bytes(byte_size, byteorder, signed=True)
        elif field_type.startswith("uint("):
            bits = int(field_type[5:-1])
            byte_size = bits // 8
            return value.to_bytes(byte_size, byteorder, signed=False)
        # Native Python types
        elif field_type == "int":
            return value.to_bytes(8, byteorder, signed=True)
        elif field_type == "str":
            value_bytes = value.encode("utf-8")
            length = len(value_bytes)
            return length.to_bytes(4, byteorder) + value_bytes
        elif field_type == "float":
            import struct

            fmt = "<f" if byteorder == "little" else ">f"
            return struct.pack(fmt, value)
        elif field_type == "double":
            import struct

            fmt = "<d" if byteorder == "little" else ">d"
            return struct.pack(fmt, value)
        elif field_type == "bool":
            return bytes([1 if value else 0])
        elif field_type == "bytes":
            length = len(value)
            return length.to_bytes(4, byteorder) + value
        else:
            raise ValueError(f"Unsupported type: {field_type}")

    def _has_bitwise_fields(self) -> bool:
        """Check if any fields use bitwise encoding."""
        for field_spec in self.fields.values():
            if field_spec.get("type") == "bit" or "bits" in field_spec:
                return True
        return False

    @classmethod
    def _has_bitwise_fields_static(cls) -> bool:
        """Check if any fields use bitwise encoding (class method version)."""
        for field_spec in cls.fields.values():
            if field_spec.get("type") == "bit" or "bits" in field_spec:
                return True
        return False

    def _serialize_bitwise(self, byteorder: str) -> bytes:
        """
        Serialize using bitwise packing.

        Packs all fields at bit-level resolution into the minimum
        number of bytes required.

        Args:
            byteorder: Byte order for multi-byte values

        Returns:
            Packed bytes
        """
        context = BitPackingContext(byteorder)

        for field_name, field_spec in self.fields.items():
            # Use static value if specified
            if "static" in field_spec:
                value = field_spec["static"]
            else:
                value = getattr(self, field_name)
            field_type = field_spec.get("type")

            # Handle arrays of bitwise fields first
            if "numlist" in field_spec and field_type == "bit":
                if not isinstance(value, list):
                    raise ValueError(f"{field_name} must be a list")
                if len(value) != field_spec["numlist"]:
                    raise ValueError(
                        f"{field_name} must have {field_spec['numlist']} elements"
                    )

                bit_count = field_spec.get("bits", 1)
                signed = field_spec.get("signed", False)

                for item in value:
                    # Validate
                    if signed:
                        min_val = -(2 ** (bit_count - 1))
                        max_val = 2 ** (bit_count - 1) - 1
                    else:
                        min_val = 0
                        max_val = 2**bit_count - 1

                    if item < min_val or item > max_val:
                        raise ValueError(
                            f"{field_name}: value {item} out of range for {bit_count}-bit field"
                        )

                    # Pack
                    if signed and item < 0:
                        item = (1 << bit_count) + item
                    context.pack_bits(item, bit_count)

            # Handle bitwise fields
            elif field_type == "bit":
                bit_count = field_spec.get("bits", 1)
                signed = field_spec.get("signed", False)

                # Validate and pack
                if signed:
                    min_val = -(2 ** (bit_count - 1))
                    max_val = 2 ** (bit_count - 1) - 1
                else:
                    min_val = 0
                    max_val = 2**bit_count - 1

                if value < min_val or value > max_val:
                    raise ValueError(
                        f"{field_name}: value {value} out of range for {bit_count}-bit {'signed' if signed else 'unsigned'} field [{min_val}, {max_val}]"
                    )

                # Convert signed to unsigned representation
                if signed and value < 0:
                    value = (1 << bit_count) + value

                context.pack_bits(value, bit_count)

            # Handle standard byte-aligned fields within bitwise context
            else:
                # For now, bitwise mode requires all fields to be bitwise
                raise ValueError(
                    f"Cannot mix bitwise and byte-aligned fields in bitwise mode. "
                    f"Field '{field_name}' is byte-aligned."
                )

        # Flush any remaining bits
        return context.flush()

    @classmethod
    def _deserialize_bitwise(
        cls, data: bytes, byteorder: str
    ) -> Tuple[Dict[str, Any], int]:
        """
        Deserialize using bitwise unpacking.

        Args:
            data: Bytes to unpack
            byteorder: Byte order

        Returns:
            Tuple of (field values dict, bytes consumed)
        """
        context = BitUnpackingContext(data, byteorder)
        kwargs = {}

        for field_name, field_spec in cls.fields.items():
            field_type = field_spec.get("type")

            # Check if field has a static value
            if "static" in field_spec:
                # Deserialize and verify it matches the static value
                if field_type == "bit":
                    bit_count = field_spec.get("bits", 1)
                    signed = field_spec.get("signed", False)
                    value = context.unpack_bits(bit_count)
                    if signed and (value & (1 << (bit_count - 1))):
                        value -= 1 << bit_count
                else:
                    raise ValueError(
                        f"Static values in bitwise mode only support 'bit' type, got '{field_type}'"
                    )
                expected = field_spec["static"]
                if value != expected:
                    raise ValueError(
                        f"Field '{field_name}': expected static value {expected}, got {value}"
                    )
                kwargs[field_name] = expected
                continue

            # Handle arrays of bitwise fields first
            if "numlist" in field_spec and field_type == "bit":
                bit_count = field_spec.get("bits", 1)
                signed = field_spec.get("signed", False)
                array_size = field_spec["numlist"]

                values = []
                for _ in range(array_size):
                    value = context.unpack_bits(bit_count)

                    # Convert to signed if needed
                    if signed and (value & (1 << (bit_count - 1))):
                        value -= 1 << bit_count

                    values.append(value)

                kwargs[field_name] = values

            # Handle bitwise fields
            elif field_type == "bit":
                bit_count = field_spec.get("bits", 1)
                signed = field_spec.get("signed", False)

                # Unpack bits
                value = context.unpack_bits(bit_count)

                # Convert to signed if needed
                if signed and (value & (1 << (bit_count - 1))):
                    value -= 1 << bit_count

                kwargs[field_name] = value

            else:
                raise ValueError(
                    f"Cannot mix bitwise and byte-aligned fields in bitwise mode. "
                    f"Field '{field_name}' is byte-aligned."
                )

        return kwargs, context.get_bytes_consumed()

    @classmethod
    def deserialize_bytes(cls, data: bytes) -> Tuple["Message", int]:
        """
        Deserialize a message from bytes.

        Supports both byte-aligned and bitwise encoding modes.
        Supports field references for length/size-dependent deserialization.

        Args:
            data: Bytes to deserialize

        Returns:
            Tuple of (Message instance, bytes consumed)
        """
        byteorder = cls.encoding.value

        # Check if this message uses bitwise encoding
        if cls.bitwise or cls._has_bitwise_fields_static():
            kwargs, bytes_consumed = cls._deserialize_bitwise(data, byteorder)
            return cls(**kwargs), bytes_consumed

        # Standard byte-aligned deserialization
        offset = 0
        kwargs = {}

        for field_name, field_spec in cls.fields.items():
            # Check if field has a static value
            if "static" in field_spec:
                # Deserialize and verify it matches the static value
                value, consumed = cls._deserialize_value(
                    data[offset:], field_spec, byteorder, kwargs
                )
                expected = field_spec["static"]
                if value != expected:
                    raise ValueError(
                        f"Field '{field_name}': expected static value {expected}, got {value}"
                    )
                # Set the static value (not the deserialized one, for consistency)
                kwargs[field_name] = expected
                offset += consumed
                continue

            # Check if this field should be conditionally included
            if "condition" in field_spec:
                condition_fn = field_spec["condition"]
                if not callable(condition_fn):
                    raise ValueError(
                        f"Field '{field_name}': 'condition' must be callable"
                    )
                # Create a temporary partial object to check condition
                temp_obj = type("TempMsg", (), {})()
                for k, v in kwargs.items():
                    setattr(temp_obj, k, v)
                if not condition_fn(temp_obj):
                    # Skip this field entirely - don't add it to kwargs at all
                    continue

            # Resolve field reference in numlist if present
            field_spec_resolved = dict(field_spec)
            if "numlist" in field_spec:
                numlist_param = field_spec["numlist"]
                if isinstance(numlist_param, str) and not str(numlist_param).isdigit():
                    # It's a field reference - look it up in already-parsed fields
                    if numlist_param not in kwargs:
                        raise ValueError(
                            f"Field '{field_name}' references '{numlist_param}' which hasn't been parsed yet. Ensure field order is correct."
                        )
                    field_spec_resolved["numlist"] = kwargs[numlist_param]

            # Handle fixed-size arrays
            if "numlist" in field_spec_resolved:
                values = []
                for _ in range(field_spec_resolved["numlist"]):
                    value, consumed = cls._deserialize_value(
                        data[offset:], field_spec, byteorder, kwargs
                    )
                    values.append(value)
                    offset += consumed
                kwargs[field_name] = values
            # Handle dynamic arrays with length prefix
            elif field_spec.get("dynamic_array"):
                if len(data) < offset + 4:
                    raise ValueError("Insufficient data for array length")
                array_length = int.from_bytes(data[offset : offset + 4], byteorder)
                offset += 4
                values = []
                for _ in range(array_length):
                    value, consumed = cls._deserialize_value(
                        data[offset:], field_spec, byteorder, kwargs
                    )
                    values.append(value)
                    offset += consumed
                kwargs[field_name] = values
            # Handle dynamic arrays with delimiter
            elif "delimiter" in field_spec:
                delimiter = field_spec["delimiter"]
                if not isinstance(delimiter, bytes):
                    raise ValueError(f"Delimiter must be bytes")
                values = []
                while True:
                    # Try to deserialize one element
                    value, consumed = cls._deserialize_value(
                        data[offset:], field_spec, byteorder, kwargs
                    )
                    offset += consumed
                    # Check if next bytes are delimiter
                    delimiter_len = len(delimiter)
                    if offset + delimiter_len > len(data):
                        raise ValueError("Missing delimiter at end of array")
                    if data[offset : offset + delimiter_len] == delimiter:
                        offset += delimiter_len
                        # Check if this is the final delimiter (no more data for this field)
                        # We peek ahead - if we can deserialize another element, continue
                        # Otherwise, this was the final delimiter
                        try:
                            if offset < len(data):
                                # Try to deserialize next element
                                test_val, test_consumed = cls._deserialize_value(
                                    data[offset:], field_spec, byteorder, kwargs
                                )
                                # Check if there's a delimiter after it
                                if offset + test_consumed + delimiter_len <= len(data):
                                    if (
                                        data[
                                            offset
                                            + test_consumed : offset
                                            + test_consumed
                                            + delimiter_len
                                        ]
                                        == delimiter
                                    ):
                                        # Valid element, add the previous value and continue
                                        values.append(value)
                                        continue
                        except:
                            pass
                        # This was the final delimiter
                        values.append(value)
                        break
                    else:
                        raise ValueError(f"Expected delimiter at position {offset}")
                kwargs[field_name] = values
            else:
                value, consumed = cls._deserialize_value(
                    data[offset:], field_spec, byteorder, kwargs
                )
                kwargs[field_name] = value
                offset += consumed

        return cls(**kwargs), offset

    @classmethod
    def _deserialize_value(
        cls,
        data: bytes,
        field_spec: Dict[str, Any],
        byteorder: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Any, int]:
        """Deserialize a single value based on field specification.

        Args:
            data: Bytes to deserialize
            field_spec: Field specification
            byteorder: Byte order for deserialization
            context: Dictionary of already-parsed fields for resolving references

        Returns:
            Tuple of (value, bytes_consumed)
        """
        field_type = field_spec.get("type")
        context = context or {}

        # Resolve size parameter if it references another field
        if "size" in field_spec:
            size_param = field_spec["size"]
            if isinstance(size_param, str) and not size_param.isdigit():
                # It's a field reference
                if size_param not in context:
                    raise ValueError(
                        f"Field references '{size_param}' which hasn't been parsed yet. Ensure field order is correct."
                    )
                # Create modified spec with resolved size
                field_spec = dict(field_spec)
                field_spec["size"] = context[size_param]

        # Per-field serializer (for mixed serialization)
        if "serializer" in field_spec:
            serializer = field_spec["serializer"]
            # Read length prefix
            if len(data) < 4:
                raise ValueError("Insufficient data for serializer length prefix")
            length = int.from_bytes(data[0:4], byteorder)
            if len(data) < 4 + length:
                raise ValueError(
                    f"Insufficient data: need {4 + length}, got {len(data)}"
                )
            # Deserialize using the specified serializer
            serialized_data = data[4 : 4 + length]

            # Determine the message class for deserialization
            if isinstance(field_type, type) and issubclass(field_type, MessagePartial):
                value = serializer.deserialize(serialized_data, field_type)
            elif isinstance(field_type, type):
                value = serializer.deserialize(serialized_data, field_type)
            else:
                # For generic types, try to deserialize
                value = serializer.deserialize(serialized_data, Message)

            if value is None:
                raise ValueError(f"Failed to deserialize field with serializer")
            return value, 4 + length

        # Custom decoder instance
        if "encoder" in field_spec:
            encoder = field_spec["encoder"]
            if isinstance(encoder, FieldEncoder):
                return encoder.decode(data, byteorder)
            raise ValueError(f"Encoder must be a FieldEncoder instance")

        # Custom decode function
        if "decode" in field_spec:
            decode_fn = field_spec["decode"]
            if callable(decode_fn):
                return decode_fn(data, byteorder)
            raise ValueError(f"decode must be callable")

        # Enum type
        if field_type == "enum":
            enum_class = field_spec.get("enum")
            size = field_spec.get("size", 1)
            if enum_class is None:
                raise ValueError("enum field must specify 'enum' class")
            encoder = EnumEncoder(enum_class, size)
            return encoder.decode(data, byteorder)

        # Handle MessagePartial
        if isinstance(field_type, type) and issubclass(field_type, MessagePartial):
            instance, consumed = field_type.deserialize_bytes(data)
            return instance, consumed

        # Handle string types
        if not isinstance(field_type, str):
            raise ValueError(
                f"Field type must be str or MessagePartial subclass, got {type(field_type)}"
            )

        # Sized integers
        if field_type.startswith("int("):
            bits = int(field_type[4:-1])
            byte_size = bits // 8
            if len(data) < byte_size:
                raise ValueError(
                    f"Insufficient data: need {byte_size}, got {len(data)}"
                )
            value = int.from_bytes(data[0:byte_size], byteorder, signed=True)
            return value, byte_size
        elif field_type.startswith("uint("):
            bits = int(field_type[5:-1])
            byte_size = bits // 8
            if len(data) < byte_size:
                raise ValueError(
                    f"Insufficient data: need {byte_size}, got {len(data)}"
                )
            value = int.from_bytes(data[0:byte_size], byteorder, signed=False)
            return value, byte_size
        # Native Python types
        elif field_type == "int":
            if len(data) < 8:
                raise ValueError(f"Insufficient data: need 8, got {len(data)}")
            value = int.from_bytes(data[0:8], byteorder, signed=True)
            return value, 8
        elif field_type == "str":
            if len(data) < 4:
                raise ValueError("Insufficient data for length prefix")
            length = int.from_bytes(data[0:4], byteorder)
            if len(data) < 4 + length:
                raise ValueError(
                    f"Insufficient data: need {4 + length}, got {len(data)}"
                )
            value = data[4 : 4 + length].decode("utf-8")
            return value, 4 + length
        elif field_type == "float":
            if len(data) < 4:
                raise ValueError(f"Insufficient data: need 4, got {len(data)}")
            import struct

            fmt = "<f" if byteorder == "little" else ">f"
            value = struct.unpack(fmt, data[0:4])[0]
            return value, 4
        elif field_type == "double":
            if len(data) < 8:
                raise ValueError(f"Insufficient data: need 8, got {len(data)}")
            import struct

            fmt = "<d" if byteorder == "little" else ">d"
            value = struct.unpack(fmt, data[0:8])[0]
            return value, 8
        elif field_type == "bool":
            if len(data) < 1:
                raise ValueError(f"Insufficient data: need 1, got {len(data)}")
            value = bool(data[0])
            return value, 1
        elif field_type == "bytes":
            if len(data) < 4:
                raise ValueError("Insufficient data for length prefix")
            length = int.from_bytes(data[0:4], byteorder)
            if len(data) < 4 + length:
                raise ValueError(
                    f"Insufficient data: need {4 + length}, got {len(data)}"
                )
            value = data[4 : 4 + length]
            return value, 4 + length
        else:
            raise ValueError(f"Unsupported type: {field_type}")

    def validate(self) -> bool:
        """
        Validate this message's data.

        Returns:
            True if valid

        Note:
            Fields with 'compute', 'length_of', 'size_of', 'value_from', or 'condition'
            are not required to be set initially as they are computed or conditional.
        """
        for field_name, field_spec in self.fields.items():
            # Skip validation for computed fields
            if any(
                k in field_spec
                for k in ["compute", "length_of", "size_of", "value_from"]
            ):
                continue

            # Skip validation for conditional fields
            if "condition" in field_spec:
                continue

            # Regular fields must be set
            if not hasattr(self, field_name):
                return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert message to dictionary for JSON/XML serialization.

        Returns:
            Dictionary representation
        """
        result = {"type": self.__class__.__name__}
        for field_name, field_spec in self.fields.items():
            value = getattr(self, field_name)
            field_type = field_spec["type"]

            # Handle MessagePartial
            if isinstance(field_type, type) and issubclass(field_type, MessagePartial):
                if isinstance(value, MessagePartial):
                    result[field_name] = value.to_dict()
                elif isinstance(value, list):
                    result[field_name] = [
                        item.to_dict() if isinstance(item, MessagePartial) else item
                        for item in value
                    ]
                else:
                    result[field_name] = value
            # Handle bytes - convert to list for JSON compatibility
            elif isinstance(value, bytes):
                result[field_name] = list(value)
            elif isinstance(value, list):
                result[field_name] = [
                    item.to_dict() if isinstance(item, MessagePartial) else item
                    for item in value
                ]
            else:
                result[field_name] = value
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """
        Create message from dictionary.

        Args:
            data: Dictionary to deserialize

        Returns:
            Message instance
        """
        kwargs = {}
        for field_name, field_spec in cls.fields.items():
            if field_name not in data:
                continue

            value = data[field_name]
            field_type = field_spec["type"]

            # Handle MessagePartial
            if isinstance(field_type, type) and issubclass(field_type, MessagePartial):
                if isinstance(value, dict):
                    kwargs[field_name] = field_type.from_dict(value)
                elif isinstance(value, list):
                    kwargs[field_name] = [
                        field_type.from_dict(item) if isinstance(item, dict) else item
                        for item in value
                    ]
                else:
                    kwargs[field_name] = value
            # Handle bytes - convert from list if needed
            elif field_type == "bytes" and isinstance(value, list):
                kwargs[field_name] = bytes(value)
            elif isinstance(value, list) and "numlist" in field_spec:
                # Handle list of MessagePartials
                if isinstance(field_type, type) and issubclass(
                    field_type, MessagePartial
                ):
                    kwargs[field_name] = [
                        field_type.from_dict(item) if isinstance(item, dict) else item
                        for item in value
                    ]
                else:
                    kwargs[field_name] = value
            else:
                kwargs[field_name] = value

        return cls(**kwargs)

    def __repr__(self) -> str:
        """String representation of message."""
        field_strs = [f"{name}={getattr(self, name)!r}" for name in self.fields.keys()]
        return f"{self.__class__.__name__}({', '.join(field_strs)})"


class TemperatureMessage(Message):
    """Example message for temperature readings."""

    encoding = Encoding.BIG_ENDIAN
    fields = {
        "sensor_id": {"type": "str"},
        "temperature": {"type": "float"},
        "timestamp": {"type": "int(64)"},
    }


class StatusMessage(Message):
    """Example message for status updates."""

    encoding = Encoding.BIG_ENDIAN
    fields = {
        "device_id": {"type": "str"},
        "is_online": {"type": "bool"},
        "uptime": {"type": "int(32)"},
    }
