"""Unit tests for protocols.message module."""

import pytest
from enum import IntEnum

from packerpy.protocols.message import Message, TemperatureMessage, StatusMessage
from packerpy.protocols.message_partial import MessagePartial, Encoding


# Test fixtures
class SimpleMessage(Message):
    """Simple test message."""

    encoding = Encoding.BIG_ENDIAN
    fields = {
        "id": {"type": "int(32)"},
        "text": {"type": "str"},
    }


class TestMessageBasic:
    """Test basic Message functionality."""

    def test_initialization(self):
        """Test Message initialization."""
        msg = SimpleMessage(id=1, text="hello")
        assert msg.id == 1
        assert msg.text == "hello"

    def test_serialize_bytes(self):
        """Test message serialization."""
        msg = SimpleMessage(id=42, text="test")
        result = msg.serialize_bytes()

        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_deserialize_bytes(self):
        """Test message deserialization."""
        original = SimpleMessage(id=42, text="test")
        serialized = original.serialize_bytes()

        deserialized, consumed = SimpleMessage.deserialize_bytes(serialized)

        assert deserialized.id == 42
        assert deserialized.text == "test"
        assert consumed == len(serialized)

    def test_round_trip(self):
        """Test round-trip serialization."""
        original = SimpleMessage(id=123, text="round trip")
        serialized = original.serialize_bytes()
        deserialized, _ = SimpleMessage.deserialize_bytes(serialized)

        assert deserialized.id == original.id
        assert deserialized.text == original.text

    def test_validate(self):
        """Test message validation."""
        msg = SimpleMessage(id=1, text="test")
        assert msg.validate() is True

    def test_to_dict(self):
        """Test conversion to dictionary."""
        msg = SimpleMessage(id=1, text="test")
        result = msg.to_dict()

        assert result["type"] == "SimpleMessage"
        assert result["id"] == 1
        assert result["text"] == "test"

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {"type": "SimpleMessage", "id": 1, "text": "test"}
        msg = SimpleMessage.from_dict(data)

        assert msg.id == 1
        assert msg.text == "test"

    def test_repr(self):
        """Test string representation."""
        msg = SimpleMessage(id=1, text="test")
        repr_str = repr(msg)

        assert "SimpleMessage" in repr_str
        assert "id=1" in repr_str
        assert "text='test'" in repr_str


class TestTemperatureMessage:
    """Test the example TemperatureMessage."""

    def test_temperature_message_creation(self):
        """Test creating a temperature message."""
        msg = TemperatureMessage(
            sensor_id="sensor_01", temperature=23.5, timestamp=1234567890
        )

        assert msg.sensor_id == "sensor_01"
        assert msg.temperature == 23.5
        assert msg.timestamp == 1234567890

    def test_temperature_message_serialization(self):
        """Test temperature message serialization."""
        msg = TemperatureMessage(
            sensor_id="sensor_01", temperature=23.5, timestamp=1234567890
        )

        serialized = msg.serialize_bytes()
        deserialized, _ = TemperatureMessage.deserialize_bytes(serialized)

        assert deserialized.sensor_id == "sensor_01"
        assert abs(deserialized.temperature - 23.5) < 0.01
        assert deserialized.timestamp == 1234567890

    def test_temperature_message_encoding(self):
        """Test temperature message uses big endian."""
        assert TemperatureMessage.encoding == Encoding.BIG_ENDIAN

    def test_temperature_message_fields(self):
        """Test temperature message field definitions."""
        assert "sensor_id" in TemperatureMessage.fields
        assert "temperature" in TemperatureMessage.fields
        assert "timestamp" in TemperatureMessage.fields

        assert TemperatureMessage.fields["sensor_id"]["type"] == "str"
        assert TemperatureMessage.fields["temperature"]["type"] == "float"
        assert TemperatureMessage.fields["timestamp"]["type"] == "int(64)"


class TestMessageFieldTypes:
    """Test various field types in messages."""

    def test_all_basic_types(self):
        """Test message with all basic field types."""

        class AllTypesMessage(Message):
            fields = {
                "int_val": {"type": "int"},
                "str_val": {"type": "str"},
                "float_val": {"type": "float"},
                "double_val": {"type": "double"},
                "bool_val": {"type": "bool"},
                "bytes_val": {"type": "bytes"},
            }

        msg = AllTypesMessage(
            int_val=42,
            str_val="test",
            float_val=3.14,
            double_val=2.718281828,
            bool_val=True,
            bytes_val=b"\x00\x01",
        )

        serialized = msg.serialize_bytes()
        deserialized, _ = AllTypesMessage.deserialize_bytes(serialized)

        assert deserialized.int_val == 42
        assert deserialized.str_val == "test"
        assert abs(deserialized.float_val - 3.14) < 0.01
        assert abs(deserialized.double_val - 2.718281828) < 1e-9
        assert deserialized.bool_val is True
        assert deserialized.bytes_val == b"\x00\x01"

    def test_sized_integers(self):
        """Test sized integer types."""

        class SizedIntMessage(Message):
            fields = {
                "int8": {"type": "int(8)"},
                "int16": {"type": "int(16)"},
                "int32": {"type": "int(32)"},
                "int64": {"type": "int(64)"},
            }

        msg = SizedIntMessage(
            int8=127, int16=32767, int32=2147483647, int64=9223372036854775807
        )
        serialized = msg.serialize_bytes()
        deserialized, _ = SizedIntMessage.deserialize_bytes(serialized)

        assert deserialized.int8 == 127
        assert deserialized.int16 == 32767
        assert deserialized.int32 == 2147483647
        assert deserialized.int64 == 9223372036854775807

    def test_unsigned_integers(self):
        """Test unsigned integer types."""

        class UnsignedMessage(Message):
            fields = {
                "uint8": {"type": "uint(8)"},
                "uint16": {"type": "uint(16)"},
                "uint32": {"type": "uint(32)"},
            }

        msg = UnsignedMessage(uint8=255, uint16=65535, uint32=4294967295)
        serialized = msg.serialize_bytes()
        deserialized, _ = UnsignedMessage.deserialize_bytes(serialized)

        assert deserialized.uint8 == 255
        assert deserialized.uint16 == 65535
        assert deserialized.uint32 == 4294967295


class TestMessageArrays:
    """Test array fields in messages."""

    def test_fixed_array(self):
        """Test fixed-size arrays."""

        class FixedArrayMessage(Message):
            fields = {"values": {"type": "int(16)", "numlist": 3}}

        msg = FixedArrayMessage(values=[10, 20, 30])
        serialized = msg.serialize_bytes()
        deserialized, _ = FixedArrayMessage.deserialize_bytes(serialized)

        assert deserialized.values == [10, 20, 30]

    def test_dynamic_array(self):
        """Test dynamic arrays with length prefix."""

        class DynamicArrayMessage(Message):
            fields = {"values": {"type": "int(32)", "dynamic_array": True}}

        msg = DynamicArrayMessage(values=[1, 2, 3, 4, 5])
        serialized = msg.serialize_bytes()
        deserialized, _ = DynamicArrayMessage.deserialize_bytes(serialized)

        assert deserialized.values == [1, 2, 3, 4, 5]


class TestMessageNested:
    """Test nested MessagePartial in messages."""

    def test_nested_partial(self):
        """Test message with nested MessagePartial."""

        class InnerPartial(MessagePartial):
            fields = {"value": {"type": "int(32)"}}

        class OuterMessage(Message):
            fields = {"id": {"type": "int(32)"}, "data": {"type": InnerPartial}}

        inner = InnerPartial(value=42)
        msg = OuterMessage(id=1, data=inner)

        serialized = msg.serialize_bytes()
        deserialized, _ = OuterMessage.deserialize_bytes(serialized)

        assert deserialized.id == 1
        assert deserialized.data.value == 42


class TestMessageBitwise:
    """Test bitwise encoding in messages."""

    def test_bitwise_message(self):
        """Test message with bitwise fields."""

        class BitwiseMessage(Message):
            bitwise = True
            fields = {
                "flag_a": {"type": "bit", "bits": 1},
                "flag_b": {"type": "bit", "bits": 1},
                "counter": {"type": "bit", "bits": 6},
            }

        msg = BitwiseMessage(flag_a=1, flag_b=0, counter=30)
        serialized = msg.serialize_bytes()

        assert len(serialized) == 1

        deserialized, _ = BitwiseMessage.deserialize_bytes(serialized)
        assert deserialized.flag_a == 1
        assert deserialized.flag_b == 0
        assert deserialized.counter == 30


class TestMessageEncodings:
    """Test different byte order encodings."""

    def test_big_endian(self):
        """Test big endian encoding."""

        class BigEndianMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"value": {"type": "int(32)"}}

        msg = BigEndianMessage(value=0x12345678)
        serialized = msg.serialize_bytes()

        assert serialized == b"\x12\x34\x56\x78"

    def test_little_endian(self):
        """Test little endian encoding."""

        class LittleEndianMessage(Message):
            encoding = Encoding.LITTLE_ENDIAN
            fields = {"value": {"type": "int(32)"}}

        msg = LittleEndianMessage(value=0x12345678)
        serialized = msg.serialize_bytes()

        assert serialized == b"\x78\x56\x34\x12"


class TestMessageEnums:
    """Test enum fields in messages."""

    def test_enum_field(self):
        """Test message with enum field."""

        class Status(IntEnum):
            IDLE = 0
            ACTIVE = 1
            ERROR = 2

        class EnumMessage(Message):
            fields = {"status": {"type": "enum", "enum": Status, "size": 1}}

        msg = EnumMessage(status=Status.ACTIVE)
        serialized = msg.serialize_bytes()
        deserialized, _ = EnumMessage.deserialize_bytes(serialized)

        assert deserialized.status == Status.ACTIVE


class TestMessageEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_string(self):
        """Test message with empty string."""
        msg = SimpleMessage(id=1, text="")
        serialized = msg.serialize_bytes()
        deserialized, _ = SimpleMessage.deserialize_bytes(serialized)

        assert deserialized.text == ""

    def test_large_string(self):
        """Test message with large string."""
        large_text = "x" * 10000
        msg = SimpleMessage(id=1, text=large_text)
        serialized = msg.serialize_bytes()
        deserialized, _ = SimpleMessage.deserialize_bytes(serialized)

        assert deserialized.text == large_text

    def test_unicode_string(self):
        """Test message with unicode string."""
        msg = SimpleMessage(id=1, text="Hello 世界 🌍")
        serialized = msg.serialize_bytes()
        deserialized, _ = SimpleMessage.deserialize_bytes(serialized)

        assert deserialized.text == "Hello 世界 🌍"

    def test_zero_values(self):
        """Test message with zero values."""
        msg = SimpleMessage(id=0, text="")
        serialized = msg.serialize_bytes()
        deserialized, _ = SimpleMessage.deserialize_bytes(serialized)

        assert deserialized.id == 0
        assert deserialized.text == ""

    def test_insufficient_data(self):
        """Test deserialization with insufficient data."""
        with pytest.raises(ValueError):
            SimpleMessage.deserialize_bytes(b"\x00\x00")

    def test_bytes_field_conversion_in_dict(self):
        """Test that bytes are converted to list in to_dict."""

        class BytesMessage(Message):
            fields = {"data": {"type": "bytes"}}

        msg = BytesMessage(data=b"\x00\x01\x02")
        result = msg.to_dict()

        assert result["data"] == [0, 1, 2]

    def test_bytes_field_from_dict(self):
        """Test creating message from dict with bytes as list."""

        class BytesMessage(Message):
            fields = {"data": {"type": "bytes"}}

        data = {"type": "BytesMessage", "data": [0, 1, 2]}
        msg = BytesMessage.from_dict(data)

        assert msg.data == b"\x00\x01\x02"


class TestMessageValidation:
    """Test message validation."""

    def test_valid_message(self):
        """Test validation of valid message."""
        msg = SimpleMessage(id=1, text="test")
        assert msg.validate() is True

    def test_message_with_none_values(self):
        """Test that None values are still considered valid."""
        msg = SimpleMessage(id=None, text=None)
        # None is a valid value for fields
        assert msg.validate() is True


class TestMessageInheritance:
    """Test Message inheritance patterns."""

    def test_message_inherits_from_abstract_base(self):
        """Test that Message is abstract."""
        from abc import ABC

        assert issubclass(Message, ABC)

    def test_custom_message_subclass(self):
        """Test creating custom message subclass."""

        class CustomMessage(Message):
            fields = {"custom_field": {"type": "str"}}

        msg = CustomMessage(custom_field="custom")
        assert msg.custom_field == "custom"

        serialized = msg.serialize_bytes()
        deserialized, _ = CustomMessage.deserialize_bytes(serialized)
        assert deserialized.custom_field == "custom"
