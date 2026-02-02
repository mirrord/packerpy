"""Unit tests for server module."""

import threading
from unittest.mock import Mock, patch

from packerpy.server import Server, ConnectionStatus
from packerpy.protocols.protocol import Protocol
from packerpy.protocols.message import Message


class TestServerConnectionStatus:
    """Test ConnectionStatus enum for server."""

    def test_status_values(self):
        """Test connection status enum values."""
        assert ConnectionStatus.STOPPED.value == "stopped"
        assert ConnectionStatus.STARTING.value == "starting"
        assert ConnectionStatus.RUNNING.value == "running"
        assert ConnectionStatus.STOPPING.value == "stopping"
        assert ConnectionStatus.ERROR.value == "error"


class TestServer:
    """Test suite for Server class."""

    def test_initialization(self):
        """Test server initialization."""
        server = Server("0.0.0.0", 8080)

        assert server.host == "0.0.0.0"
        assert server.port == 8080
        assert isinstance(server.protocol, Protocol)
        assert server.message_handler is None
        assert server._status == ConnectionStatus.STOPPED
        assert server._server_thread is None
        assert server._loop is None
        assert server._transport is None
        assert server._error is None

    def test_initialization_with_handler(self):
        """Test server initialization with message handler."""
        handler = Mock()
        server = Server("0.0.0.0", 8080, message_handler=handler)

        assert server.message_handler == handler

    def test_initialization_defaults(self):
        """Test server initialization with defaults."""
        server = Server()

        assert server.host == "0.0.0.0"
        assert server.port == 8080

    def test_handle_raw_data_decode_failure(self):
        """Test handling data that fails to decode."""
        server = Server("0.0.0.0", 8080)

        with patch.object(server.protocol, "decode", return_value=None):
            result = server._handle_raw_data(b"invalid", ("127.0.0.1", 54321))

        # Failed decode returns None instead of error message
        assert result is None

    def test_handle_raw_data_invalid_message(self):
        """Test handling invalid message."""
        server = Server("0.0.0.0", 8080)
        mock_message = Mock(spec=Message)

        with patch.object(
            server.protocol, "decode", return_value=(mock_message, b"")
        ), patch.object(server.protocol, "validate_message", return_value=False):
            result = server._handle_raw_data(b"data", ("127.0.0.1", 54321))

        # Invalid message returns None instead of error message
        assert result is None

    def test_handle_raw_data_stores_in_queue(self):
        """Test that valid messages are stored in queue."""
        server = Server("0.0.0.0", 8080)
        mock_message = Mock(spec=Message)

        with patch.object(
            server.protocol, "decode", return_value=(mock_message, b"")
        ), patch.object(server.protocol, "validate_message", return_value=True):

            server._handle_raw_data(b"data", ("127.0.0.1", 54321))

        assert not server._received_messages.empty()
        msg, addr = server._received_messages.get()
        assert msg == mock_message
        assert addr == ("127.0.0.1", 54321)

    def test_handle_raw_data_with_handler(self):
        """Test handling data with message handler."""
        handler = Mock(return_value=Mock(spec=Message))
        server = Server("0.0.0.0", 8080, message_handler=handler)
        mock_message = Mock(spec=Message)

        with patch.object(
            server.protocol, "decode", return_value=(mock_message, b"")
        ), patch.object(
            server.protocol, "validate_message", return_value=True
        ), patch.object(
            server.protocol, "encode_message", return_value=b"response"
        ):

            result = server._handle_raw_data(b"data", ("127.0.0.1", 54321))

        handler.assert_called_once_with(mock_message, ("127.0.0.1", 54321))
        assert result == b"response"

    def test_handle_raw_data_handler_returns_none(self):
        """Test when message handler returns None."""
        handler = Mock(return_value=None)
        server = Server("0.0.0.0", 8080, message_handler=handler)
        mock_message = Mock(spec=Message)

        with patch.object(
            server.protocol, "decode", return_value=(mock_message, b"")
        ), patch.object(server.protocol, "validate_message", return_value=True):

            result = server._handle_raw_data(b"data", ("127.0.0.1", 54321))

        assert result is None

    @patch("packerpy.server.AsyncTCPServer")
    def test_start_creates_thread(self, mock_async_server):
        """Test that start creates background thread."""
        server = Server("0.0.0.0", 8080)

        with patch.object(threading.Thread, "start"):
            server.start()

        assert server._server_thread is not None

    def test_stop(self):
        """Test stopping server."""
        server = Server("0.0.0.0", 8080)
        server._status = ConnectionStatus.RUNNING
        server._loop = Mock()
        mock_transport = Mock()
        server._transport = mock_transport
        server._server_thread = Mock()

        # Mock run_coroutine_threadsafe to avoid creating unawaited coroutines
        with patch("asyncio.run_coroutine_threadsafe") as mock_run_coro:
            mock_future = Mock()
            mock_future.result = Mock(return_value=None)
            mock_run_coro.return_value = mock_future

            server.stop()

        assert server._status == ConnectionStatus.STOPPING

    def test_get_status(self):
        """Test getting server status."""
        server = Server("0.0.0.0", 8080)
        server._status = ConnectionStatus.RUNNING

        status = server.get_status()

        assert status == ConnectionStatus.RUNNING

    def test_get_error(self):
        """Test getting last error."""
        server = Server("0.0.0.0", 8080)
        test_error = ValueError("Test error")
        server._error = test_error

        error = server.get_error()

        assert error == test_error

    def test_get_error_when_none(self):
        """Test getting error when none exists."""
        server = Server("0.0.0.0", 8080)

        error = server.get_error()

        assert error is None

    def test_receive_with_timeout(self):
        """Test receiving message with timeout."""
        server = Server("0.0.0.0", 8080)

        result = server.receive(timeout=0.1)

        assert result is None

    def test_receive_returns_message_from_queue(self):
        """Test receiving returns message and address from queue."""
        server = Server("0.0.0.0", 8080)
        mock_message = Mock(spec=Message)
        address = ("127.0.0.1", 54321)
        server._received_messages.put((mock_message, address))

        result = server.receive(timeout=0.1)

        assert result == (mock_message, address)

    def test_receive_non_blocking(self):
        """Test non-blocking receive."""
        server = Server("0.0.0.0", 8080)

        result = server.receive(timeout=0)

        assert result is None

    def test_send_invalid_message(self, capsys):
        """Test sending invalid message returns False."""
        server = Server("0.0.0.0", 8080)
        mock_message = Mock(spec=Message)

        with patch.object(server.protocol, "validate_message", return_value=False):
            result = server.send(mock_message, ("127.0.0.1", 54321))

        assert result is False
        captured = capsys.readouterr()
        assert "Invalid message" in captured.out

    def test_send_prints_warning(self, capsys):
        """Test that send prints warning about connection management."""
        server = Server("0.0.0.0", 8080)
        mock_message = Mock(spec=Message)

        with patch.object(server.protocol, "validate_message", return_value=True):
            result = server.send(mock_message, ("127.0.0.1", 54321))

        captured = capsys.readouterr()
        assert "Warning" in captured.out
        assert result is False

    def test_status_transitions(self):
        """Test server status transitions."""
        server = Server("0.0.0.0", 8080)

        # Initial state
        assert server.get_status() == ConnectionStatus.STOPPED

        # Starting
        server._status = ConnectionStatus.STARTING
        assert server.get_status() == ConnectionStatus.STARTING

        # Running
        server._status = ConnectionStatus.RUNNING
        assert server.get_status() == ConnectionStatus.RUNNING

        # Stopping
        server._status = ConnectionStatus.STOPPING
        assert server.get_status() == ConnectionStatus.STOPPING

        # Error
        server._status = ConnectionStatus.ERROR
        assert server.get_status() == ConnectionStatus.ERROR

    def test_protocol_decode_and_encode(self):
        """Test that protocol is used for decode and encode."""
        server = Server("0.0.0.0", 8080)

        assert isinstance(server.protocol, Protocol)
        assert hasattr(server.protocol, "decode_message")
        assert hasattr(server.protocol, "encode_message")
        assert hasattr(server.protocol, "validate_message")

    def test_multiple_messages_in_queue(self):
        """Test receiving multiple messages from queue."""
        server = Server("0.0.0.0", 8080)

        msg1 = Mock(spec=Message)
        msg2 = Mock(spec=Message)
        addr1 = ("127.0.0.1", 54321)
        addr2 = ("127.0.0.1", 54322)

        server._received_messages.put((msg1, addr1))
        server._received_messages.put((msg2, addr2))

        result1 = server.receive(timeout=0.1)
        result2 = server.receive(timeout=0.1)
        result3 = server.receive(timeout=0.1)

        assert result1 == (msg1, addr1)
        assert result2 == (msg2, addr2)
        assert result3 is None

    def test_received_messages_queue_empty(self):
        """Test that received messages queue starts empty."""
        server = Server("0.0.0.0", 8080)

        assert server._received_messages.empty()

    def test_error_message_creation(self):
        """Test that decode errors return None instead of error messages."""
        server = Server("0.0.0.0", 8080)

        with patch.object(server.protocol, "decode", return_value=None):
            result = server._handle_raw_data(b"invalid", ("127.0.0.1", 54321))

        # Decode failures now return None
        assert result is None

    def test_handler_called_with_message_and_address(self):
        """Test that handler is called with correct parameters."""
        handler = Mock(return_value=None)
        server = Server("0.0.0.0", 8080, message_handler=handler)
        mock_message = Mock(spec=Message)
        address = ("192.168.1.100", 12345)

        with patch.object(
            server.protocol, "decode", return_value=(mock_message, b"")
        ), patch.object(server.protocol, "validate_message", return_value=True):

            server._handle_raw_data(b"data", address)

        handler.assert_called_once_with(mock_message, address)

    def test_receive_with_none_timeout_blocks(self):
        """Test that receive with None timeout would block."""
        server = Server("0.0.0.0", 8080)

        # Put a message so it doesn't block
        mock_message = Mock(spec=Message)
        server._received_messages.put((mock_message, ("127.0.0.1", 54321)))

        result = server.receive(timeout=None)

        assert result == (mock_message, ("127.0.0.1", 54321))
