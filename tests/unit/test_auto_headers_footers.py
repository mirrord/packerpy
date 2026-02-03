"""Tests for automatic headers and footers in Protocol."""

import pytest
from packerpy.protocols.protocol import Protocol, protocol, InvalidMessage
from packerpy.protocols.message import Message
from packerpy.protocols.message_partial import MessagePartial, Encoding


class SampleData(MessagePartial):
    """Sample message partial for testing."""

    encoding = Encoding.BIG_ENDIAN
    fields = {
        "value": {"type": "uint(16)"},
    }


def test_basic_header():
    """Test basic header with static value."""
    proto = Protocol()

    @protocol(proto)
    class TestMsg(Message):
        encoding = Encoding.BIG_ENDIAN
        fields = {
            "data": {"type": "str"},
        }

    # Set header with static value
    proto.set_headers({"version": {"type": "uint(8)", "static": 1}})

    msg = TestMsg(data="Hello")
    encoded = proto.encode(msg)
    decoded, _ = proto.decode(encoded)

    assert decoded.data == "Hello"
    proto.clear_headers()


def test_basic_footer():
    """Test basic footer with static value."""
    proto = Protocol()

    @protocol(proto)
    class TestMsg(Message):
        encoding = Encoding.BIG_ENDIAN
        fields = {
            "data": {"type": "str"},
        }

    # Set footer with end marker
    proto.set_footers({"end_marker": {"type": "uint(16)", "static": 0xFFFF}})

    msg = TestMsg(data="World")
    encoded = proto.encode(msg)
    decoded, _ = proto.decode(encoded)

    assert decoded.data == "World"
    proto.clear_footers()


def test_field_count_header():
    """Test header that counts fields."""
    proto = Protocol()

    @protocol(proto)
    class TestMsg(Message):
        encoding = Encoding.BIG_ENDIAN
        fields = {
            "field1": {"type": "int(32)"},
            "field2": {"type": "str"},
        }

    proto.set_headers(
        {
            "field_count": {
                "type": "uint(8)",
                "compute": lambda msg: Protocol.count_fields(msg.message),
            }
        }
    )

    msg = TestMsg(field1=100, field2="test")
    encoded = proto.encode(msg)
    decoded, _ = proto.decode(encoded)

    assert decoded.field1 == 100
    assert decoded.field2 == "test"
    proto.clear_headers()


def test_list_length_header():
    """Test header that reports list length."""
    proto = Protocol()

    @protocol(proto)
    class TestMsg(Message):
        encoding = Encoding.BIG_ENDIAN
        fields = {
            "items": {"type": "int(32)", "numlist": 3},
        }

    proto.set_headers(
        {
            "num_items": {
                "type": "uint(8)",
                "compute": lambda msg: Protocol.list_length(msg.message, "items"),
            }
        }
    )

    msg = TestMsg(items=[10, 20, 30])
    encoded = proto.encode(msg)
    decoded, _ = proto.decode(encoded)

    assert decoded.items == [10, 20, 30]
    proto.clear_headers()


def test_crc32_footer():
    """Test CRC32 checksum footer."""
    proto = Protocol()

    @protocol(proto)
    class TestMsg(Message):
        encoding = Encoding.BIG_ENDIAN
        fields = {
            "data": {"type": "str"},
        }

    proto.set_footers(
        {
            "crc": {
                "type": "uint(32)",
                "compute": lambda msg: Protocol.crc32(msg.serialize_bytes()),
            }
        }
    )

    msg = TestMsg(data="Test CRC")
    encoded = proto.encode(msg)
    decoded, _ = proto.decode(encoded)

    assert decoded.data == "Test CRC"
    proto.clear_footers()


def test_crc32_tamper_detection():
    """Test that CRC32 detects tampering."""
    proto = Protocol()

    @protocol(proto)
    class TestMsg(Message):
        encoding = Encoding.BIG_ENDIAN
        fields = {
            "value": {"type": "int(32)"},
        }

    proto.set_footers(
        {
            "crc": {
                "type": "uint(32)",
                "compute": lambda msg: Protocol.crc32(msg.serialize_bytes()),
            }
        }
    )

    msg = TestMsg(value=12345)
    encoded = proto.encode(msg)

    # Tamper with the message
    tampered = bytearray(encoded)
    # Corrupt a byte in the message (skip type header)
    tampered[15] ^= 0xFF

    # Should detect tampering
    result = proto.decode(bytes(tampered))
    assert result is not None
    decoded, _ = result
    assert isinstance(decoded, InvalidMessage)

    proto.clear_footers()


def test_message_size_header():
    """Test header with message size."""
    proto = Protocol()

    @protocol(proto)
    class TestMsg(Message):
        encoding = Encoding.BIG_ENDIAN
        fields = {
            "data": {"type": "str"},
        }

    proto.set_headers({"msg_size": {"type": "uint(32)", "size_of": "body"}})

    msg = TestMsg(data="Size test")
    encoded = proto.encode(msg)
    decoded, _ = proto.decode(encoded)

    assert decoded.data == "Size test"
    proto.clear_headers()


def test_deep_field_reference():
    """Test deep field references in headers."""
    proto = Protocol()

    @protocol(proto)
    class TestMsg(Message):
        encoding = Encoding.BIG_ENDIAN
        fields = {
            "nested": {"type": SampleData},
            "data": {"type": "str"},
        }

    proto.set_headers(
        {"nested_value": {"type": "uint(16)", "value_from": "nested.value"}}
    )

    nested = SampleData(value=42)
    msg = TestMsg(nested=nested, data="test")
    encoded = proto.encode(msg)
    decoded, _ = proto.decode(encoded)

    assert decoded.nested.value == 42
    assert decoded.data == "test"
    proto.clear_headers()


def test_combined_headers_and_footers():
    """Test using both headers and footers together."""
    proto = Protocol()

    @protocol(proto)
    class TestMsg(Message):
        encoding = Encoding.BIG_ENDIAN
        fields = {
            "value": {"type": "int(32)"},
            "name": {"type": "str"},
        }

    proto.set_headers(
        {
            "version": {"type": "uint(8)", "static": 1},
            "field_count": {
                "type": "uint(8)",
                "compute": lambda msg: Protocol.count_fields(msg.message),
            },
        }
    )

    proto.set_footers(
        {
            "crc": {
                "type": "uint(32)",
                "compute": lambda msg: Protocol.crc32(msg.serialize_bytes()),
            },
            "end": {"type": "uint(16)", "static": 0xFFFF},
        }
    )

    msg = TestMsg(value=999, name="Combined")
    encoded = proto.encode(msg)
    decoded, _ = proto.decode(encoded)

    assert decoded.value == 999
    assert decoded.name == "Combined"

    proto.clear_headers()
    proto.clear_footers()


def test_length_of_field():
    """Test length_of computation."""
    proto = Protocol()

    @protocol(proto)
    class TestMsg(Message):
        encoding = Encoding.BIG_ENDIAN
        fields = {
            "data": {"type": "bytes"},
        }

    proto.set_headers({"data_len": {"type": "uint(32)", "length_of": "data"}})

    msg = TestMsg(data=b"Hello World")
    encoded = proto.encode(msg)
    decoded, _ = proto.decode(encoded)

    assert decoded.data == b"Hello World"
    proto.clear_headers()


def test_length_of_list():
    """Test length_of on list field."""
    proto = Protocol()

    @protocol(proto)
    class TestMsg(Message):
        encoding = Encoding.BIG_ENDIAN
        fields = {
            "items": {"type": "int(32)", "numlist": 5},
        }

    proto.set_headers({"num_items": {"type": "uint(8)", "length_of": "items"}})

    msg = TestMsg(items=[1, 2, 3, 4, 5])
    encoded = proto.encode(msg)
    decoded, _ = proto.decode(encoded)

    assert decoded.items == [1, 2, 3, 4, 5]
    proto.clear_headers()


def test_size_of_field():
    """Test size_of computation."""
    proto = Protocol()

    @protocol(proto)
    class TestMsg(Message):
        encoding = Encoding.BIG_ENDIAN
        fields = {
            "value": {"type": "int(64)"},
        }

    proto.set_headers({"value_size": {"type": "uint(8)", "size_of": "value"}})

    msg = TestMsg(value=123456)
    encoded = proto.encode(msg)
    decoded, _ = proto.decode(encoded)

    assert decoded.value == 123456
    proto.clear_headers()


def test_value_from_field():
    """Test value_from reference."""
    proto = Protocol()

    @protocol(proto)
    class TestMsg(Message):
        encoding = Encoding.BIG_ENDIAN
        fields = {
            "id": {"type": "uint(32)"},
            "data": {"type": "str"},
        }

    proto.set_headers({"msg_id": {"type": "uint(32)", "value_from": "id"}})

    msg = TestMsg(id=12345, data="test")
    encoded = proto.encode(msg)
    decoded, _ = proto.decode(encoded)

    assert decoded.id == 12345
    assert decoded.data == "test"
    proto.clear_headers()


def test_partial_crc():
    """Test CRC over subset of message."""
    proto = Protocol()

    @protocol(proto)
    class TestMsg(Message):
        encoding = Encoding.BIG_ENDIAN
        fields = {
            "critical": {"type": "int(32)"},
            "non_critical": {"type": "str"},
        }

    def compute_critical_crc(msg):
        # CRC only over the critical field
        critical_bytes = msg.message.critical.to_bytes(4, "big", signed=True)
        return Protocol.crc32(critical_bytes)

    proto.set_footers({"crc": {"type": "uint(32)", "compute": compute_critical_crc}})

    msg = TestMsg(critical=999, non_critical="not protected")
    encoded = proto.encode(msg)
    decoded, _ = proto.decode(encoded)

    assert decoded.critical == 999
    assert decoded.non_critical == "not protected"
    proto.clear_footers()


def test_static_field_validation():
    """Test that static fields are validated during decode."""
    proto = Protocol()

    @protocol(proto)
    class TestMsg(Message):
        encoding = Encoding.BIG_ENDIAN
        fields = {
            "data": {"type": "str"},
        }

    proto.set_headers({"magic": {"type": "uint(32)", "static": 0x12345678}})

    msg = TestMsg(data="test")
    encoded = proto.encode(msg)

    # Tamper with the magic number
    tampered = bytearray(encoded)
    # Magic is in the header, right after type header
    # Type header is 2 + len("TestMsg") = 9 bytes
    # Magic starts at offset 9
    tampered[9] ^= 0xFF  # Corrupt magic number

    result = proto.decode(bytes(tampered))
    assert result is not None
    decoded, _ = result
    assert isinstance(decoded, InvalidMessage)

    proto.clear_headers()


def test_multiple_messages_with_headers():
    """Test that headers work correctly with multiple message types."""
    proto = Protocol()

    @protocol(proto)
    class MsgA(Message):
        encoding = Encoding.BIG_ENDIAN
        fields = {
            "value_a": {"type": "int(32)"},
        }

    @protocol(proto)
    class MsgB(Message):
        encoding = Encoding.BIG_ENDIAN
        fields = {
            "value_b": {"type": "str"},
        }

    proto.set_headers({"version": {"type": "uint(8)", "static": 1}})

    # Encode and decode different message types
    msg_a = MsgA(value_a=100)
    encoded_a = proto.encode(msg_a)
    decoded_a, _ = proto.decode(encoded_a)
    assert decoded_a.value_a == 100

    msg_b = MsgB(value_b="test")
    encoded_b = proto.encode(msg_b)
    decoded_b, _ = proto.decode(encoded_b)
    assert decoded_b.value_b == "test"

    proto.clear_headers()


def test_clear_headers():
    """Test clearing headers."""
    proto = Protocol()

    @protocol(proto)
    class TestMsg(Message):
        encoding = Encoding.BIG_ENDIAN
        fields = {
            "data": {"type": "str"},
        }

    # Set headers
    proto.set_headers({"version": {"type": "uint(8)", "static": 1}})

    msg = TestMsg(data="test")
    encoded_with = proto.encode(msg)

    # Clear headers
    proto.clear_headers()

    msg2 = TestMsg(data="test")
    encoded_without = proto.encode(msg2)

    # Encoded size should be different
    assert len(encoded_with) > len(encoded_without)


def test_clear_footers():
    """Test clearing footers."""
    proto = Protocol()

    @protocol(proto)
    class TestMsg(Message):
        encoding = Encoding.BIG_ENDIAN
        fields = {
            "data": {"type": "str"},
        }

    # Set footers
    proto.set_footers({"end": {"type": "uint(16)", "static": 0xFFFF}})

    msg = TestMsg(data="test")
    encoded_with = proto.encode(msg)

    # Clear footers
    proto.clear_footers()

    msg2 = TestMsg(data="test")
    encoded_without = proto.encode(msg2)

    # Encoded size should be different
    assert len(encoded_with) > len(encoded_without)


def test_helper_count_fields():
    """Test Protocol.count_fields helper."""
    proto = Protocol()

    @protocol(proto)
    class TestMsg(Message):
        encoding = Encoding.BIG_ENDIAN
        fields = {
            "field1": {"type": "int(32)"},
            "field2": {"type": "str"},
            "field3": {"type": "int(32)"},
        }

    msg = TestMsg(field1=1, field2="test", field3=3)
    assert Protocol.count_fields(msg) == 3


def test_helper_list_length():
    """Test Protocol.list_length helper."""
    proto = Protocol()

    @protocol(proto)
    class TestMsg(Message):
        encoding = Encoding.BIG_ENDIAN
        fields = {
            "items": {"type": "int(32)", "numlist": 4},
        }

    msg = TestMsg(items=[10, 20, 30, 40])
    assert Protocol.list_length(msg, "items") == 4


def test_helper_crc32():
    """Test Protocol.crc32 helper."""
    data1 = b"Hello World"
    crc1 = Protocol.crc32(data1)
    assert isinstance(crc1, int)
    assert 0 <= crc1 <= 0xFFFFFFFF

    # Same data should produce same CRC
    crc2 = Protocol.crc32(data1)
    assert crc1 == crc2

    # Different data should produce different CRC (with high probability)
    data2 = b"Hello World!"
    crc3 = Protocol.crc32(data2)
    assert crc1 != crc3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
