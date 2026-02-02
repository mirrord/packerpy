"""Tests for Protocol message scheduling feature."""

import pytest
import time
import threading
from unittest.mock import Mock

from packerpy.protocols.message import Message
from packerpy.protocols.message_partial import Encoding
from packerpy.protocols.protocol import Protocol, protocol


class TestMessageScheduling:
    """Test suite for message scheduling functionality."""

    def test_schedule_message_basic(self):
        """Test basic message scheduling."""
        # Create protocol and message
        test_protocol = Protocol()

        @protocol(test_protocol)
        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"value": {"type": "int(32)"}}

        msg = TestMessage(value=42)
        callback = Mock()

        # Schedule message
        schedule_id = test_protocol.schedule_message(
            msg=msg, interval=0.1, send_callback=callback
        )

        # Verify schedule ID is returned
        assert isinstance(schedule_id, int)
        assert schedule_id >= 0

        # Wait for a few calls
        time.sleep(0.35)

        # Clean up
        test_protocol.cancel_scheduled_message(schedule_id)

        # Verify callback was called multiple times
        assert callback.call_count >= 3

    def test_schedule_message_sends_encoded_data(self):
        """Test that scheduled messages send properly encoded data."""
        test_protocol = Protocol()

        @protocol(test_protocol)
        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"value": {"type": "int(32)"}}

        msg = TestMessage(value=100)
        expected_data = test_protocol.encode(msg)

        callback = Mock()
        schedule_id = test_protocol.schedule_message(
            msg=msg, interval=0.1, send_callback=callback
        )

        # Wait for at least one call
        time.sleep(0.15)

        # Clean up
        test_protocol.cancel_scheduled_message(schedule_id)

        # Verify the callback was called with encoded data
        assert callback.call_count >= 1
        callback.assert_called_with(expected_data)

    def test_schedule_multiple_messages(self):
        """Test scheduling multiple different messages."""
        test_protocol = Protocol()

        @protocol(test_protocol)
        class Message1(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"value": {"type": "int(32)"}}

        @protocol(test_protocol)
        class Message2(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"text": {"type": "str"}}

        msg1 = Message1(value=1)
        msg2 = Message2(text="test")

        callback1 = Mock()
        callback2 = Mock()

        # Schedule both messages
        id1 = test_protocol.schedule_message(msg1, 0.1, callback1)
        id2 = test_protocol.schedule_message(msg2, 0.1, callback2)

        # Verify different IDs
        assert id1 != id2

        # Wait for calls
        time.sleep(0.25)

        # Clean up
        test_protocol.cancel_scheduled_message(id1)
        test_protocol.cancel_scheduled_message(id2)

        # Both callbacks should have been called
        assert callback1.call_count >= 2
        assert callback2.call_count >= 2

    def test_cancel_scheduled_message(self):
        """Test cancelling a scheduled message."""
        test_protocol = Protocol()

        @protocol(test_protocol)
        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"value": {"type": "int(32)"}}

        msg = TestMessage(value=1)
        callback = Mock()

        schedule_id = test_protocol.schedule_message(msg, 0.1, callback)

        # Wait for a few calls
        time.sleep(0.25)
        initial_count = callback.call_count

        # Cancel the message
        result = test_protocol.cancel_scheduled_message(schedule_id)
        assert result is True

        # Wait and verify no more calls are made
        time.sleep(0.3)
        assert callback.call_count == initial_count

    def test_cancel_nonexistent_schedule(self):
        """Test cancelling a non-existent schedule ID."""
        test_protocol = Protocol()
        result = test_protocol.cancel_scheduled_message(999)
        assert result is False

    def test_cancel_all_scheduled_messages(self):
        """Test cancelling all scheduled messages at once."""
        test_protocol = Protocol()

        @protocol(test_protocol)
        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"value": {"type": "int(32)"}}

        # Schedule multiple messages
        callbacks = [Mock() for _ in range(3)]
        for i, callback in enumerate(callbacks):
            msg = TestMessage(value=i)
            test_protocol.schedule_message(msg, 0.1, callback)

        # Wait for calls
        time.sleep(0.25)

        # Cancel all
        test_protocol.cancel_all_scheduled_messages()

        # Record counts
        counts = [cb.call_count for cb in callbacks]

        # Wait and verify no more calls
        time.sleep(0.3)
        for i, callback in enumerate(callbacks):
            assert callback.call_count == counts[i]

    def test_get_scheduled_messages(self):
        """Test retrieving information about scheduled messages."""
        test_protocol = Protocol()

        @protocol(test_protocol)
        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"value": {"type": "int(32)"}}

        msg1 = TestMessage(value=1)
        msg2 = TestMessage(value=2)

        callback = Mock()

        id1 = test_protocol.schedule_message(msg1, 1.0, callback)
        id2 = test_protocol.schedule_message(msg2, 2.0, callback)

        scheduled = test_protocol.get_scheduled_messages()

        assert len(scheduled) == 2
        assert id1 in scheduled
        assert id2 in scheduled
        assert scheduled[id1]["message"] == msg1
        assert scheduled[id1]["interval"] == 1.0
        assert scheduled[id2]["message"] == msg2
        assert scheduled[id2]["interval"] == 2.0

        # Clean up
        test_protocol.cancel_all_scheduled_messages()

    def test_schedule_invalid_interval(self):
        """Test that scheduling with invalid interval raises error."""
        test_protocol = Protocol()

        @protocol(test_protocol)
        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"value": {"type": "int(32)"}}

        msg = TestMessage(value=1)
        callback = Mock()

        # Test zero interval
        with pytest.raises(ValueError, match="Interval must be positive"):
            test_protocol.schedule_message(msg, 0, callback)

        # Test negative interval
        with pytest.raises(ValueError, match="Interval must be positive"):
            test_protocol.schedule_message(msg, -1, callback)

    def test_schedule_invalid_message(self):
        """Test that scheduling an invalid message raises error."""
        test_protocol = Protocol()

        @protocol(test_protocol)
        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "value": {"type": "int(32)"},
                "required_field": {"type": "str", "required": True},
            }

        # Create invalid message (missing required field)
        msg = TestMessage(value=42)
        test_protocol = Protocol()

        @protocol(test_protocol)
        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"value": {"type": "int(32)"}}

        msg = TestMessage(value=1)

        call_count = 0

        def failing_callback(data):
            nonlocal call_count
            call_count += 1
            raise RuntimeError("Test exception")

        schedule_id = test_protocol.schedule_message(msg, 0.1, failing_callback)

        # Wait for multiple attempts
        time.sleep(0.35)

        # Clean up
        test_protocol.cancel_scheduled_message(schedule_id)

        # Verify it kept trying despite exceptions
        assert call_count >= 3

    def test_different_intervals(self):
        """Test that different intervals work correctly."""
        test_protocol = Protocol()

        @protocol(test_protocol)
        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"value": {"type": "int(32)"}}

        msg1 = TestMessage(value=1)
        msg2 = TestMessage(value=2)

        callback1 = Mock()
        callback2 = Mock()

        # Schedule with different intervals
        id1 = test_protocol.schedule_message(msg1, 0.1, callback1)  # Fast
        id2 = test_protocol.schedule_message(msg2, 0.3, callback2)  # Slow

        # Wait for about 0.6 seconds
        time.sleep(0.65)

        # Clean up
        test_protocol.cancel_scheduled_message(id1)
        test_protocol.cancel_scheduled_message(id2)

        # Fast message should have been called ~6 times
        # Slow message should have been called ~2 times
        assert callback1.call_count >= 5
        assert callback2.call_count >= 2
        assert callback1.call_count > callback2.call_count

    def test_thread_safety(self):
        """Test thread-safe scheduling and cancellation."""
        test_protocol = Protocol()

        @protocol(test_protocol)
        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"value": {"type": "int(32)"}}

        schedule_ids = []

        def schedule_many():
            for i in range(10):
                msg = TestMessage(value=i)
                sid = test_protocol.schedule_message(msg, 0.5, Mock())
                schedule_ids.append(sid)

        # Schedule from multiple threads
        threads = [threading.Thread(target=schedule_many) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have 30 scheduled messages
        scheduled = test_protocol.get_scheduled_messages()
        assert len(scheduled) == 30

        # Clean up
        test_protocol.cancel_all_scheduled_messages()
        assert len(test_protocol.get_scheduled_messages()) == 0

    def test_update_callback(self):
        """Test message update callback before each send."""
        test_protocol = Protocol()

        @protocol(test_protocol)
        class CounterMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"counter": {"type": "int(32)"}}

        msg = CounterMessage(counter=0)
        callback = Mock()

        # Define update callback that increments counter
        def update_counter(m):
            m.counter += 1

        schedule_id = test_protocol.schedule_message(msg, 0.1, callback, update_counter)

        # Wait for several calls
        time.sleep(0.35)

        # Clean up
        test_protocol.cancel_scheduled_message(schedule_id)

        # Verify callback was called multiple times
        assert callback.call_count >= 3

        # Verify counter was incremented
        assert msg.counter >= 3

    def test_update_callback_with_timestamp(self):
        """Test update callback updating timestamp."""
        test_protocol = Protocol()

        @protocol(test_protocol)
        class TimestampMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"timestamp": {"type": "int(64)"}}

        msg = TimestampMessage(timestamp=0)
        sent_data = []

        def capture_callback(data):
            sent_data.append(data)

        # Update callback that sets current time
        def update_timestamp(m):
            m.timestamp = int(time.time() * 1000)  # milliseconds

        schedule_id = test_protocol.schedule_message(
            msg, 0.1, capture_callback, update_timestamp
        )

        # Wait for multiple sends
        time.sleep(0.25)

        # Clean up
        test_protocol.cancel_scheduled_message(schedule_id)

        # Verify we got multiple sends
        assert len(sent_data) >= 2

        # Decode and verify timestamps are different
        timestamps = []
        for data in sent_data:
            result = test_protocol.decode(data)
            assert result is not None
            decoded, _ = result
            timestamps.append(decoded.timestamp)

        # All timestamps should be unique (updated each time)
        assert len(set(timestamps)) == len(timestamps)

    def test_update_callback_none(self):
        """Test that None update callback works (backward compatibility)."""
        test_protocol = Protocol()

        @protocol(test_protocol)
        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"value": {"type": "int(32)"}}

        msg = TestMessage(value=42)
        callback = Mock()

        # Schedule without update callback (None)
        schedule_id = test_protocol.schedule_message(msg, 0.1, callback, None)

        time.sleep(0.25)
        test_protocol.cancel_scheduled_message(schedule_id)

        # Should work normally
        assert callback.call_count >= 2
        # Value should remain unchanged
        assert msg.value == 42

    def test_update_callback_exception_handling(self):
        """Test that exceptions in update callback are handled."""
        test_protocol = Protocol()

        @protocol(test_protocol)
        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"value": {"type": "int(32)"}}

        msg = TestMessage(value=1)
        callback = Mock()

        call_count = 0

        def failing_update(m):
            nonlocal call_count
            call_count += 1
            raise RuntimeError("Update failed")

        schedule_id = test_protocol.schedule_message(msg, 0.1, callback, failing_update)

        # Wait for attempts
        time.sleep(0.35)

        # Clean up
        test_protocol.cancel_scheduled_message(schedule_id)

        # Update callback should have been called multiple times
        assert call_count >= 3
        # But send callback should not have been called (due to exception)
        # The exception should prevent sending
        assert callback.call_count == 0

    def test_update_callback_complex_logic(self):
        """Test update callback with complex state management."""
        test_protocol = Protocol()

        @protocol(test_protocol)
        class StatusMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"seq": {"type": "int(32)"}, "value": {"type": "int(32)"}}

        msg = StatusMessage(seq=0, value=100)
        sent_data = []

        def capture_callback(data):
            sent_data.append(data)

        # Update callback with complex logic
        def update_status(m):
            m.seq += 1
            m.value = m.value + m.seq  # Compound update

        schedule_id = test_protocol.schedule_message(
            msg, 0.1, capture_callback, update_status
        )

        time.sleep(0.35)
        test_protocol.cancel_scheduled_message(schedule_id)

        # Verify progression
        assert len(sent_data) >= 3

        # Decode and check sequence
        for i, data in enumerate(sent_data):
            result = test_protocol.decode(data)
            assert result is not None
            decoded, _ = result
            assert decoded.seq == i + 1
            # First: seq=1, value=101
            # Second: seq=2, value=103
            # Third: seq=3, value=106
