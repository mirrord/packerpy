"""Unit tests for transports.tcp.sync_server module."""

import pytest
import socket
from unittest.mock import Mock, patch, MagicMock

from packerpy.transports.tcp.sync_server import SyncTCPServer


class TestSyncTCPServer:
    """Test suite for SyncTCPServer."""

    def test_initialization(self):
        """Test server initialization."""
        handler = Mock()
        server = SyncTCPServer("0.0.0.0", 8080, handler)

        assert server.host == "0.0.0.0"
        assert server.port == 8080
        assert server.handler == handler
        assert server.socket is None
        assert server.running is False

    @patch("socket.socket")
    def test_start(self, mock_socket_class):
        """Test starting the server."""
        mock_socket = Mock()
        mock_socket.accept.side_effect = KeyboardInterrupt()  # Stop after one iteration
        mock_socket_class.return_value = mock_socket

        handler = Mock()
        server = SyncTCPServer("0.0.0.0", 8080, handler)

        try:
            server.start()
        except KeyboardInterrupt:
            pass

        mock_socket_class.assert_called_once_with(socket.AF_INET, socket.SOCK_STREAM)
        mock_socket.setsockopt.assert_called_once_with(
            socket.SOL_SOCKET, socket.SO_REUSEADDR, 1
        )
        mock_socket.bind.assert_called_once_with(("0.0.0.0", 8080))
        mock_socket.listen.assert_called_once_with(5)
        assert server.running is True

    @patch("socket.socket")
    def test_handle_client(self, mock_socket_class):
        """Test handling a client connection."""
        mock_server_socket = Mock()
        mock_client_socket = Mock()
        mock_client_socket.recv.return_value = b"request data"
        mock_server_socket.accept.return_value = (
            mock_client_socket,
            ("127.0.0.1", 54321),
        )
        mock_socket_class.return_value = mock_server_socket

        handler = Mock(return_value=b"response data")
        server = SyncTCPServer("0.0.0.0", 8080, handler)

        # Manually call _handle_client
        server._handle_client(mock_client_socket, ("127.0.0.1", 54321))

        mock_client_socket.recv.assert_called_once_with(4096)
        handler.assert_called_once_with(b"request data", ("127.0.0.1", 54321))
        mock_client_socket.sendall.assert_called_once_with(b"response data")
        mock_client_socket.close.assert_called_once()

    @patch("socket.socket")
    def test_handle_client_no_data(self, mock_socket_class):
        """Test handling client when no data received."""
        mock_client_socket = Mock()
        mock_client_socket.recv.return_value = b""

        handler = Mock()
        server = SyncTCPServer("0.0.0.0", 8080, handler)
        server._handle_client(mock_client_socket, ("127.0.0.1", 54321))

        # Handler should not be called if no data
        handler.assert_not_called()
        mock_client_socket.close.assert_called_once()

    @patch("socket.socket")
    def test_stop(self, mock_socket_class):
        """Test stopping the server."""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket

        handler = Mock()
        server = SyncTCPServer("0.0.0.0", 8080, handler)
        server.socket = mock_socket
        server.running = True

        server.stop()

        assert server.running is False
        mock_socket.close.assert_called_once()
        assert server.socket is None

    def test_stop_when_not_running(self):
        """Test stopping when not running."""
        handler = Mock()
        server = SyncTCPServer("0.0.0.0", 8080, handler)

        server.stop()  # Should not raise

        assert server.running is False
        assert server.socket is None

    @patch("socket.socket")
    def test_handler_exception(self, mock_socket_class):
        """Test handling exception in handler."""
        mock_client_socket = Mock()
        mock_client_socket.recv.return_value = b"data"

        handler = Mock(side_effect=Exception("Handler error"))
        server = SyncTCPServer("0.0.0.0", 8080, handler)

        # Should raise the exception
        with pytest.raises(Exception, match="Handler error"):
            server._handle_client(mock_client_socket, ("127.0.0.1", 54321))

        # Socket should still be closed in finally block
        mock_client_socket.close.assert_called_once()

    @patch("socket.socket")
    def test_handler_returns_none(self, mock_socket_class):
        """Test when handler returns None."""
        mock_client_socket = Mock()
        mock_client_socket.recv.return_value = b"data"

        handler = Mock(return_value=None)
        server = SyncTCPServer("0.0.0.0", 8080, handler)

        # Should handle None response
        server._handle_client(mock_client_socket, ("127.0.0.1", 54321))

        handler.assert_called_once()
        mock_client_socket.close.assert_called_once()

    @patch("socket.socket")
    def test_multiple_clients(self, mock_socket_class):
        """Test handling multiple client connections."""
        mock_client1 = Mock()
        mock_client1.recv.return_value = b"data1"

        mock_client2 = Mock()
        mock_client2.recv.return_value = b"data2"

        handler = Mock(side_effect=[b"response1", b"response2"])
        server = SyncTCPServer("0.0.0.0", 8080, handler)

        server._handle_client(mock_client1, ("127.0.0.1", 54321))
        server._handle_client(mock_client2, ("127.0.0.1", 54322))

        assert handler.call_count == 2
        mock_client1.sendall.assert_called_once_with(b"response1")
        mock_client2.sendall.assert_called_once_with(b"response2")

    @patch("socket.socket")
    def test_bind_error(self, mock_socket_class):
        """Test bind error handling."""
        mock_socket = Mock()
        mock_socket.bind.side_effect = OSError("Address already in use")
        mock_socket_class.return_value = mock_socket

        handler = Mock()
        server = SyncTCPServer("0.0.0.0", 8080, handler)

        with pytest.raises(OSError, match="Address already in use"):
            server.start()

    @patch("socket.socket")
    def test_accept_error(self, mock_socket_class, capsys):
        """Test accept error handling."""
        mock_socket = Mock()
        # First raise an error, then stop the loop
        mock_socket.accept.side_effect = [OSError("Accept error"), KeyboardInterrupt()]
        mock_socket_class.return_value = mock_socket

        handler = Mock()
        server = SyncTCPServer("0.0.0.0", 8080, handler)

        try:
            server.start()
        except KeyboardInterrupt:
            pass

        # Error should be printed
        captured = capsys.readouterr()
        assert "Error handling client" in captured.out
