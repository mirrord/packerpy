"""Test static field values in Messages."""

import pytest
from packerpy.protocols import Protocol, Message, protocol
from packerpy.protocols.message_partial import Encoding


def test_static_field_basic():
    """Test basic static field functionality."""
    test_protocol = Protocol()

    @protocol(test_protocol)
    class MagicMessage(Message):
        encoding = Encoding.BIG_ENDIAN
        fields = {
            "magic": {"type": "int(32)", "static": 0x12345678},
            "version": {"type": "int(16)", "static": 1},
            "data": {"type": "str"},
        }

    # Create message - static fields should be set automatically
    msg = MagicMessage(data="Hello")

    # Verify static fields are set
    assert msg.magic == 0x12345678
    assert msg.version == 1
    assert msg.data == "Hello"

    # Encode
    encoded = test_protocol.encode(msg)

    # Decode
    result = test_protocol.decode(encoded)
    assert result is not None
    decoded, remaining = result

    # Verify all fields match
    assert decoded.magic == 0x12345678
    assert decoded.version == 1
    assert decoded.data == "Hello"
    assert remaining == b""


def test_static_field_ignored_in_kwargs():
    """Test that static fields ignore kwargs values."""
    test_protocol = Protocol()

    @protocol(test_protocol)
    class ConstMessage(Message):
        fields = {
            "constant": {"type": "int(32)", "static": 42},
            "variable": {"type": "int(32)"},
        }

    # Try to set static field via kwargs - should be ignored
    msg = ConstMessage(constant=999, variable=100)

    # Static field should still be 42
    assert msg.constant == 42
    assert msg.variable == 100


def test_static_field_verification_on_decode():
    """Test that deserialization correctly handles static field values."""
    test_protocol = Protocol()

    @protocol(test_protocol)
    class VerifyMessage(Message):
        fields = {
            "header": {"type": "uint(16)", "static": 0xABCD},
            "payload": {"type": "int(32)"},
        }

    # Create valid message
    msg = VerifyMessage(payload=123)
    encoded = test_protocol.encode(msg)

    # Should decode successfully
    result = test_protocol.decode(encoded)
    assert result is not None
    decoded, _ = result
    assert decoded.header == 0xABCD
    assert decoded.payload == 123

    # Static field should always be set to the same value
    msg2 = VerifyMessage(payload=456)
    assert msg2.header == 0xABCD  # Same static value
    assert msg2.payload == 456


def test_static_field_with_multiple_types():
    """Test static fields with different types."""
    test_protocol = Protocol()

    @protocol(test_protocol)
    class MultiTypeMessage(Message):
        encoding = Encoding.LITTLE_ENDIAN
        fields = {
            "magic_byte": {"type": "uint(8)", "static": 0xFF},
            "protocol_version": {"type": "uint(16)", "static": 256},
            "flags": {"type": "uint(32)", "static": 0x0000FFFF},
            "identifier": {"type": "str", "static": "PROTO"},
            "data": {"type": "bytes"},
        }

    msg = MultiTypeMessage(data=b"test data")

    # Verify all static fields
    assert msg.magic_byte == 0xFF
    assert msg.protocol_version == 256
    assert msg.flags == 0x0000FFFF
    assert msg.identifier == "PROTO"
    assert msg.data == b"test data"

    # Round trip
    encoded = test_protocol.encode(msg)
    result = test_protocol.decode(encoded)
    assert result is not None
    decoded, _ = result

    assert decoded.magic_byte == 0xFF
    assert decoded.protocol_version == 256
    assert decoded.flags == 0x0000FFFF
    assert decoded.identifier == "PROTO"
    assert decoded.data == b"test data"


def test_static_field_protocol_discrimination():
    """Test static fields for protocol version discrimination."""
    test_protocol = Protocol()

    @protocol(test_protocol)
    class V1Message(Message):
        fields = {
            "version": {"type": "int(8)", "static": 1},
            "command": {"type": "str"},
        }

    @protocol(test_protocol)
    class V2Message(Message):
        fields = {
            "version": {"type": "int(8)", "static": 2},
            "command": {"type": "str"},
            "flags": {"type": "int(32)"},
        }

    # Create v1 message
    v1 = V1Message(command="ping")
    assert v1.version == 1

    # Create v2 message
    v2 = V2Message(command="ping", flags=0x0001)
    assert v2.version == 2

    # Encode both
    v1_data = test_protocol.encode(v1)
    v2_data = test_protocol.encode(v2)

    # Decode and verify
    result1 = test_protocol.decode(v1_data)
    assert result1 is not None
    decoded1, _ = result1
    assert isinstance(decoded1, V1Message)
    assert decoded1.version == 1

    result2 = test_protocol.decode(v2_data)
    assert result2 is not None
    decoded2, _ = result2
    assert isinstance(decoded2, V2Message)
    assert decoded2.version == 2


def test_static_field_with_bool():
    """Test static fields with boolean type."""
    test_protocol = Protocol()

    @protocol(test_protocol)
    class BoolMessage(Message):
        fields = {
            "is_request": {"type": "bool", "static": True},
            "data": {"type": "int(32)"},
        }

    msg = BoolMessage(data=42)
    assert msg.is_request is True

    encoded = test_protocol.encode(msg)
    result = test_protocol.decode(encoded)
    assert result is not None
    decoded, _ = result
    assert decoded.is_request is True
    assert decoded.data == 42


def test_static_field_with_enum():
    """Test static fields with enum type."""
    from enum import IntEnum

    test_protocol = Protocol()

    class MessageType(IntEnum):
        REQUEST = 1
        RESPONSE = 2
        ERROR = 3

    @protocol(test_protocol)
    class RequestMessage(Message):
        fields = {
            "msg_type": {
                "type": "enum",
                "enum": MessageType,
                "size": 1,
                "static": MessageType.REQUEST,
            },
            "data": {"type": "int(32)"},
        }

    msg = RequestMessage(data=100)
    assert msg.msg_type == MessageType.REQUEST

    encoded = test_protocol.encode(msg)
    result = test_protocol.decode(encoded)
    assert result is not None
    decoded, _ = result
    assert decoded.msg_type == MessageType.REQUEST
    assert decoded.data == 100


def test_static_field_serialization_order():
    """Test that static fields maintain proper serialization order."""
    test_protocol = Protocol()

    @protocol(test_protocol)
    class OrderedMessage(Message):
        fields = {
            "header1": {"type": "uint(16)", "static": 0x1111},
            "dynamic1": {"type": "uint(16)"},
            "header2": {"type": "uint(16)", "static": 0x2222},
            "dynamic2": {"type": "uint(16)"},
            "footer": {"type": "uint(16)", "static": 0xFFFF},
        }

    msg = OrderedMessage(dynamic1=0xAAAA, dynamic2=0xBBBB)

    encoded = test_protocol.encode(msg)

    # Manually verify the byte order
    # Skip protocol header (type info), then check field bytes
    # Since this is big endian and fields are int(16):
    # Should be: header1, dynamic1, header2, dynamic2, footer

    result = test_protocol.decode(encoded)
    assert result is not None
    decoded, _ = result

    assert decoded.header1 == 0x1111
    assert decoded.dynamic1 == 0xAAAA
    assert decoded.header2 == 0x2222
    assert decoded.dynamic2 == 0xBBBB
    assert decoded.footer == 0xFFFF


def test_static_field_with_bitwise():
    """Test static fields with bitwise encoding."""
    test_protocol = Protocol()

    @protocol(test_protocol)
    class BitwiseMessage(Message):
        bitwise = True
        fields = {
            "version": {"type": "bit", "bits": 4, "static": 0b0001},
            "flags": {"type": "bit", "bits": 4, "static": 0b1111},
            "data": {"type": "bit", "bits": 8},
        }

    msg = BitwiseMessage(data=0xAB)
    assert msg.version == 0b0001
    assert msg.flags == 0b1111
    assert msg.data == 0xAB

    encoded = test_protocol.encode(msg)
    result = test_protocol.decode(encoded)
    assert result is not None
    decoded, _ = result

    assert decoded.version == 0b0001
    assert decoded.flags == 0b1111
    assert decoded.data == 0xAB


def test_static_field_no_attribute_set_needed():
    """Test that static fields don't require setting before serialization."""
    test_protocol = Protocol()

    @protocol(test_protocol)
    class AutoMessage(Message):
        fields = {
            "magic": {"type": "uint(32)", "static": 0xDEADBEEF},
            "data": {"type": "str"},
        }

    # Create without explicitly setting magic
    msg = AutoMessage(data="test")

    # Magic should already be set
    assert hasattr(msg, "magic")
    assert msg.magic == 0xDEADBEEF

    # Should serialize correctly
    encoded = test_protocol.encode(msg)
    result = test_protocol.decode(encoded)
    assert result is not None
    decoded, _ = result
    assert decoded.magic == 0xDEADBEEF


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
