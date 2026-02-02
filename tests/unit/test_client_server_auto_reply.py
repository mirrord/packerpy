"""Tests for Client and Server auto-reply integration."""

import time
import pytest
from packerpy.protocols.message import Message
from packerpy.protocols.message_partial import Encoding
from packerpy.protocols.protocol import Protocol, protocol
from packerpy.client import Client
from packerpy.server import Server


class TestClientServerAutoReply:
    """Test auto-reply integration with Client and Server."""

    def test_client_auto_reply_integration(self):
        """Test that client checks auto-replies on received messages."""
        # Create protocol
        test_protocol = Protocol()

        @protocol(test_protocol)
        class PingMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"seq": {"type": "int(32)"}}

        @protocol(test_protocol)
        class PongMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"seq": {"type": "int(32)"}}

        # Track auto-replies sent
        replies_sent = []

        def capture_reply(data):
            replies_sent.append(data)

        # Register auto-reply
        pong = PongMessage(seq=0)

        def update_pong(ping, pong):
            pong.seq = ping.seq

        test_protocol.register_auto_reply(
            condition_callback=lambda msg: isinstance(msg, PingMessage),
            reply_msg=pong,
            send_callback=capture_reply,
            update_callback=update_pong,
        )

        # Create client with protocol
        client = Client(protocol=test_protocol)

        # Start client (don't actually connect)
        # We'll simulate receiving a message directly

        # Simulate receiving a ping
        ping = PingMessage(seq=42)
        encoded_ping = test_protocol.encode(ping)

        # Decode and check auto-replies (simulating what happens in receive loop)
        result = test_protocol.decode(encoded_ping)
        assert result is not None
        decoded, _ = result
        test_protocol.check_auto_replies(decoded)

        # Verify auto-reply was triggered
        assert len(replies_sent) == 1
        result_reply = test_protocol.decode(replies_sent[0])
        assert result_reply is not None
        decoded_reply, _ = result_reply
        assert isinstance(decoded_reply, PongMessage)
        assert decoded_reply.seq == 42

    def test_client_register_auto_reply_helper(self):
        """Test client's convenience method for registering auto-replies."""
        test_protocol = Protocol()

        @protocol(test_protocol)
        class RequestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"req_id": {"type": "int(32)"}}

        @protocol(test_protocol)
        class ResponseMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"req_id": {"type": "int(32)"}}

        client = Client(protocol=test_protocol)

        response = ResponseMessage(req_id=0)

        def update_response(req, resp):
            resp.req_id = req.req_id

        # Use client's helper method (send_callback auto-provided)
        reply_id = client.register_auto_reply(
            condition_callback=lambda msg: isinstance(msg, RequestMessage),
            reply_msg=response,
            update_callback=update_response,
        )

        assert isinstance(reply_id, int)
        assert reply_id >= 0

        # Verify it was registered
        auto_replies = test_protocol.get_auto_replies()
        assert len(auto_replies) == 1
        assert reply_id in auto_replies

    def test_server_auto_reply_integration(self):
        """Test that server checks auto-replies on received messages."""
        test_protocol = Protocol()

        @protocol(test_protocol)
        class CommandMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"cmd": {"type": "int(32)"}}

        @protocol(test_protocol)
        class AckMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"status": {"type": "int(32)"}}

        # Track auto-replies sent
        replies_sent = []

        def capture_reply(data):
            replies_sent.append(data)

        # Register auto-reply
        ack = AckMessage(status=200)

        test_protocol.register_auto_reply(
            condition_callback=lambda msg: isinstance(msg, CommandMessage),
            reply_msg=ack,
            send_callback=capture_reply,
        )

        # Create server with protocol
        server = Server(protocol=test_protocol)

        # Simulate handling a command message
        cmd = CommandMessage(cmd=5)
        encoded_cmd = test_protocol.encode(cmd)

        # Call the handler directly (simulating what happens in server)
        server._handle_raw_data(encoded_cmd, ("127.0.0.1", 12345))

        # Verify auto-reply was triggered
        assert len(replies_sent) == 1
        result = test_protocol.decode(replies_sent[0])
        assert result is not None
        decoded_reply, _ = result
        assert isinstance(decoded_reply, AckMessage)
        assert decoded_reply.status == 200

    def test_server_register_auto_reply_with_callback(self):
        """Test server's register_auto_reply with custom send callback."""
        test_protocol = Protocol()

        @protocol(test_protocol)
        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"value": {"type": "int(32)"}}

        server = Server(protocol=test_protocol)

        msg = TestMessage(value=1)
        sent_data = []

        def custom_send(data):
            sent_data.append(data)

        # Register with custom send callback
        reply_id = server.register_auto_reply(
            condition_callback=lambda m: isinstance(m, TestMessage),
            reply_msg=msg,
            send_callback=custom_send,
        )

        assert isinstance(reply_id, int)

        # Trigger the auto-reply
        test_protocol.check_auto_replies(msg)
        assert len(sent_data) == 1

    def test_server_register_auto_reply_without_callback(self):
        """Test server's register_auto_reply without send callback (warning case)."""
        test_protocol = Protocol()

        @protocol(test_protocol)
        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"value": {"type": "int(32)"}}

        server = Server(protocol=test_protocol)

        msg = TestMessage(value=1)

        # Register without send callback - should use warning callback
        reply_id = server.register_auto_reply(
            condition_callback=lambda m: isinstance(m, TestMessage),
            reply_msg=msg,
            # No send_callback provided
        )

        assert isinstance(reply_id, int)

        # Trigger should print warning but not crash
        test_protocol.check_auto_replies(msg)

    def test_multiple_auto_replies_on_client(self):
        """Test multiple auto-replies registered on client."""
        test_protocol = Protocol()

        @protocol(test_protocol)
        class EventMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"event_type": {"type": "int(32)"}}

        client = Client(protocol=test_protocol)

        event = EventMessage(event_type=1)
        reply_counts = []

        def count_reply(data):
            reply_counts.append(1)

        # Register multiple auto-replies
        for _ in range(3):
            client.register_auto_reply(
                condition_callback=lambda msg: isinstance(msg, EventMessage),
                reply_msg=event,
                send_callback=count_reply,
            )

        # Trigger all auto-replies
        test_protocol.check_auto_replies(event)

        # All three should have been triggered
        assert len(reply_counts) == 3

    def test_client_auto_reply_with_scheduling(self):
        """Test that client can use both auto-replies and message scheduling."""
        test_protocol = Protocol()

        @protocol(test_protocol)
        class HeartbeatMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"seq": {"type": "int(32)"}}

        @protocol(test_protocol)
        class AckMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {"seq": {"type": "int(32)"}}

        client = Client(protocol=test_protocol)

        # Setup auto-reply
        ack = AckMessage(seq=0)
        ack_count = []

        def count_ack(data):
            ack_count.append(1)

        def update_ack(hb, ack):
            ack.seq = hb.seq

        client.register_auto_reply(
            condition_callback=lambda msg: isinstance(msg, HeartbeatMessage),
            reply_msg=ack,
            send_callback=count_ack,
            update_callback=update_ack,
        )

        # Setup scheduled message
        heartbeat = HeartbeatMessage(seq=0)
        hb_count = []

        def count_hb(data):
            hb_count.append(1)

        def update_hb(msg):
            msg.seq += 1

        schedule_id = test_protocol.schedule_message(
            heartbeat, 0.1, count_hb, update_hb
        )

        # Let scheduling run
        time.sleep(0.25)

        # Stop scheduling
        test_protocol.cancel_scheduled_message(schedule_id)

        # Verify scheduled messages were sent
        assert len(hb_count) >= 2

        # Simulate receiving a heartbeat (triggers auto-reply)
        incoming_hb = HeartbeatMessage(seq=99)
        test_protocol.check_auto_replies(incoming_hb)

        # Verify auto-reply was triggered
        assert len(ack_count) == 1

        # Both features work together
        assert len(hb_count) >= 2
        assert len(ack_count) == 1
