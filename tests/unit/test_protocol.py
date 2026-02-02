"""Unit tests for protocols.protocol module."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from packerpy.protocols.protocol import Protocol, protocol
from packerpy.protocols.message import Message, Encoding


# Test message classes for registry testing
class SampleMessageA(Message):
    """Test message type A."""

    encoding = Encoding.BIG_ENDIAN
    fields = {
        "value_a": {"type": "int(32)"},
    }


class SampleMessageB(Message):
    """Test message type B."""

    encoding = Encoding.BIG_ENDIAN
    fields = {
        "value_b": {"type": "int(32)"},
        "name": {"type": "str"},
    }


class TestProtocol:
    """Test suite for Protocol class."""

    def test_initialization(self):
        """Test Protocol initialization."""
        proto = Protocol()
        assert proto is not None
        assert hasattr(proto, "_message_registry")
        assert proto._message_registry == {}

    def test_register_message_class(self):
        """Test registering a message class."""
        proto = Protocol()
        proto.register(SampleMessageA)

        assert "SampleMessageA" in proto._message_registry
        assert proto._message_registry["SampleMessageA"] == SampleMessageA

    def test_register_duplicate_raises_error(self):
        """Test registering duplicate message type raises error."""
        proto = Protocol()
        proto.register(SampleMessageA)

        with pytest.raises(ValueError, match="already registered"):
            proto.register(SampleMessageA)

    def test_protocol_decorator(self):
        """Test @protocol decorator registers message."""
        proto = Protocol()

        @protocol(proto)
        class DecoratedMessage(Message):
            fields = {"x": {"type": "int(32)"}}

        assert "DecoratedMessage" in proto._message_registry
        assert proto._message_registry["DecoratedMessage"] == DecoratedMessage

    def test_encode_registered_message(self):
        """Test encoding a registered message."""
        proto = Protocol()
        proto.register(SampleMessageA)

        msg = SampleMessageA(value_a=42)
        encoded = proto.encode(msg)

        # Should include type header + message data
        assert isinstance(encoded, bytes)
        assert len(encoded) > 4  # Type header + data

    def test_encode_unregistered_message_raises_error(self):
        """Test encoding unregistered message raises error."""
        proto = Protocol()

        class UnregisteredMessage(Message):
            fields = {"x": {"type": "int(32)"}}

        msg = UnregisteredMessage(x=10)

        with pytest.raises(ValueError, match="not registered"):
            proto.encode(msg)

    def test_decode_registered_message(self):
        """Test decoding returns correct message type."""
        proto = Protocol()
        proto.register(SampleMessageA)

        # Create and encode
        original = SampleMessageA(value_a=123)
        encoded = proto.encode(original)

        # Decode
        result = proto.decode(encoded)
        assert result is not None
        decoded, remaining = result

        assert isinstance(decoded, SampleMessageA)
        assert decoded.value_a == 123
        assert remaining == b""

    def test_decode_multiple_message_types(self):
        """Test decoding different message types correctly."""
        proto = Protocol()
        proto.register(SampleMessageA)
        proto.register(SampleMessageB)

        # Encode both types
        msg_a = SampleMessageA(value_a=100)
        msg_b = SampleMessageB(value_b=200, name="test")

        data_a = proto.encode(msg_a)
        data_b = proto.encode(msg_b)

        # Decode both
        result_a = proto.decode(data_a)
        result_b = proto.decode(data_b)

        assert result_a is not None
        assert result_b is not None

        decoded_a, _ = result_a
        decoded_b, _ = result_b

        assert isinstance(decoded_a, SampleMessageA)
        assert decoded_a.value_a == 100

        assert isinstance(decoded_b, SampleMessageB)
        assert decoded_b.value_b == 200
        assert decoded_b.name == "test"

    def test_decode_unregistered_type_returns_none(self):
        """Test decoding message with unregistered type returns InvalidMessage."""
        from packerpy.protocols.protocol import InvalidMessage

        proto1 = Protocol()
        proto2 = Protocol()

        proto1.register(SampleMessageA)
        proto2.register(SampleMessageA)

        msg = SampleMessageA(value_a=42)
        data = proto1.encode(msg)

        # Clear proto1's registry to simulate unknown type
        proto1._message_registry.clear()

        result = proto1.decode(data)
        assert result is not None
        decoded, _ = result
        # Should return InvalidMessage when type is not registered
        assert isinstance(decoded, InvalidMessage)

    def test_decode_invalid_data_returns_none(self):
        """Test decode with invalid data returns None."""
        proto = Protocol()

        result = proto.decode(b"invalid")
        assert result is None

    def test_decode_empty_data_returns_none(self):
        """Test decode with empty data returns None."""
        proto = Protocol()

        result = proto.decode(b"")
        assert result is None

    def test_validate_message_valid(self):
        """Test validate_message with valid message."""
        proto = Protocol()
        msg = SampleMessageA(value_a=10)

        result = proto.validate_message(msg)
        assert result is True

    def test_validate_message_static_method(self):
        """Test that validate_message is a static method."""
        msg = SampleMessageA(value_a=10)
        result = Protocol.validate_message(msg)
        assert result is True

    def test_encode_message_legacy_alias(self):
        """Test encode_message as legacy alias for encode."""
        proto = Protocol()
        proto.register(SampleMessageA)

        msg = SampleMessageA(value_a=42)
        result1 = proto.encode(msg)
        result2 = proto.encode_message(msg)

        # Both should produce same output
        assert result1 == result2

    def test_decode_message_legacy_alias(self):
        """Test decode_message as legacy alias for decode."""
        proto = Protocol()
        proto.register(SampleMessageA)

        msg = SampleMessageA(value_a=42)
        encoded = proto.encode(msg)

        result1 = proto.decode(encoded)
        result2 = proto.decode_message(encoded)

        # decode returns tuple, decode_message returns just the message
        assert result1 is not None
        decoded1, _ = result1
        assert isinstance(decoded1, SampleMessageA)
        assert isinstance(result2, SampleMessageA)
        assert decoded1.value_a == result2.value_a

    def test_round_trip_encode_decode(self):
        """Test encoding and then decoding a message."""
        proto = Protocol()
        proto.register(SampleMessageB)

        original = SampleMessageB(value_b=999, name="round_trip_test")

        # Encode
        encoded = proto.encode(original)
        assert isinstance(encoded, bytes)

        # Decode
        result = proto.decode(encoded)
        assert result is not None
        decoded, remaining = result

        assert isinstance(decoded, SampleMessageB)
        assert decoded.value_b == 999
        assert decoded.name == "round_trip_test"
        assert remaining == b""

    def test_multiple_protocols_independent(self):
        """Test multiple protocol instances are independent."""
        proto1 = Protocol()
        proto2 = Protocol()

        proto1.register(SampleMessageA)
        proto2.register(SampleMessageB)

        assert "SampleMessageA" in proto1._message_registry
        assert "SampleMessageA" not in proto2._message_registry

        assert "SampleMessageB" in proto2._message_registry
        assert "SampleMessageB" not in proto1._message_registry

    def test_type_header_format(self):
        """Test that type header is properly formatted."""
        proto = Protocol()
        proto.register(SampleMessageA)

        msg = SampleMessageA(value_a=10)
        encoded = proto.encode(msg)

        # Extract type header
        type_length = int.from_bytes(encoded[0:2], "big")
        message_type = encoded[2 : 2 + type_length].decode("utf-8")

        assert message_type == "SampleMessageA"
        assert type_length == len("SampleMessageA")
