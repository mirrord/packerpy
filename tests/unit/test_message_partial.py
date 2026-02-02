"""Unit tests for protocols.message_partial module."""

import pytest
import struct
from enum import IntEnum

from packerpy.protocols.message_partial import (
    MessagePartial,
    Encoding,
    FieldEncoder,
    FixedPointEncoder,
    EnumEncoder,
    RunLengthEncoder,
    SevenBitASCIIEncoder,
    BitwiseEncoder,
    BitPackingContext,
    BitUnpackingContext,
)


# Test fixtures - define test MessagePartial classes
class SimplePartial(MessagePartial):
    """Simple test partial with basic types."""

    encoding = Encoding.BIG_ENDIAN
    fields = {
        "name": {"type": "str"},
        "value": {"type": "int(32)"},
    }


class ComplexPartial(MessagePartial):
    """Complex partial with multiple field types."""

    encoding = Encoding.BIG_ENDIAN
    fields = {
        "int_field": {"type": "int"},
        "str_field": {"type": "str"},
        "float_field": {"type": "float"},
        "bool_field": {"type": "bool"},
        "bytes_field": {"type": "bytes"},
    }


class StatusEnum(IntEnum):
    """Test enum."""

    IDLE = 0
    ACTIVE = 1
    ERROR = 2


class EnumPartial(MessagePartial):
    """Partial with enum field."""

    encoding = Encoding.BIG_ENDIAN
    fields = {
        "status": {"type": "enum", "enum": StatusEnum, "size": 1},
    }


class ArrayPartial(MessagePartial):
    """Partial with fixed array."""

    encoding = Encoding.BIG_ENDIAN
    fields = {
        "values": {"type": "int(16)", "numlist": 3},
    }


class NestedPartial(MessagePartial):
    """Partial with nested MessagePartial."""

    encoding = Encoding.BIG_ENDIAN
    fields = {
        "nested": {"type": SimplePartial},
    }


class BitwisePartial(MessagePartial):
    """Partial with bitwise fields."""

    encoding = Encoding.BIG_ENDIAN
    bitwise = True
    fields = {
        "flag_a": {"type": "bit", "bits": 1},
        "flag_b": {"type": "bit", "bits": 1},
        "counter": {"type": "bit", "bits": 6},
    }


class TestEncoding:
    """Test Encoding enum."""

    def test_encoding_values(self):
        """Test encoding enum values."""
        assert Encoding.LITTLE_ENDIAN.value == "little"
        assert Encoding.BIG_ENDIAN.value == "big"


class TestMessagePartialBasic:
    """Test basic MessagePartial functionality."""

    def test_initialization(self):
        """Test MessagePartial initialization."""
        partial = SimplePartial(name="test", value=42)
        assert partial.name == "test"
        assert partial.value == 42

    def test_initialization_partial_fields(self):
        """Test initialization with only some fields."""
        partial = SimplePartial(name="test")
        assert partial.name == "test"
        assert partial.value is None

    def test_serialize_simple_types(self):
        """Test serialization of simple types."""
        partial = SimplePartial(name="hello", value=100)
        result = partial.serialize_bytes()

        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_deserialize_simple_types(self):
        """Test deserialization of simple types."""
        original = SimplePartial(name="hello", value=100)
        serialized = original.serialize_bytes()

        deserialized, consumed = SimplePartial.deserialize_bytes(serialized)

        assert deserialized.name == "hello"
        assert deserialized.value == 100
        assert consumed == len(serialized)

    def test_round_trip_serialization(self):
        """Test round-trip serialization and deserialization."""
        original = SimplePartial(name="test", value=42)
        serialized = original.serialize_bytes()
        deserialized, _ = SimplePartial.deserialize_bytes(serialized)

        assert deserialized.name == original.name
        assert deserialized.value == original.value

    def test_validate_valid_partial(self):
        """Test validate returns True for valid partial."""
        partial = SimplePartial(name="test", value=42)
        assert partial.validate() is True

    def test_validate_missing_field(self):
        """Test validate returns False for missing field."""
        partial = SimplePartial()
        # Fields are None by default
        assert partial.validate() is True  # None is a valid value

    def test_to_dict(self):
        """Test conversion to dictionary."""
        partial = SimplePartial(name="test", value=42)
        result = partial.to_dict()

        assert isinstance(result, dict)
        assert result["type"] == "SimplePartial"
        assert result["name"] == "test"
        assert result["value"] == 42

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {"type": "SimplePartial", "name": "test", "value": 42}
        partial = SimplePartial.from_dict(data)

        assert partial.name == "test"
        assert partial.value == 42


class TestMessagePartialFieldTypes:
    """Test different field types."""

    def test_int_field(self):
        """Test int field serialization."""
        partial = ComplexPartial(
            int_field=12345,
            str_field="",
            float_field=0.0,
            bool_field=False,
            bytes_field=b"",
        )
        serialized = partial.serialize_bytes()
        deserialized, _ = ComplexPartial.deserialize_bytes(serialized)

        assert deserialized.int_field == 12345

    def test_str_field(self):
        """Test string field serialization."""
        partial = ComplexPartial(
            int_field=0,
            str_field="hello world",
            float_field=0.0,
            bool_field=False,
            bytes_field=b"",
        )
        serialized = partial.serialize_bytes()
        deserialized, _ = ComplexPartial.deserialize_bytes(serialized)

        assert deserialized.str_field == "hello world"

    def test_float_field(self):
        """Test float field serialization."""
        partial = ComplexPartial(
            int_field=0,
            str_field="",
            float_field=3.14,
            bool_field=False,
            bytes_field=b"",
        )
        serialized = partial.serialize_bytes()
        deserialized, _ = ComplexPartial.deserialize_bytes(serialized)

        assert abs(deserialized.float_field - 3.14) < 0.001

    def test_bool_field(self):
        """Test boolean field serialization."""
        partial = ComplexPartial(
            int_field=0, str_field="", float_field=0.0, bool_field=True, bytes_field=b""
        )
        serialized = partial.serialize_bytes()
        deserialized, _ = ComplexPartial.deserialize_bytes(serialized)

        assert deserialized.bool_field is True

    def test_bytes_field(self):
        """Test bytes field serialization."""
        data = b"\x00\x01\x02\x03"
        partial = ComplexPartial(
            int_field=0,
            str_field="",
            float_field=0.0,
            bool_field=False,
            bytes_field=data,
        )
        serialized = partial.serialize_bytes()
        deserialized, _ = ComplexPartial.deserialize_bytes(serialized)

        assert deserialized.bytes_field == data

    def test_sized_int(self):
        """Test sized integer types."""

        class SizedIntPartial(MessagePartial):
            fields = {
                "int8": {"type": "int(8)"},
                "int16": {"type": "int(16)"},
                "int32": {"type": "int(32)"},
                "int64": {"type": "int(64)"},
            }

        partial = SizedIntPartial(
            int8=127, int16=32767, int32=2147483647, int64=9223372036854775807
        )
        serialized = partial.serialize_bytes()
        deserialized, _ = SizedIntPartial.deserialize_bytes(serialized)

        assert deserialized.int8 == 127
        assert deserialized.int16 == 32767
        assert deserialized.int32 == 2147483647
        assert deserialized.int64 == 9223372036854775807

    def test_unsigned_int(self):
        """Test unsigned integer types."""

        class UnsignedPartial(MessagePartial):
            fields = {
                "uint8": {"type": "uint(8)"},
                "uint16": {"type": "uint(16)"},
                "uint32": {"type": "uint(32)"},
            }

        partial = UnsignedPartial(uint8=255, uint16=65535, uint32=4294967295)
        serialized = partial.serialize_bytes()
        deserialized, _ = UnsignedPartial.deserialize_bytes(serialized)

        assert deserialized.uint8 == 255
        assert deserialized.uint16 == 65535
        assert deserialized.uint32 == 4294967295

    def test_double_field(self):
        """Test double precision float."""

        class DoublePartial(MessagePartial):
            fields = {"value": {"type": "double"}}

        partial = DoublePartial(value=3.141592653589793)
        serialized = partial.serialize_bytes()
        deserialized, _ = DoublePartial.deserialize_bytes(serialized)

        assert abs(deserialized.value - 3.141592653589793) < 1e-10


class TestMessagePartialEncodings:
    """Test different byte order encodings."""

    def test_big_endian_encoding(self):
        """Test big endian encoding."""

        class BigEndianPartial(MessagePartial):
            encoding = Encoding.BIG_ENDIAN
            fields = {"value": {"type": "int(32)"}}

        partial = BigEndianPartial(value=0x12345678)
        serialized = partial.serialize_bytes()

        # Big endian: most significant byte first
        assert serialized == b"\x12\x34\x56\x78"

    def test_little_endian_encoding(self):
        """Test little endian encoding."""

        class LittleEndianPartial(MessagePartial):
            encoding = Encoding.LITTLE_ENDIAN
            fields = {"value": {"type": "int(32)"}}

        partial = LittleEndianPartial(value=0x12345678)
        serialized = partial.serialize_bytes()

        # Little endian: least significant byte first
        assert serialized == b"\x78\x56\x34\x12"


class TestMessagePartialArrays:
    """Test array field types."""

    def test_fixed_array(self):
        """Test fixed-size array."""
        partial = ArrayPartial(values=[10, 20, 30])
        serialized = partial.serialize_bytes()
        deserialized, _ = ArrayPartial.deserialize_bytes(serialized)

        assert deserialized.values == [10, 20, 30]

    def test_fixed_array_wrong_size_raises_error(self):
        """Test fixed array with wrong size raises error."""
        partial = ArrayPartial(values=[10, 20])  # Should be 3 elements

        with pytest.raises(ValueError, match="must have 3 elements"):
            partial.serialize_bytes()

    def test_fixed_array_not_list_raises_error(self):
        """Test fixed array with non-list raises error."""
        partial = ArrayPartial(values=42)

        with pytest.raises(ValueError, match="must be a list"):
            partial.serialize_bytes()

    def test_dynamic_array(self):
        """Test dynamic array with length prefix."""

        class DynamicArrayPartial(MessagePartial):
            fields = {"values": {"type": "int(16)", "dynamic_array": True}}

        partial = DynamicArrayPartial(values=[1, 2, 3, 4, 5])
        serialized = partial.serialize_bytes()
        deserialized, _ = DynamicArrayPartial.deserialize_bytes(serialized)

        assert deserialized.values == [1, 2, 3, 4, 5]


class TestMessagePartialNested:
    """Test nested MessagePartial."""

    def test_nested_partial(self):
        """Test nested MessagePartial serialization."""
        inner = SimplePartial(name="inner", value=99)
        outer = NestedPartial(nested=inner)

        serialized = outer.serialize_bytes()
        deserialized, _ = NestedPartial.deserialize_bytes(serialized)

        assert deserialized.nested.name == "inner"
        assert deserialized.nested.value == 99

    def test_nested_partial_to_dict(self):
        """Test nested partial to_dict."""
        inner = SimplePartial(name="inner", value=99)
        outer = NestedPartial(nested=inner)

        result = outer.to_dict()

        assert result["type"] == "NestedPartial"
        assert result["nested"]["type"] == "SimplePartial"
        assert result["nested"]["name"] == "inner"
        assert result["nested"]["value"] == 99

    def test_nested_partial_from_dict(self):
        """Test nested partial from_dict."""
        data = {
            "type": "NestedPartial",
            "nested": {"type": "SimplePartial", "name": "inner", "value": 99},
        }

        partial = NestedPartial.from_dict(data)

        assert partial.nested.name == "inner"
        assert partial.nested.value == 99


class TestFixedPointEncoder:
    """Test FixedPointEncoder."""

    def test_encode_decode(self):
        """Test fixed-point encoding and decoding."""
        encoder = FixedPointEncoder(16, 16)
        value = 123.456

        encoded = encoder.encode(value, "big")
        decoded, consumed = encoder.decode(encoded, "big")

        assert abs(decoded - value) < 0.01
        assert consumed == 4  # 32 bits = 4 bytes

    def test_different_precision(self):
        """Test different fixed-point precisions."""
        encoder = FixedPointEncoder(8, 24)
        value = 123.456789

        encoded = encoder.encode(value, "big")
        decoded, _ = encoder.decode(encoded, "big")

        assert abs(decoded - value) < 0.001

    def test_negative_values(self):
        """Test negative fixed-point values."""
        encoder = FixedPointEncoder(16, 16, signed=True)
        value = -50.25

        encoded = encoder.encode(value, "big")
        decoded, _ = encoder.decode(encoded, "big")

        assert abs(decoded - value) < 0.01

    def test_value_out_of_range(self):
        """Test value out of range raises error."""
        encoder = FixedPointEncoder(8, 8, signed=False)
        value = 300.0  # Too large for 8.8 unsigned

        with pytest.raises(ValueError, match="out of range"):
            encoder.encode(value, "big")


class TestEnumEncoder:
    """Test EnumEncoder."""

    def test_encode_decode_enum(self):
        """Test enum encoding and decoding."""
        encoder = EnumEncoder(StatusEnum, size=1)

        encoded = encoder.encode(StatusEnum.ACTIVE, "big")
        decoded, consumed = encoder.decode(encoded, "big")

        assert decoded == StatusEnum.ACTIVE
        assert consumed == 1

    def test_encode_int_value(self):
        """Test encoding integer value of enum."""
        encoder = EnumEncoder(StatusEnum, size=1)

        encoded = encoder.encode(1, "big")
        decoded, _ = encoder.decode(encoded, "big")

        assert decoded == StatusEnum.ACTIVE

    def test_different_sizes(self):
        """Test different enum sizes."""
        encoder = EnumEncoder(StatusEnum, size=2)

        encoded = encoder.encode(StatusEnum.ERROR, "big")
        decoded, consumed = encoder.decode(encoded, "big")

        assert decoded == StatusEnum.ERROR
        assert consumed == 2

    def test_enum_partial(self):
        """Test MessagePartial with enum field."""
        partial = EnumPartial(status=StatusEnum.ACTIVE)
        serialized = partial.serialize_bytes()
        deserialized, _ = EnumPartial.deserialize_bytes(serialized)

        assert deserialized.status == StatusEnum.ACTIVE


class TestRunLengthEncoder:
    """Test RunLengthEncoder."""

    def test_encode_decode_repeated_data(self):
        """Test run-length encoding of repeated data."""
        encoder = RunLengthEncoder()
        data = b"\x00" * 10 + b"\xff" * 5

        encoded = encoder.encode(data, "big")
        decoded, _ = encoder.decode(encoded, "big")

        assert decoded == data

    def test_encode_empty_data(self):
        """Test encoding empty data."""
        encoder = RunLengthEncoder()
        data = b""

        encoded = encoder.encode(data, "big")
        decoded, _ = encoder.decode(encoded, "big")

        assert decoded == data

    def test_encode_no_repeats(self):
        """Test encoding data with no repeats."""
        encoder = RunLengthEncoder()
        data = b"\x00\x01\x02\x03\x04"

        encoded = encoder.encode(data, "big")
        decoded, _ = encoder.decode(encoded, "big")

        assert decoded == data


class TestSevenBitASCIIEncoder:
    """Test SevenBitASCIIEncoder."""

    def test_encode_decode_ascii(self):
        """Test 7-bit ASCII encoding."""
        encoder = SevenBitASCIIEncoder()
        text = "Hello"

        encoded = encoder.encode(text, "big")
        decoded, _ = encoder.decode(encoded, "big")

        assert decoded == text

    def test_packing_efficiency(self):
        """Test that 8 chars pack into 7 bytes."""
        encoder = SevenBitASCIIEncoder()
        text = "12345678"  # 8 characters

        encoded = encoder.encode(text, "big")
        # Should be 2 bytes (length) + 7 bytes (packed data) = 9 bytes
        assert len(encoded) == 2 + 7

    def test_empty_string(self):
        """Test encoding empty string."""
        encoder = SevenBitASCIIEncoder()
        text = ""

        encoded = encoder.encode(text, "big")
        decoded, _ = encoder.decode(encoded, "big")

        assert decoded == text


class TestBitwiseEncoder:
    """Test BitwiseEncoder."""

    def test_encode_decode_bits(self):
        """Test bitwise encoding and decoding."""
        encoder = BitwiseEncoder(4, signed=False)
        value = 15  # 0b1111

        encoded = encoder.encode(value, "big")
        decoded, bits_consumed = encoder.decode(encoded, "big")

        assert decoded == value
        assert bits_consumed == 4

    def test_value_out_of_range(self):
        """Test value out of range raises error."""
        encoder = BitwiseEncoder(4, signed=False)
        value = 16  # Too large for 4 bits (max is 15)

        with pytest.raises(ValueError, match="out of range"):
            encoder.encode(value, "big")

    def test_signed_bitwise(self):
        """Test signed bitwise encoding."""
        encoder = BitwiseEncoder(4, signed=True)
        value = -5

        encoded = encoder.encode(value, "big")
        decoded, _ = encoder.decode(encoded, "big")

        assert decoded == value


class TestBitPackingContext:
    """Test BitPackingContext."""

    def test_pack_single_byte(self):
        """Test packing bits that fit in one byte."""
        context = BitPackingContext("big")
        context.pack_bits(0b1010, 4)
        context.pack_bits(0b1100, 4)

        result = context.flush()

        assert result == b"\xac"  # 0b10101100

    def test_pack_multiple_bytes(self):
        """Test packing bits across multiple bytes."""
        context = BitPackingContext("big")
        context.pack_bits(0xFF, 8)
        context.pack_bits(0xFF, 8)

        result = context.flush()

        assert result == b"\xff\xff"

    def test_pack_with_padding(self):
        """Test packing with padding to byte boundary."""
        context = BitPackingContext("big")
        context.pack_bits(0b111, 3)

        result = context.flush()

        # 0b111 padded to byte: 0b11100000
        assert result == b"\xe0"

    def test_flush_resets_buffer(self):
        """Test that flush resets the buffer."""
        context = BitPackingContext("big")
        context.pack_bits(0xFF, 8)

        result1 = context.flush()
        result2 = context.flush()

        assert result1 == b"\xff"
        assert result2 == b""


class TestBitUnpackingContext:
    """Test BitUnpackingContext."""

    def test_unpack_single_byte(self):
        """Test unpacking bits from one byte."""
        data = b"\xac"  # 0b10101100
        context = BitUnpackingContext(data, "big")

        value1 = context.unpack_bits(4)
        value2 = context.unpack_bits(4)

        assert value1 == 0b1010
        assert value2 == 0b1100

    def test_unpack_multiple_bytes(self):
        """Test unpacking bits across multiple bytes."""
        data = b"\xff\xff"
        context = BitUnpackingContext(data, "big")

        value1 = context.unpack_bits(8)
        value2 = context.unpack_bits(8)

        assert value1 == 0xFF
        assert value2 == 0xFF

    def test_unpack_insufficient_data(self):
        """Test unpacking with insufficient data raises error."""
        data = b"\xff"
        context = BitUnpackingContext(data, "big")

        context.unpack_bits(8)

        with pytest.raises(ValueError, match="Insufficient data"):
            context.unpack_bits(8)

    def test_get_bytes_consumed(self):
        """Test tracking bytes consumed."""
        data = b"\xff\xff\xff"
        context = BitUnpackingContext(data, "big")

        context.unpack_bits(16)

        assert context.get_bytes_consumed() == 2


class TestBitwisePartial:
    """Test MessagePartial with bitwise encoding."""

    def test_bitwise_serialization(self):
        """Test bitwise field serialization."""
        partial = BitwisePartial(flag_a=1, flag_b=0, counter=30)
        serialized = partial.serialize_bytes()

        # Should pack into 1 byte: 1 + 0 + 30 = 0b10011110 = 0x9e
        assert len(serialized) == 1
        assert serialized == b"\x9e"

    def test_bitwise_deserialization(self):
        """Test bitwise field deserialization."""
        data = b"\x9e"  # 0b10011110
        deserialized, consumed = BitwisePartial.deserialize_bytes(data)

        assert deserialized.flag_a == 1
        assert deserialized.flag_b == 0
        assert deserialized.counter == 30
        assert consumed == 1

    def test_bitwise_round_trip(self):
        """Test bitwise round-trip serialization."""
        original = BitwisePartial(flag_a=1, flag_b=1, counter=15)
        serialized = original.serialize_bytes()
        deserialized, _ = BitwisePartial.deserialize_bytes(serialized)

        assert deserialized.flag_a == original.flag_a
        assert deserialized.flag_b == original.flag_b
        assert deserialized.counter == original.counter

    def test_bitwise_value_out_of_range(self):
        """Test bitwise value out of range raises error."""
        partial = BitwisePartial(
            flag_a=1, flag_b=0, counter=70
        )  # counter max is 63 (6 bits)

        with pytest.raises(ValueError, match="out of range"):
            partial.serialize_bytes()


class TestMessagePartialEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_string(self):
        """Test serialization of empty string."""
        partial = SimplePartial(name="", value=0)
        serialized = partial.serialize_bytes()
        deserialized, _ = SimplePartial.deserialize_bytes(serialized)

        assert deserialized.name == ""

    def test_empty_bytes(self):
        """Test serialization of empty bytes."""
        partial = ComplexPartial(
            int_field=0,
            str_field="",
            float_field=0.0,
            bool_field=False,
            bytes_field=b"",
        )
        serialized = partial.serialize_bytes()
        deserialized, _ = ComplexPartial.deserialize_bytes(serialized)

        assert deserialized.bytes_field == b""

    def test_large_string(self):
        """Test serialization of large string."""
        large_str = "x" * 10000
        partial = SimplePartial(name=large_str, value=0)
        serialized = partial.serialize_bytes()
        deserialized, _ = SimplePartial.deserialize_bytes(serialized)

        assert deserialized.name == large_str

    def test_insufficient_data_for_deserialization(self):
        """Test deserialization with insufficient data."""
        data = b"\x00\x00\x00"  # Too short

        with pytest.raises(ValueError):
            SimplePartial.deserialize_bytes(data)

    def test_unicode_string(self):
        """Test serialization of unicode string."""
        partial = SimplePartial(name="Hello 世界 🌍", value=42)
        serialized = partial.serialize_bytes()
        deserialized, _ = SimplePartial.deserialize_bytes(serialized)

        assert deserialized.name == "Hello 世界 🌍"
