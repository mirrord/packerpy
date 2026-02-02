"""Integration test for client multiple sends bug fix."""

import time
import pytest
from packerpy.client import Client
from packerpy.server import Server
from packerpy.protocols.protocol import Protocol
from packerpy.protocols.message import Message, Encoding


class TestMessage(Message):
    """Test message class."""

    encoding = Encoding.BIG_ENDIAN
    fields = {"text": {"type": "str"}}


class TestClientMultipleSendsIntegration:
    """Integration tests for multiple send operations."""

    @pytest.mark.timeout(10)
    def test_send_message_twice_integration(self):
        """Test sending two messages in succession - integration test."""
        protocol = Protocol()
        protocol.register(TestMessage)

        # Start server
        def echo_handler(msg, addr):
            return msg

        server = Server(
            host="127.0.0.1",
            port=18080,
            message_handler=echo_handler,
            protocol=protocol,
        )
        server.start()
        time.sleep(0.2)

        try:
            # Connect client
            client = Client(host="127.0.0.1", port=18080, protocol=protocol)
            client.connect()
            time.sleep(0.2)

            # First send - this should work
            msg1 = TestMessage()
            msg1.text = "First message"
            result1 = client.send(msg1)
            assert result1 is True, "First send failed"

            time.sleep(0.1)
            response1 = client.receive(timeout=1.0)
            assert response1 is not None, "First response not received"
            assert response1.text == "First message"

            # Second send - this is the bug we're fixing
            # Without the fix, this would timeout because receive loop blocks event loop
            msg2 = TestMessage()
            msg2.text = "Second message"
            result2 = client.send(msg2)
            assert result2 is True, "Second send failed - bug not fixed!"

            # Note: We may not receive second response if server closes connection
            # but the send itself should succeed

            client.close()
        finally:
            server.stop()
            time.sleep(0.2)

    @pytest.mark.timeout(10)
    def test_send_bytes_after_message_integration(self):
        """Test sending raw bytes after a message - integration test."""
        protocol = Protocol()
        protocol.register(TestMessage)

        # Start server
        server = Server(host="127.0.0.1", port=18081, protocol=protocol)
        server.start()
        time.sleep(0.2)

        try:
            # Connect client
            client = Client(host="127.0.0.1", port=18081, protocol=protocol)
            client.connect()
            time.sleep(0.2)

            # First send a message
            msg = TestMessage()
            msg.text = "Message"
            result1 = client.send(msg)
            assert result1 is True

            time.sleep(0.1)
            # Try to receive but don't fail if nothing comes
            response = client.receive(timeout=0.5)

            # Now send raw bytes - this should not timeout
            # This is the key test - before the fix, this would timeout
            msg2 = TestMessage()
            msg2.text = "Raw bytes test"
            raw_bytes = protocol.encode_message(msg2)
            result2 = client.send(raw_bytes)
            assert result2 is True, "Sending raw bytes after message failed!"

            client.close()
        finally:
            server.stop()
            time.sleep(0.2)
