"""Tests for Protocol automatic reply feature."""

import pytest
from unittest.mock import Mock

from packerpy.protocols.message import Message
from packerpy.protocols.message_partial import Encoding
from packerpy.protocols.protocol import Protocol, protocol


class TestAutoReply:
    """Test suite for automatic reply functionality."""

    def test_register_auto_reply_basic(self):
        """Test basic auto-reply registration."""
        test_protocol = Protocol()

        @protocol(test_protocol)
        class PingMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"seq": {"type": "int(32)"}}

        @protocol(test_protocol)
        class PongMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"seq": {"type": "int(32)"}}

        ping = PingMessage(seq=1)
        pong = PongMessage(seq=1)

        def condition(msg):
            return isinstance(msg, PingMessage)

        callback = Mock()

        reply_id = test_protocol.register_auto_reply(condition, pong, callback)

        assert isinstance(reply_id, int)
        assert reply_id >= 0

        # Check the reply
        test_protocol.check_auto_replies(ping)
        assert callback.call_count == 1

    def test_auto_reply_sends_encoded_data(self):
        """Test that auto-replies send properly encoded data."""
        test_protocol = Protocol()

        @protocol(test_protocol)
        class RequestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"value": {"type": "int(32)"}}

        @protocol(test_protocol)
        class ResponseMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"value": {"type": "int(32)"}}

        request = RequestMessage(value=42)
        response = ResponseMessage(value=100)
        expected_data = test_protocol.encode(response)

        def condition(msg):
            return isinstance(msg, RequestMessage)

        callback = Mock()
        test_protocol.register_auto_reply(condition, response, callback)

        test_protocol.check_auto_replies(request)

        callback.assert_called_once_with(expected_data)

    def test_auto_reply_condition_false(self):
        """Test that replies don't send when condition is False."""
        test_protocol = Protocol()

        @protocol(test_protocol)
        class Message1(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"value": {"type": "int(32)"}}

        @protocol(test_protocol)
        class Message2(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"value": {"type": "int(32)"}}

        msg1 = Message1(value=1)
        msg2 = Message2(value=2)

        # Condition only matches Message2
        def condition(msg):
            return isinstance(msg, Message2)

        callback = Mock()
        test_protocol.register_auto_reply(condition, msg2, callback)

        # Check with Message1 - should not trigger
        test_protocol.check_auto_replies(msg1)
        assert callback.call_count == 0

        # Check with Message2 - should trigger
        test_protocol.check_auto_replies(msg2)
        assert callback.call_count == 1

    def test_multiple_auto_replies(self):
        """Test registering multiple auto-replies."""
        test_protocol = Protocol()

        @protocol(test_protocol)
        class PingMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"value": {"type": "int(32)"}}

        @protocol(test_protocol)
        class Pong1Message(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"value": {"type": "int(32)"}}

        @protocol(test_protocol)
        class Pong2Message(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"value": {"type": "int(32)"}}

        ping = PingMessage(value=1)
        pong1 = Pong1Message(value=10)
        pong2 = Pong2Message(value=20)

        def condition1(msg):
            return isinstance(msg, PingMessage)

        def condition2(msg):
            return isinstance(msg, PingMessage)

        callback1 = Mock()
        callback2 = Mock()

        id1 = test_protocol.register_auto_reply(condition1, pong1, callback1)
        id2 = test_protocol.register_auto_reply(condition2, pong2, callback2)

        assert id1 != id2

        # Both should trigger
        replies_sent = test_protocol.check_auto_replies(ping)
        assert replies_sent == 2
        assert callback1.call_count == 1
        assert callback2.call_count == 1

    def test_unregister_auto_reply(self):
        """Test unregistering an auto-reply."""
        test_protocol = Protocol()

        @protocol(test_protocol)
        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"value": {"type": "int(32)"}}

        msg = TestMessage(value=1)

        def condition(m):
            return True

        callback = Mock()

        reply_id = test_protocol.register_auto_reply(condition, msg, callback)

        # Should trigger
        test_protocol.check_auto_replies(msg)
        assert callback.call_count == 1

        # Unregister
        result = test_protocol.unregister_auto_reply(reply_id)
        assert result is True

        # Should not trigger anymore
        test_protocol.check_auto_replies(msg)
        assert callback.call_count == 1  # Still 1, not incremented

    def test_unregister_nonexistent_reply(self):
        """Test unregistering a non-existent reply ID."""
        test_protocol = Protocol()
        result = test_protocol.unregister_auto_reply(999)
        assert result is False

    def test_unregister_all_auto_replies(self):
        """Test unregistering all auto-replies."""
        test_protocol = Protocol()

        @protocol(test_protocol)
        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"value": {"type": "int(32)"}}

        msg = TestMessage(value=1)

        def condition(m):
            return True

        # Register multiple replies
        callbacks = [Mock() for _ in range(3)]
        for callback in callbacks:
            test_protocol.register_auto_reply(condition, msg, callback)

        # All should trigger
        test_protocol.check_auto_replies(msg)
        assert all(cb.call_count == 1 for cb in callbacks)

        # Unregister all
        test_protocol.unregister_all_auto_replies()

        # None should trigger
        test_protocol.check_auto_replies(msg)
        assert all(cb.call_count == 1 for cb in callbacks)  # Still 1 each

    def test_get_auto_replies(self):
        """Test retrieving information about registered auto-replies."""
        test_protocol = Protocol()

        @protocol(test_protocol)
        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"value": {"type": "int(32)"}}

        msg1 = TestMessage(value=1)
        msg2 = TestMessage(value=2)

        def condition(m):
            return True

        callback = Mock()

        id1 = test_protocol.register_auto_reply(condition, msg1, callback)
        id2 = test_protocol.register_auto_reply(condition, msg2, callback)

        auto_replies = test_protocol.get_auto_replies()

        assert len(auto_replies) == 2
        assert id1 in auto_replies
        assert id2 in auto_replies
        assert auto_replies[id1]["reply_msg"] == msg1
        assert auto_replies[id2]["reply_msg"] == msg2

    def test_update_callback(self):
        """Test auto-reply with update callback."""
        test_protocol = Protocol()

        @protocol(test_protocol)
        class RequestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"req_id": {"type": "int(32)"}}

        @protocol(test_protocol)
        class ResponseMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"req_id": {"type": "int(32)"}, "status": {"type": "int(32)"}}

        request = RequestMessage(req_id=42)
        response = ResponseMessage(req_id=0, status=200)

        sent_data = []

        def capture_callback(data):
            sent_data.append(data)

        # Update callback copies req_id from request to response
        def update_response(incoming, reply):
            reply.req_id = incoming.req_id

        def condition(msg):
            return isinstance(msg, RequestMessage)

        test_protocol.register_auto_reply(
            condition, response, capture_callback, update_response
        )

        test_protocol.check_auto_replies(request)

        assert len(sent_data) == 1
        result = test_protocol.decode(sent_data[0])
        assert result is not None
        decoded, _ = result
        assert decoded.req_id == 42  # Copied from request
        assert decoded.status == 200

    def test_update_callback_complex(self):
        """Test auto-reply with complex update logic."""
        test_protocol = Protocol()

        @protocol(test_protocol)
        class QueryMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"query_id": {"type": "int(32)"}, "value": {"type": "int(32)"}}

        @protocol(test_protocol)
        class ResultMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "query_id": {"type": "int(32)"},
                "result": {"type": "int(32)"},
            }

        query = QueryMessage(query_id=5, value=10)
        result = ResultMessage(query_id=0, result=0)

        sent_data = []

        def capture_callback(data):
            sent_data.append(data)

        # Update callback computes result based on incoming value
        def compute_result(incoming, reply):
            reply.query_id = incoming.query_id
            reply.result = incoming.value * 2  # Double the value

        def condition(msg):
            return isinstance(msg, QueryMessage)

        test_protocol.register_auto_reply(
            condition, result, capture_callback, compute_result
        )

        test_protocol.check_auto_replies(query)

        assert len(sent_data) == 1
        result = test_protocol.decode(sent_data[0])
        assert result is not None
        decoded, _ = result
        assert decoded.query_id == 5
        assert decoded.result == 20  # 10 * 2

    def test_update_callback_none(self):
        """Test that None update callback works (no updates)."""
        test_protocol = Protocol()

        @protocol(test_protocol)
        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"value": {"type": "int(32)"}}

        request = TestMessage(value=1)
        reply = TestMessage(value=99)

        callback = Mock()

        def condition(msg):
            return True

        test_protocol.register_auto_reply(condition, reply, callback, None)

        test_protocol.check_auto_replies(request)

        assert callback.call_count == 1
        assert reply.value == 99  # Unchanged

    def test_condition_callback_exception_handling(self):
        """Test that exceptions in condition callbacks are handled."""
        test_protocol = Protocol()

        @protocol(test_protocol)
        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"value": {"type": "int(32)"}}

        msg = TestMessage(value=1)
        callback = Mock()

        def failing_condition(m):
            raise RuntimeError("Condition failed")

        test_protocol.register_auto_reply(failing_condition, msg, callback)

        # Should not crash
        replies_sent = test_protocol.check_auto_replies(msg)
        assert replies_sent == 0
        assert callback.call_count == 0

    def test_update_callback_exception_handling(self):
        """Test that exceptions in update callbacks are handled."""
        test_protocol = Protocol()

        @protocol(test_protocol)
        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"value": {"type": "int(32)"}}

        msg = TestMessage(value=1)
        callback = Mock()

        def condition(m):
            return True

        def failing_update(incoming, reply):
            raise RuntimeError("Update failed")

        test_protocol.register_auto_reply(condition, msg, callback, failing_update)

        # Should not crash
        replies_sent = test_protocol.check_auto_replies(msg)
        assert replies_sent == 0
        assert callback.call_count == 0

    def test_send_callback_exception_handling(self):
        """Test that exceptions in send callbacks are handled."""
        test_protocol = Protocol()

        @protocol(test_protocol)
        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"value": {"type": "int(32)"}}

        msg = TestMessage(value=1)

        def condition(m):
            return True

        def failing_send(data):
            raise RuntimeError("Send failed")

        test_protocol.register_auto_reply(condition, msg, failing_send)

        # Should not crash
        replies_sent = test_protocol.check_auto_replies(msg)
        assert replies_sent == 0

    def test_register_invalid_reply_message(self):
        """Test that registering an invalid reply message raises error."""
        test_protocol = Protocol()

        @protocol(test_protocol)
        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "value": {"type": "int(32)"},
                "required_field": {"type": "str", "required": True},
            }

        # Invalid message (missing required field)
        invalid_msg = TestMessage(value=42)

        def condition(m):
            return True

        callback = Mock()

        with pytest.raises(ValueError, match="Cannot register invalid reply message"):
            test_protocol.register_auto_reply(condition, invalid_msg, callback)

    def test_condition_based_on_message_content(self):
        """Test condition callback that checks message content."""
        test_protocol = Protocol()

        @protocol(test_protocol)
        class CommandMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"command": {"type": "int(32)"}, "value": {"type": "int(32)"}}

        @protocol(test_protocol)
        class AckMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"status": {"type": "int(32)"}}

        cmd_ping = CommandMessage(command=1, value=0)
        cmd_reset = CommandMessage(command=2, value=0)
        ack = AckMessage(status=1)

        callback = Mock()

        # Only reply to ping command (command == 1)
        def is_ping(msg):
            return isinstance(msg, CommandMessage) and msg.command == 1

        test_protocol.register_auto_reply(is_ping, ack, callback)

        # Should trigger for ping
        test_protocol.check_auto_replies(cmd_ping)
        assert callback.call_count == 1

        # Should not trigger for reset
        test_protocol.check_auto_replies(cmd_reset)
        assert callback.call_count == 1  # Still 1

    def test_check_auto_replies_return_count(self):
        """Test that check_auto_replies returns correct count."""
        test_protocol = Protocol()

        @protocol(test_protocol)
        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"value": {"type": "int(32)"}}

        msg = TestMessage(value=1)
        callback = Mock()

        def condition(m):
            return True

        # Register 5 auto-replies
        for _ in range(5):
            test_protocol.register_auto_reply(condition, msg, callback)

        replies_sent = test_protocol.check_auto_replies(msg)
        assert replies_sent == 5
        assert callback.call_count == 5

    def test_auto_reply_with_different_message_types(self):
        """Test auto-replies with different message types."""
        test_protocol = Protocol()

        @protocol(test_protocol)
        class PingMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"seq": {"type": "int(32)"}}

        @protocol(test_protocol)
        class StatusMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"value": {"type": "int(32)"}}

        @protocol(test_protocol)
        class PongMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"seq": {"type": "int(32)"}}

        @protocol(test_protocol)
        class AckMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"value": {"type": "int(32)"}}

        ping = PingMessage(seq=1)
        status = StatusMessage(value=100)
        pong = PongMessage(seq=1)
        ack = AckMessage(value=1)

        callback1 = Mock()
        callback2 = Mock()

        # Reply to ping with pong
        test_protocol.register_auto_reply(
            lambda m: isinstance(m, PingMessage), pong, callback1
        )

        # Reply to status with ack
        test_protocol.register_auto_reply(
            lambda m: isinstance(m, StatusMessage), ack, callback2
        )

        # Check with ping - only callback1 should trigger
        test_protocol.check_auto_replies(ping)
        assert callback1.call_count == 1
        assert callback2.call_count == 0

        # Check with status - only callback2 should trigger
        test_protocol.check_auto_replies(status)
        assert callback1.call_count == 1
        assert callback2.call_count == 1
