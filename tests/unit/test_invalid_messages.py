"""Test invalid and incomplete message handling."""

import pytest
from packerpy.protocols import Protocol, Message, InvalidMessage, protocol


# Define test messages
TestProtocol = Protocol()


@protocol(TestProtocol)
class SimpleMessage(Message):
    """Simple test message."""

    fields = {"value": {"type": "int(32)"}}


def test_incomplete_message_buffered():
    """Test that incomplete messages are buffered."""
    proto = Protocol()
    proto.register(SimpleMessage)

    # Create a complete message
    msg = SimpleMessage(value=42)
    complete_data = proto.encode(msg)

    # Send only partial data (not enough for type header)
    partial_data = complete_data[:1]

    # Should return None (buffered)
    result = proto.decode(partial_data, source_id="test1")
    assert result is None

    # Verify buffer exists
    assert proto.get_incomplete_buffer_size("test1") == 1

    # Send remaining data - should successfully decode
    remaining_data = complete_data[1:]
    result = proto.decode(remaining_data, source_id="test1")
    assert result is not None
    decoded_msg, leftover = result
    assert isinstance(decoded_msg, SimpleMessage)
    assert decoded_msg.value == 42
    assert leftover == b""

    # Buffer should be cleared
    assert proto.get_incomplete_buffer_size("test1") == 0


def test_incomplete_message_type_header():
    """Test incomplete message with partial type header."""
    proto = Protocol()
    proto.register(SimpleMessage)

    msg = SimpleMessage(value=100)
    complete_data = proto.encode(msg)

    # Send data up to middle of type name
    partial_data = complete_data[: len(complete_data) // 2]

    result = proto.decode(partial_data, source_id="test2")
    assert result is None

    # Complete the message
    remaining_data = complete_data[len(complete_data) // 2 :]
    result = proto.decode(remaining_data, source_id="test2")
    assert result is not None
    decoded_msg, leftover = result
    assert isinstance(decoded_msg, SimpleMessage)
    assert decoded_msg.value == 100


def test_invalid_message_wrapped():
    """Test that invalid messages are wrapped in InvalidMessage."""
    proto = Protocol()
    proto.register(SimpleMessage)

    # Create invalid data with unknown message type
    invalid_data = b"\x00\x07Unknown" + b"\x00\x00\x00\x01"

    result = proto.decode(invalid_data, source_id="test3")
    assert result is not None
    decoded, leftover = result
    assert isinstance(decoded, InvalidMessage)
    assert decoded.raw_data == invalid_data
    assert "Unknown message type" in str(decoded.error)


def test_clear_incomplete_buffer():
    """Test clearing incomplete buffers."""
    proto = Protocol()
    proto.register(SimpleMessage)

    # Buffer some data
    proto.decode(b"\x00", source_id="test4")
    assert proto.get_incomplete_buffer_size("test4") > 0

    # Clear specific buffer
    assert proto.clear_incomplete_buffer("test4") is True
    assert proto.get_incomplete_buffer_size("test4") == 0

    # Try clearing non-existent buffer
    assert proto.clear_incomplete_buffer("nonexistent") is False


def test_clear_all_incomplete_buffers():
    """Test clearing all incomplete buffers."""
    proto = Protocol()
    proto.register(SimpleMessage)

    # Buffer data for multiple sources
    proto.decode(b"\x00", source_id="source1")
    proto.decode(b"\x00", source_id="source2")
    proto.decode(b"\x00", source_id="source3")

    # Clear all
    count = proto.clear_all_incomplete_buffers()
    assert count == 3
    assert proto.get_incomplete_buffer_size("source1") == 0
    assert proto.get_incomplete_buffer_size("source2") == 0
    assert proto.get_incomplete_buffer_size("source3") == 0


def test_multiple_messages_with_remaining():
    """Test decoding with remaining data."""
    proto = Protocol()
    proto.register(SimpleMessage)

    # Create two messages
    msg1 = SimpleMessage(value=1)
    msg2 = SimpleMessage(value=2)

    data1 = proto.encode(msg1)
    data2 = proto.encode(msg2)

    # Concatenate them
    combined = data1 + data2

    # Decode first message
    result = proto.decode(combined, source_id="test5")
    assert result is not None
    decoded1, remaining = result
    assert isinstance(decoded1, SimpleMessage)
    assert decoded1.value == 1
    assert remaining == data2

    # Decode second message from remaining
    result = proto.decode(remaining, source_id="test5")
    assert result is not None
    decoded2, remaining2 = result
    assert isinstance(decoded2, SimpleMessage)
    assert decoded2.value == 2
    assert remaining2 == b""


def test_invalid_message_representation():
    """Test InvalidMessage string representation."""
    invalid = InvalidMessage(
        raw_data=b"test data",
        error=ValueError("test error"),
        partial_type="TestMessage",
    )

    repr_str = repr(invalid)
    assert "InvalidMessage" in repr_str
    assert "type=TestMessage" in repr_str
    assert "ValueError" in repr_str
    assert "raw_bytes=9" in repr_str


def test_legacy_decode_message():
    """Test legacy decode_message method still works."""
    proto = Protocol()
    proto.register(SimpleMessage)

    msg = SimpleMessage(value=999)
    data = proto.encode(msg)

    # Use legacy method
    decoded = proto.decode_message(data)
    assert decoded is not None
    assert isinstance(decoded, SimpleMessage)
    assert decoded.value == 999


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
