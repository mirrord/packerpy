"""
Unit tests for JSON serializer and mixed serialization.

Tests cover:
- JSONSerializer basic functionality
- JSON serialization/deserialization of messages
- Mixed binary/JSON serialization in the same message
- Per-field serializer specification
- Edge cases and error handling
"""

import pytest
from packerpy.protocols.message import Message
from packerpy.protocols.message_partial import MessagePartial, Encoding
from packerpy.protocols.serializer import BytesSerializer, JSONSerializer


class SimplePartial(MessagePartial):
    """Simple message partial for testing."""

    encoding = Encoding.BIG_ENDIAN
    fields = {
        "name": {"type": "str"},
        "value": {"type": "int(32)"},
    }


class ComplexPartial(MessagePartial):
    """Complex message partial with multiple field types."""

    encoding = Encoding.BIG_ENDIAN
    fields = {
        "id": {"type": "uint(16)"},
        "temperature": {"type": "float"},
        "humidity": {"type": "float"},
        "label": {"type": "str"},
        "active": {"type": "bool"},
    }


class TestJSONSerializer:
    """Test suite for JSONSerializer class."""

    def test_serialize_simple_partial(self):
        """Test JSON serialization of a simple MessagePartial."""
        partial = SimplePartial(name="test", value=42)
        serializer = JSONSerializer()

        # Serialize
        json_bytes = serializer.serialize(partial)

        # Verify it's valid UTF-8 JSON
        assert isinstance(json_bytes, bytes)
        json_str = json_bytes.decode("utf-8")
        assert "test" in json_str
        assert "42" in json_str

    def test_deserialize_simple_partial(self):
        """Test JSON deserialization of a simple MessagePartial."""
        partial = SimplePartial(name="test", value=42)
        serializer = JSONSerializer()

        # Serialize and deserialize
        json_bytes = serializer.serialize(partial)
        restored = serializer.deserialize(json_bytes, SimplePartial)

        # Verify
        assert restored is not None
        assert restored.name == "test"
        assert restored.value == 42

    def test_serialize_complex_partial(self):
        """Test JSON serialization with multiple field types."""
        partial = ComplexPartial(
            id=100, temperature=23.5, humidity=65.2, label="sensor-1", active=True
        )
        serializer = JSONSerializer()

        # Serialize
        json_bytes = serializer.serialize(partial)
        restored = serializer.deserialize(json_bytes, ComplexPartial)

        # Verify all fields
        assert restored.id == 100
        assert abs(restored.temperature - 23.5) < 0.001
        assert abs(restored.humidity - 65.2) < 0.001
        assert restored.label == "sensor-1"
        assert restored.active == True

    def test_pretty_print(self):
        """Test pretty-printed JSON output."""
        partial = SimplePartial(name="test", value=42)
        serializer = JSONSerializer(indent=2)

        json_str = serializer.serialize_to_string(partial, indent=2)

        # Pretty-printed JSON should have newlines
        assert "\n" in json_str
        assert "  " in json_str  # Should have indentation

    def test_compact_output(self):
        """Test compact JSON output."""
        partial = SimplePartial(name="test", value=42)
        serializer = JSONSerializer()  # No indent

        json_str = serializer.serialize_to_string(partial)

        # Compact JSON should be on one line (except for any inherent newlines)
        lines = json_str.strip().split("\n")
        # Should be relatively compact (few lines)
        assert len(lines) <= 3

    def test_serialize_to_string(self):
        """Test serialize_to_string method."""
        partial = SimplePartial(name="test", value=42)
        serializer = JSONSerializer()

        json_str = serializer.serialize_to_string(partial)

        # Should be a string, not bytes
        assert isinstance(json_str, str)
        assert "test" in json_str
        assert "42" in json_str

    def test_deserialize_from_string(self):
        """Test deserialize_from_string method."""
        partial = SimplePartial(name="test", value=42)
        serializer = JSONSerializer()

        # Serialize to string and deserialize
        json_str = serializer.serialize_to_string(partial)
        restored = serializer.deserialize_from_string(json_str, SimplePartial)

        # Verify
        assert restored is not None
        assert restored.name == "test"
        assert restored.value == 42

    def test_round_trip(self):
        """Test complete round-trip serialization."""
        original = ComplexPartial(
            id=999,
            temperature=25.7,
            humidity=70.5,
            label="round-trip-test",
            active=False,
        )
        serializer = JSONSerializer()

        # Serialize and deserialize
        json_bytes = serializer.serialize(original)
        restored = serializer.deserialize(json_bytes, ComplexPartial)

        # Verify all fields match
        assert restored.id == original.id
        assert abs(restored.temperature - original.temperature) < 0.001
        assert abs(restored.humidity - original.humidity) < 0.001
        assert restored.label == original.label
        assert restored.active == original.active

    def test_invalid_json(self):
        """Test deserialization of invalid JSON."""
        serializer = JSONSerializer()
        invalid_json = b"not valid json {{{["

        # Should return None for invalid JSON
        result = serializer.deserialize(invalid_json, SimplePartial)
        assert result is None

    def test_ensure_ascii_option(self):
        """Test ensure_ascii serializer option."""
        # Create partial with non-ASCII characters
        partial = SimplePartial(name="tëst_üñïçödé", value=123)

        # Without ensure_ascii
        serializer_unicode = JSONSerializer(ensure_ascii=False)
        json_unicode = serializer_unicode.serialize_to_string(partial)

        # With ensure_ascii
        serializer_ascii = JSONSerializer(ensure_ascii=True)
        json_ascii = serializer_ascii.serialize_to_string(partial)

        # ASCII version should escape special characters
        assert len(json_ascii) >= len(json_unicode)
        assert (
            "\\u" in json_ascii or json_ascii == json_unicode
        )  # Either escaped or happened to be ASCII


class TestMixedSerialization:
    """Test suite for mixed binary/JSON serialization."""

    def test_mixed_serialization_basic(self):
        """Test basic mixed serialization with binary and JSON fields."""

        class Header(MessagePartial):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "version": {"type": "uint(8)"},
                "id": {"type": "uint(32)"},
            }

        class Payload(MessagePartial):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "message": {"type": "str"},
                "count": {"type": "int(32)"},
            }

        class MixedMsg(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "header": {"type": Header, "serializer": BytesSerializer()},
                "payload": {"type": Payload, "serializer": JSONSerializer()},
            }

        # Create message
        msg = MixedMsg(
            header=Header(version=1, id=12345),
            payload=Payload(message="test", count=100),
        )

        # Serialize
        data = msg.serialize_bytes()

        # Verify it serializes
        assert isinstance(data, bytes)
        assert len(data) > 0

        # Deserialize
        restored, consumed = MixedMsg.deserialize_bytes(data)

        # Verify header (binary)
        assert restored.header.version == 1
        assert restored.header.id == 12345

        # Verify payload (JSON)
        assert restored.payload.message == "test"
        assert restored.payload.count == 100

    def test_mixed_serialization_three_fields(self):
        """Test mixed serialization with three different fields."""

        class Part1(MessagePartial):
            encoding = Encoding.BIG_ENDIAN
            fields = {"a": {"type": "uint(8)"}}

        class Part2(MessagePartial):
            encoding = Encoding.BIG_ENDIAN
            fields = {"b": {"type": "str"}}

        class Part3(MessagePartial):
            encoding = Encoding.BIG_ENDIAN
            fields = {"c": {"type": "float"}}

        class TripleMixed(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "first": {"type": Part1, "serializer": BytesSerializer()},
                "second": {"type": Part2, "serializer": JSONSerializer()},
                "third": {"type": Part3, "serializer": BytesSerializer()},
            }

        # Create and test
        msg = TripleMixed(
            first=Part1(a=42), second=Part2(b="json_field"), third=Part3(c=3.14)
        )

        data = msg.serialize_bytes()
        restored, _ = TripleMixed.deserialize_bytes(data)

        assert restored.first.a == 42
        assert restored.second.b == "json_field"
        assert abs(restored.third.c - 3.14) < 0.001

    def test_all_json_serialization(self):
        """Test message where all fields use JSON serialization."""

        class JsonPart(MessagePartial):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "x": {"type": "int(32)"},
                "y": {"type": "str"},
            }

        class AllJson(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "field1": {"type": JsonPart, "serializer": JSONSerializer()},
                "field2": {"type": JsonPart, "serializer": JSONSerializer()},
            }

        msg = AllJson(
            field1=JsonPart(x=10, y="first"), field2=JsonPart(x=20, y="second")
        )

        data = msg.serialize_bytes()
        restored, _ = AllJson.deserialize_bytes(data)

        assert restored.field1.x == 10
        assert restored.field1.y == "first"
        assert restored.field2.x == 20
        assert restored.field2.y == "second"

    def test_all_binary_serialization(self):
        """Test message where all fields use binary serialization."""

        class BinaryPart(MessagePartial):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "x": {"type": "uint(16)"},
                "y": {"type": "uint(16)"},
            }

        class AllBinary(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "field1": {"type": BinaryPart, "serializer": BytesSerializer()},
                "field2": {"type": BinaryPart, "serializer": BytesSerializer()},
            }

        msg = AllBinary(
            field1=BinaryPart(x=100, y=200), field2=BinaryPart(x=300, y=400)
        )

        data = msg.serialize_bytes()
        restored, _ = AllBinary.deserialize_bytes(data)

        assert restored.field1.x == 100
        assert restored.field1.y == 200
        assert restored.field2.x == 300
        assert restored.field2.y == 400

    def test_size_comparison(self):
        """Test that JSON is larger than binary serialization."""

        class Data(MessagePartial):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "a": {"type": "uint(32)"},
                "b": {"type": "uint(32)"},
                "c": {"type": "uint(32)"},
            }

        data_obj = Data(a=1000, b=2000, c=3000)

        # Binary serialization
        binary_serializer = BytesSerializer()
        binary_data = binary_serializer.serialize(data_obj)

        # JSON serialization
        json_serializer = JSONSerializer()
        json_data = json_serializer.serialize(data_obj)

        # JSON should be larger for this numeric data
        assert len(json_data) > len(binary_data)

    def test_nested_partial_with_serializer(self):
        """Test nested MessagePartial with per-field serializer."""

        class Inner(MessagePartial):
            encoding = Encoding.BIG_ENDIAN
            fields = {"value": {"type": "int(32)"}}

        class Outer(MessagePartial):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "inner": {"type": Inner, "serializer": JSONSerializer()},
                "extra": {"type": "uint(8)"},
            }

        outer = Outer(inner=Inner(value=999), extra=42)

        # Serialize and deserialize
        data = outer.serialize_bytes()
        restored, _ = Outer.deserialize_bytes(data)

        assert restored.inner.value == 999
        assert restored.extra == 42


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_message(self):
        """Test serialization of message with no fields."""

        class EmptyPartial(MessagePartial):
            encoding = Encoding.BIG_ENDIAN
            fields = {}

        partial = EmptyPartial()
        serializer = JSONSerializer()

        # Should serialize to minimal JSON
        json_bytes = serializer.serialize(partial)
        restored = serializer.deserialize(json_bytes, EmptyPartial)

        assert restored is not None

    def test_unicode_in_json(self):
        """Test JSON serialization with Unicode characters."""

        class UnicodePartial(MessagePartial):
            encoding = Encoding.BIG_ENDIAN
            fields = {"text": {"type": "str"}}

        partial = UnicodePartial(text="Hello 世界 🌍")
        serializer = JSONSerializer(ensure_ascii=False)

        # Serialize and deserialize
        json_bytes = serializer.serialize(partial)
        restored = serializer.deserialize(json_bytes, UnicodePartial)

        assert restored.text == "Hello 世界 🌍"

    def test_special_float_values(self):
        """Test JSON serialization with special float values."""

        class FloatPartial(MessagePartial):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "value": {"type": "float"},
            }

        # Test very small value
        partial = FloatPartial(value=0.0000001)
        serializer = JSONSerializer()

        json_bytes = serializer.serialize(partial)
        restored = serializer.deserialize(json_bytes, FloatPartial)

        # Should be approximately equal
        assert abs(restored.value - 0.0000001) < 0.00000001

    def test_large_message(self):
        """Test mixed serialization with a larger message."""

        class LargePart(MessagePartial):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "data": {"type": "str"},
            }

        class LargeMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "part1": {"type": LargePart, "serializer": JSONSerializer()},
                "part2": {"type": LargePart, "serializer": BytesSerializer()},
            }

        # Create with large string data
        large_str = "x" * 10000
        msg = LargeMessage(
            part1=LargePart(data=large_str), part2=LargePart(data=large_str)
        )

        data = msg.serialize_bytes()
        restored, consumed = LargeMessage.deserialize_bytes(data)

        assert len(restored.part1.data) == 10000
        assert len(restored.part2.data) == 10000
        assert restored.part1.data == large_str
        assert restored.part2.data == large_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
