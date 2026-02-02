"""Unit tests for client module."""

import threading
from unittest.mock import Mock, patch

from packerpy.client import Client, ConnectionStatus
from packerpy.protocols.protocol import Protocol
from packerpy.protocols.message import Message


class TestConnectionStatus:
    """Test ConnectionStatus enum."""

    def test_status_values(self):
        """Test connection status enum values."""
        assert ConnectionStatus.DISCONNECTED.value == "disconnected"
        assert ConnectionStatus.CONNECTING.value == "connecting"
        assert ConnectionStatus.CONNECTED.value == "connected"
        assert ConnectionStatus.DISCONNECTING.value == "disconnecting"
        assert ConnectionStatus.ERROR.value == "error"


class TestClient:
    """Test suite for Client class."""

    def test_initialization(self):
        """Test client initialization."""
        client = Client("127.0.0.1", 8080)

        assert client.host == "127.0.0.1"
        assert client.port == 8080
        assert isinstance(client.protocol, Protocol)
        assert client._status == ConnectionStatus.DISCONNECTED
        assert client._client_thread is None
        assert client._loop is None
        assert client._error is None
        assert client._running is False

    def test_initialization_defaults(self):
        """Test client initialization with defaults."""
        client = Client()

        assert client.host == "127.0.0.1"
        assert client.port == 8080

    @patch("packerpy.client.AsyncTCPClient")
    def test_connect_starts_thread(self, mock_async_client):
        """Test that connect starts background thread."""
        client = Client("127.0.0.1", 8080)

        with patch.object(threading.Thread, "start"):
            client.connect()

        assert client._status == ConnectionStatus.CONNECTING
        assert client._running is True
        assert client._client_thread is not None

    @patch("packerpy.client.AsyncTCPClient")
    @patch("time.sleep")
    def test_connect_waits_briefly(self, mock_sleep, mock_async_client):
        """Test that connect waits briefly for connection."""
        client = Client("127.0.0.1", 8080)

        with patch.object(threading.Thread, "start"):
            client.connect()

        mock_sleep.assert_called_once_with(0.1)

    def test_send_invalid_message(self, capsys):
        """Test sending invalid message returns False."""
        client = Client("127.0.0.1", 8080)
        mock_message = Mock(spec=Message)

        with patch.object(client.protocol, "validate_message", return_value=False):
            result = client.send(mock_message)

        assert result is False
        captured = capsys.readouterr()
        assert "Invalid message" in captured.out

    def test_send_when_not_connected(self):
        """Test sending when not connected returns False."""
        client = Client("127.0.0.1", 8080)
        mock_message = Mock(spec=Message)

        with patch.object(
            client.protocol, "validate_message", return_value=True
        ), patch.object(client.protocol, "encode_message", return_value=b"data"):
            result = client.send(mock_message)

        assert result is False

    def test_receive_with_timeout(self):
        """Test receiving message with timeout."""
        client = Client("127.0.0.1", 8080)

        result = client.receive(timeout=0.1)

        assert result is None

    def test_receive_returns_message_from_queue(self):
        """Test receiving returns message from queue."""
        client = Client("127.0.0.1", 8080)
        mock_message = Mock(spec=Message)
        client._received_messages.put(mock_message)

        result = client.receive(timeout=0.1)

        assert result == mock_message

    def test_receive_non_blocking(self):
        """Test non-blocking receive."""
        client = Client("127.0.0.1", 8080)

        result = client.receive(timeout=0)

        assert result is None

    def test_close(self):
        """Test closing client connection."""
        client = Client("127.0.0.1", 8080)
        client._running = True
        client._status = ConnectionStatus.CONNECTED

        mock_transport = Mock()

        # Mock run_coroutine_threadsafe to avoid creating unawaited coroutines
        with patch.object(client, "_loop", Mock()), patch.object(
            client, "_transport", mock_transport
        ), patch.object(client, "_client_thread", Mock()), patch(
            "asyncio.run_coroutine_threadsafe"
        ) as mock_run_coro:
            mock_future = Mock()
            mock_future.result = Mock(return_value=None)
            mock_run_coro.return_value = mock_future

            client.close()

        assert client._running is False
        assert client._status == ConnectionStatus.DISCONNECTING

    def test_get_status(self):
        """Test getting connection status."""
        client = Client("127.0.0.1", 8080)
        client._status = ConnectionStatus.CONNECTED

        status = client.get_status()

        assert status == ConnectionStatus.CONNECTED

    def test_get_error(self):
        """Test getting last error."""
        client = Client("127.0.0.1", 8080)
        test_error = ValueError("Test error")
        client._error = test_error

        error = client.get_error()

        assert error == test_error

    def test_get_error_when_none(self):
        """Test getting error when none exists."""
        client = Client("127.0.0.1", 8080)

        error = client.get_error()

        assert error is None

    def test_context_manager_entry(self):
        """Test context manager entry."""
        client = Client("127.0.0.1", 8080)

        with patch.object(client, "connect"):
            result = client.__aenter__()

        assert result == client

    def test_context_manager_exit(self):
        """Test context manager exit."""
        client = Client("127.0.0.1", 8080)

        with patch.object(client, "close"):
            client.__aexit__(None, None, None)

            client.close.assert_called_once()

    def test_protocol_decode_message(self):
        """Test that protocol is used to decode messages."""
        client = Client("127.0.0.1", 8080)

        assert isinstance(client.protocol, Protocol)
        assert hasattr(client.protocol, "decode_message")
        assert hasattr(client.protocol, "encode_message")

    def test_multiple_messages_in_queue(self):
        """Test receiving multiple messages from queue."""
        client = Client("127.0.0.1", 8080)

        msg1 = Mock(spec=Message)
        msg2 = Mock(spec=Message)
        msg3 = Mock(spec=Message)

        client._received_messages.put(msg1)
        client._received_messages.put(msg2)
        client._received_messages.put(msg3)

        assert client.receive(timeout=0.1) == msg1
        assert client.receive(timeout=0.1) == msg2
        assert client.receive(timeout=0.1) == msg3
        assert client.receive(timeout=0.1) is None

    def test_status_transitions(self):
        """Test connection status transitions."""
        client = Client("127.0.0.1", 8080)

        # Initial state
        assert client.get_status() == ConnectionStatus.DISCONNECTED

        # Connecting
        client._status = ConnectionStatus.CONNECTING
        assert client.get_status() == ConnectionStatus.CONNECTING

        # Connected
        client._status = ConnectionStatus.CONNECTED
        assert client.get_status() == ConnectionStatus.CONNECTED

        # Disconnecting
        client._status = ConnectionStatus.DISCONNECTING
        assert client.get_status() == ConnectionStatus.DISCONNECTING

        # Error
        client._status = ConnectionStatus.ERROR
        assert client.get_status() == ConnectionStatus.ERROR

    def test_send_sets_error_on_exception(self):
        """Test that send sets error on exception."""
        client = Client("127.0.0.1", 8080)
        client._status = ConnectionStatus.CONNECTED
        client._loop = Mock()
        mock_message = Mock(spec=Message)

        with patch.object(
            client.protocol, "validate_message", return_value=True
        ), patch.object(
            client.protocol, "encode_message", side_effect=Exception("Encode error")
        ):
            result = client.send(mock_message)

        # Should catch exception and set error status
        assert result is False

    def test_transport_initialization(self):
        """Test that transport is initialized with correct parameters."""
        client = Client("192.168.1.100", 9000)

        assert client._transport.host == "192.168.1.100"
        assert client._transport.port == 9000

    def test_received_messages_queue_empty(self):
        """Test that received messages queue starts empty."""
        client = Client("127.0.0.1", 8080)

        assert client._received_messages.empty()

    def test_receive_with_none_timeout_blocks(self):
        """Test that receive with None timeout would block."""
        client = Client("127.0.0.1", 8080)

        # Put a message so it doesn't block
        mock_message = Mock(spec=Message)
        client._received_messages.put(mock_message)

        result = client.receive(timeout=None)

        assert result == mock_message
