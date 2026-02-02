"""MessagePartial base class with support for arbitrary encoding schemes."""

from abc import ABC
from enum import Enum, IntEnum
from typing import Any, Dict, List, Tuple, Union, Type, Callable, Optional
import struct


class Encoding(Enum):
    """Byte order encodings."""

    LITTLE_ENDIAN = "little"
    BIG_ENDIAN = "big"


class FieldEncoder(ABC):
    """
    Base class for custom field encoders.

    Allows users to define arbitrary encoding schemes for field types.
    """

    @staticmethod
    def encode(value: Any, byteorder: str) -> bytes:
        """Encode a value to bytes."""
        raise NotImplementedError

    @staticmethod
    def decode(data: bytes, byteorder: str) -> Tuple[Any, int]:
        """Decode bytes to value. Returns (value, bytes_consumed)."""
        raise NotImplementedError


class FixedPointEncoder(FieldEncoder):
    """
    Encoder for fixed-point numbers.

    Example:
        # 16.16 fixed point (16 bits integer, 16 bits fraction)
        fields = {
            "price": {"type": "custom", "encoder": FixedPointEncoder(16, 16)}
        }
    """

    def __init__(self, int_bits: int, frac_bits: int, signed: bool = True):
        self.int_bits = int_bits
        self.frac_bits = frac_bits
        self.signed = signed
        self.total_bits = int_bits + frac_bits
        self.scale = 2**frac_bits

    def encode(self, value: float, byteorder: str) -> bytes:
        """Encode float as fixed-point."""
        fixed = int(value * self.scale)
        byte_size = (self.total_bits + 7) // 8

        # Check for overflow
        if self.signed:
            max_val = (1 << (self.total_bits - 1)) - 1
            min_val = -(1 << (self.total_bits - 1))
            if fixed > max_val or fixed < min_val:
                raise ValueError(
                    f"Value {value} out of range for {self.int_bits}.{self.frac_bits} fixed point"
                )
        else:
            max_val = (1 << self.total_bits) - 1
            if fixed > max_val or fixed < 0:
                raise ValueError(
                    f"Value {value} out of range for {self.int_bits}.{self.frac_bits} unsigned fixed point"
                )

        return fixed.to_bytes(byte_size, byteorder, signed=self.signed)

    def decode(self, data: bytes, byteorder: str) -> Tuple[float, int]:
        """Decode fixed-point to float."""
        byte_size = (self.total_bits + 7) // 8
        if len(data) < byte_size:
            raise ValueError(f"Insufficient data: need {byte_size}, got {len(data)}")
        fixed = int.from_bytes(data[0:byte_size], byteorder, signed=self.signed)
        value = fixed / self.scale
        return value, byte_size


class EnumEncoder(FieldEncoder):
    """
    Encoder for enum types.

    Example:
        class Status(IntEnum):
            IDLE = 0
            ACTIVE = 1
            ERROR = 2

        fields = {
            "status": {"type": "enum", "enum": Status, "size": 1}
        }
    """

    def __init__(self, enum_class: Type[IntEnum], size: int = 1):
        self.enum_class = enum_class
        self.size = size

    def encode(self, value: Union[IntEnum, int], byteorder: str) -> bytes:
        """Encode enum value."""
        if isinstance(value, IntEnum):
            value = value.value
        return value.to_bytes(self.size, byteorder, signed=False)

    def decode(self, data: bytes, byteorder: str) -> Tuple[IntEnum, int]:
        """Decode enum value."""
        if len(data) < self.size:
            raise ValueError(f"Insufficient data: need {self.size}, got {len(data)}")
        value = int.from_bytes(data[0 : self.size], byteorder, signed=False)
        return self.enum_class(value), self.size


class RunLengthEncoder(FieldEncoder):
    """
    Encoder for run-length encoded data.

    Example:
        fields = {
            "compressed_data": {"type": "custom", "encoder": RunLengthEncoder()}
        }
    """

    def encode(self, value: bytes, byteorder: str) -> bytes:
        """Encode bytes using run-length encoding."""
        if not value:
            return b"\x00\x00\x00\x00"  # Empty data

        result = []
        i = 0
        while i < len(value):
            current = value[i]
            count = 1
            while (
                i + count < len(value) and value[i + count] == current and count < 255
            ):
                count += 1
            result.append(count)
            result.append(current)
            i += count

        # Prefix with length
        encoded = bytes(result)
        length = len(encoded)
        return length.to_bytes(4, byteorder) + encoded

    def decode(self, data: bytes, byteorder: str) -> Tuple[bytes, int]:
        """Decode run-length encoded bytes."""
        if len(data) < 4:
            raise ValueError("Insufficient data for length prefix")
        length = int.from_bytes(data[0:4], byteorder)
        if len(data) < 4 + length:
            raise ValueError(f"Insufficient data: need {4 + length}, got {len(data)}")

        encoded = data[4 : 4 + length]
        result = []
        for i in range(0, len(encoded), 2):
            if i + 1 >= len(encoded):
                break
            count = encoded[i]
            value = encoded[i + 1]
            result.extend([value] * count)

        return bytes(result), 4 + length


class SevenBitASCIIEncoder(FieldEncoder):
    """
    Encoder for 7-bit ASCII packed encoding.

    Packs 8 characters into 7 bytes instead of 8.

    Example:
        fields = {
            "ascii_text": {"type": "custom", "encoder": SevenBitASCIIEncoder()}
        }
    """

    def encode(self, value: str, byteorder: str) -> bytes:
        """Encode string as packed 7-bit ASCII."""
        # Convert to 7-bit values
        ascii_values = [ord(c) & 0x7F for c in value]

        # Pack into bytes
        packed = []
        bit_buffer = 0
        bits_in_buffer = 0

        for val in ascii_values:
            bit_buffer = (bit_buffer << 7) | val
            bits_in_buffer += 7

            while bits_in_buffer >= 8:
                bits_in_buffer -= 8
                byte = (bit_buffer >> bits_in_buffer) & 0xFF
                packed.append(byte)
                bit_buffer &= (1 << bits_in_buffer) - 1

        # Flush remaining bits
        if bits_in_buffer > 0:
            packed.append((bit_buffer << (8 - bits_in_buffer)) & 0xFF)

        # Prefix with length (number of characters)
        length = len(value)
        return length.to_bytes(2, byteorder) + bytes(packed)

    def decode(self, data: bytes, byteorder: str) -> Tuple[str, int]:
        """Decode packed 7-bit ASCII to string."""
        if len(data) < 2:
            raise ValueError("Insufficient data for length prefix")

        char_count = int.from_bytes(data[0:2], byteorder)
        packed_data = data[2:]

        # Unpack 7-bit values
        bit_buffer = 0
        bits_in_buffer = 0
        chars = []

        for byte in packed_data:
            bit_buffer = (bit_buffer << 8) | byte
            bits_in_buffer += 8

            while bits_in_buffer >= 7 and len(chars) < char_count:
                bits_in_buffer -= 7
                val = (bit_buffer >> bits_in_buffer) & 0x7F
                chars.append(chr(val))
                bit_buffer &= (1 << bits_in_buffer) - 1

            if len(chars) >= char_count:
                break

        # Calculate bytes consumed
        packed_bytes = (char_count * 7 + 7) // 8
        total_consumed = 2 + packed_bytes

        return "".join(chars), total_consumed


class BitwiseEncoder(FieldEncoder):
    """
    Encoder for bitwise field packing at single-bit resolution.

    Allows efficient packing of multiple fields into bytes by specifying
    bit offsets and sizes. This is ideal for protocols that pack multiple
    boolean flags or small integers into single bytes.

    Example:
        # Pack 3 flags and a 5-bit value into 1 byte
        class StatusByte(MessagePartial):
            encoding = Encoding.BIG_ENDIAN
            bitwise = True  # Enable bitwise mode
            fields = {
                "flag_a": {"type": "bit", "bits": 1},      # 1 bit
                "flag_b": {"type": "bit", "bits": 1},      # 1 bit
                "flag_c": {"type": "bit", "bits": 1},      # 1 bit
                "counter": {"type": "bit", "bits": 5},     # 5 bits
            }

        # Pack multiple small integers efficiently
        class CompactData(MessagePartial):
            bitwise = True
            fields = {
                "sensor_id": {"type": "bit", "bits": 4},   # 0-15
                "reading": {"type": "bit", "bits": 12},    # 0-4095
            }

    Field specification for bitwise encoding:
    - type: "bit" to indicate bitwise field
    - bits: Number of bits (1-64)
    - signed: Optional, True for signed integers (default False)

    Note: Bitwise fields are packed in declaration order. When all fields
    are processed, any remaining bits are padded to the next byte boundary.
    """

    def __init__(self, bits: int, signed: bool = False):
        """
        Initialize bitwise encoder.

        Args:
            bits: Number of bits for this field (1-64)
            signed: Whether to treat as signed integer
        """
        if bits < 1 or bits > 64:
            raise ValueError("Bits must be between 1 and 64")
        self.bits = bits
        self.signed = signed

    def encode(self, value: int, byteorder: str) -> bytes:
        """
        Encode integer value to the specified number of bits.

        Note: This returns partial bits. The actual byte packing
        is handled by the BitPackingContext.

        Args:
            value: Integer value to encode
            byteorder: Byte order (not used for single field, but kept for interface)

        Returns:
            Bytes containing the packed bits
        """
        # Validate value range
        if self.signed:
            min_val = -(2 ** (self.bits - 1))
            max_val = 2 ** (self.bits - 1) - 1
        else:
            min_val = 0
            max_val = 2**self.bits - 1

        if value < min_val or value > max_val:
            raise ValueError(
                f"Value {value} out of range for {self.bits}-bit {'signed' if self.signed else 'unsigned'} field [{min_val}, {max_val}]"
            )

        # Convert signed to unsigned representation if needed
        if self.signed and value < 0:
            value = (1 << self.bits) + value

        # Return the bit pattern (to be assembled by context)
        # We encode as bytes with metadata about bit count
        byte_count = (self.bits + 7) // 8
        return value.to_bytes(byte_count, "big", signed=False)

    def decode(self, data: bytes, byteorder: str) -> Tuple[int, int]:
        """
        Decode bits to integer value.

        Note: This is called by BitPackingContext which extracts
        the appropriate bits.

        Args:
            data: Bytes containing the bits
            byteorder: Byte order

        Returns:
            Tuple of (value, bits_consumed)
        """
        byte_count = (self.bits + 7) // 8
        if len(data) < byte_count:
            raise ValueError(f"Insufficient data: need {byte_count}, got {len(data)}")

        # Extract the value
        value = int.from_bytes(data[:byte_count], "big", signed=False)

        # Mask to get only the relevant bits
        mask = (1 << self.bits) - 1
        value &= mask

        # Convert to signed if needed
        if self.signed and (value & (1 << (self.bits - 1))):
            value -= 1 << self.bits

        return value, self.bits  # Return bits consumed, not bytes


class BitPackingContext:
    """
    Context manager for packing/unpacking bits at single-bit resolution.

    This class handles the bit-level assembly and extraction for
    bitwise-encoded message partials and messages.
    """

    def __init__(self, byteorder: str = "big"):
        """
        Initialize bit packing context.

        Args:
            byteorder: Byte order for multi-byte values
        """
        self.byteorder = byteorder
        self.bit_buffer = 0
        self.bits_in_buffer = 0
        self.output = bytearray()

    def pack_bits(self, value: int, bit_count: int) -> None:
        """
        Pack a value with specified bit count into the buffer.

        Args:
            value: Integer value to pack
            bit_count: Number of bits to use
        """
        # Add bits to buffer
        self.bit_buffer = (self.bit_buffer << bit_count) | (
            value & ((1 << bit_count) - 1)
        )
        self.bits_in_buffer += bit_count

        # Flush complete bytes
        while self.bits_in_buffer >= 8:
            self.bits_in_buffer -= 8
            byte = (self.bit_buffer >> self.bits_in_buffer) & 0xFF
            self.output.append(byte)
            self.bit_buffer &= (1 << self.bits_in_buffer) - 1

    def flush(self) -> bytes:
        """
        Flush remaining bits to output, padding to byte boundary.

        Returns:
            Packed bytes
        """
        if self.bits_in_buffer > 0:
            # Pad with zeros and flush final byte
            byte = (self.bit_buffer << (8 - self.bits_in_buffer)) & 0xFF
            self.output.append(byte)
            self.bits_in_buffer = 0
            self.bit_buffer = 0

        result = bytes(self.output)
        self.output = bytearray()  # Reset output buffer
        return result


class BitUnpackingContext:
    """
    Context for unpacking bits at single-bit resolution.

    Handles bit-level extraction from byte streams.
    """

    def __init__(self, data: bytes, byteorder: str = "big"):
        """
        Initialize bit unpacking context.

        Args:
            data: Bytes to unpack
            byteorder: Byte order for multi-byte values
        """
        self.data = data
        self.byteorder = byteorder
        self.bit_buffer = 0
        self.bits_in_buffer = 0
        self.byte_offset = 0

    def unpack_bits(self, bit_count: int) -> int:
        """
        Unpack specified number of bits from the stream.

        Args:
            bit_count: Number of bits to extract

        Returns:
            Integer value
        """
        # Ensure we have enough bits
        while self.bits_in_buffer < bit_count:
            if self.byte_offset >= len(self.data):
                raise ValueError("Insufficient data for bit unpacking")

            # Load next byte
            self.bit_buffer = (self.bit_buffer << 8) | self.data[self.byte_offset]
            self.bits_in_buffer += 8
            self.byte_offset += 1

        # Extract the bits
        self.bits_in_buffer -= bit_count
        value = (self.bit_buffer >> self.bits_in_buffer) & ((1 << bit_count) - 1)
        self.bit_buffer &= (1 << self.bits_in_buffer) - 1

        return value

    def get_bytes_consumed(self) -> int:
        """
        Get total number of bytes consumed.

        Returns:
            Bytes consumed from input
        """
        return self.byte_offset


class MessagePartial(ABC):
    """
    Base class for message partial components with declarative field definitions.

    Supports arbitrary encoding schemes through custom encoders.

    Field specification options:
    - type: Built-in type string or MessagePartial class
    - encoder: Custom FieldEncoder instance
    - encode/decode: Custom encode/decode functions
    - enum: Enum class for enum types
    - size: Size parameter for certain encoders
    - numlist: Fixed array size
    - serializer: Serializer instance (BytesSerializer/JSONSerializer) for this field

    Examples:
        # Built-in types
        class Basic(MessagePartial):
            fields = {
                "name": {"type": "str"},
                "value": {"type": "int(32)"}
            }

        # Custom encoder
        class FixedPoint(MessagePartial):
            fields = {
                "price": {"type": "custom", "encoder": FixedPointEncoder(16, 16)}
            }

        # Enum type
        class StatusMsg(MessagePartial):
            fields = {
                "status": {"type": "enum", "enum": MyEnum, "size": 1}
            }

        # Custom encode/decode functions
        class CustomEncoding(MessagePartial):
            fields = {
                "data": {
                    "type": "custom",
                    "encode": lambda v, bo: custom_encode(v),
                    "decode": lambda d, bo: custom_decode(d)
                }
            }
    """

    encoding: Encoding = Encoding.BIG_ENDIAN
    fields: Dict[str, Dict[str, Any]] = {}
    bitwise: bool = False  # Set to True to enable bitwise packing

    def __init__(self, **kwargs):
        """Initialize with field values."""
        for field_name in self.fields:
            setattr(self, field_name, kwargs.get(field_name))

    def serialize_bytes(self) -> bytes:
        """
        Serialize this message partial to bytes based on field definitions.

        Supports both byte-aligned and bitwise encoding modes.

        Returns:
            Byte representation
        """
        byteorder = self.encoding.value

        # Check if this partial uses bitwise encoding
        if self.bitwise or self._has_bitwise_fields():
            return self._serialize_bitwise(byteorder)

        # Standard byte-aligned serialization
        result = b""

        for field_name, field_spec in self.fields.items():
            value = getattr(self, field_name)
            field_type = field_spec.get("type")

            # Handle fixed-size arrays
            if "numlist" in field_spec:
                if not isinstance(value, list):
                    raise ValueError(f"{field_name} must be a list")
                if len(value) != field_spec["numlist"]:
                    raise ValueError(
                        f"{field_name} must have {field_spec['numlist']} elements"
                    )
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

        # Handle nested MessagePartial
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
            fmt = "<f" if byteorder == "little" else ">f"
            return struct.pack(fmt, value)
        elif field_type == "double":
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
                # Flush current bits to byte boundary
                if context.bits_in_buffer > 0:
                    partial_bytes = context.flush()
                    context = BitPackingContext(byteorder)
                    # We need to accumulate this differently
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
    def deserialize_bytes(cls, data: bytes) -> Tuple["MessagePartial", int]:
        """
        Deserialize a message partial from bytes.

        Supports both byte-aligned and bitwise encoding modes.

        Args:
            data: Bytes to deserialize

        Returns:
            Tuple of (MessagePartial instance, bytes consumed)
        """
        byteorder = cls.encoding.value

        # Check if this partial uses bitwise encoding
        if cls.bitwise or cls._has_bitwise_fields_static():
            kwargs, bytes_consumed = cls._deserialize_bitwise(data, byteorder)
            return cls(**kwargs), bytes_consumed

        # Standard byte-aligned deserialization
        offset = 0
        kwargs = {}

        for field_name, field_spec in cls.fields.items():
            # Handle fixed-size arrays
            if "numlist" in field_spec:
                values = []
                for _ in range(field_spec["numlist"]):
                    value, consumed = cls._deserialize_value(
                        data[offset:], field_spec, byteorder
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
                        data[offset:], field_spec, byteorder
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
                        data[offset:], field_spec, byteorder
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
                                    data[offset:], field_spec, byteorder
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
                    data[offset:], field_spec, byteorder
                )
                kwargs[field_name] = value
                offset += consumed

        return cls(**kwargs), offset

    @classmethod
    def _deserialize_value(
        cls, data: bytes, field_spec: Dict[str, Any], byteorder: str
    ) -> Tuple[Any, int]:
        """Deserialize a single value based on field specification."""
        field_type = field_spec.get("type")

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
                from packerpy.protocols.message import Message

                value = serializer.deserialize(serialized_data, Message)

            if value is None:
                raise ValueError(f"Failed to deserialize field with serializer")
            return value, 4 + length

        # Custom encoder instance
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

        # Handle nested MessagePartial
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
            fmt = "<f" if byteorder == "little" else ">f"
            value = struct.unpack(fmt, data[0:4])[0]
            return value, 4
        elif field_type == "double":
            if len(data) < 8:
                raise ValueError(f"Insufficient data: need 8, got {len(data)}")
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
        Validate this message partial's data.

        Returns:
            True if valid
        """
        for field_name in self.fields:
            if not hasattr(self, field_name):
                return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert message partial to dictionary for JSON/XML serialization.

        Returns:
            Dictionary representation
        """
        result = {"type": self.__class__.__name__}
        for field_name, field_spec in self.fields.items():
            value = getattr(self, field_name)

            # Handle enums
            if isinstance(value, IntEnum):
                result[field_name] = {
                    "enum": value.__class__.__name__,
                    "value": value.value,
                }
            # Handle MessagePartial
            elif isinstance(value, MessagePartial):
                result[field_name] = value.to_dict()
            # Handle bytes - convert to list for JSON compatibility
            elif isinstance(value, bytes):
                result[field_name] = list(value)
            elif isinstance(value, list):
                result[field_name] = [
                    (
                        item.to_dict()
                        if isinstance(item, (MessagePartial, IntEnum))
                        else (
                            {"enum": item.__class__.__name__, "value": item.value}
                            if isinstance(item, IntEnum)
                            else item
                        )
                    )
                    for item in value
                ]
            else:
                result[field_name] = value
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MessagePartial":
        """
        Create message partial from dictionary.

        Args:
            data: Dictionary to deserialize

        Returns:
            MessagePartial instance
        """
        kwargs = {}
        for field_name, field_spec in cls.fields.items():
            if field_name not in data:
                continue

            value = data[field_name]
            field_type = field_spec.get("type")

            # Handle enum type
            if field_type == "enum" and isinstance(value, dict) and "value" in value:
                enum_class = field_spec.get("enum")
                if enum_class:
                    kwargs[field_name] = enum_class(value["value"])
                continue

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
