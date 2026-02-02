"""Unit tests for transports.tcp.sync_client module."""

import pytest
import socket
from unittest.mock import Mock, patch, MagicMock

from packerpy.transports.tcp.sync_client import SyncTCPClient


class TestSyncTCPClient:
    """Test suite for SyncTCPClient."""

    def test_initialization(self):
        """Test client initialization."""
        client = SyncTCPClient("127.0.0.1", 8080)

        assert client.host == "127.0.0.1"
        assert client.port == 8080
        assert client.timeout == 30.0
        assert client.socket is None

    def test_initialization_with_timeout(self):
        """Test initialization with custom timeout."""
        client = SyncTCPClient("127.0.0.1", 8080, timeout=60.0)

        assert client.timeout == 60.0

    @patch("socket.socket")
    def test_connect(self, mock_socket_class):
        """Test connection to server."""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket

        client = SyncTCPClient("127.0.0.1", 8080, timeout=30.0)
        client.connect()

        mock_socket_class.assert_called_once_with(socket.AF_INET, socket.SOCK_STREAM)
        mock_socket.settimeout.assert_called_once_with(30.0)
        mock_socket.connect.assert_called_once_with(("127.0.0.1", 8080))
        assert client.socket == mock_socket

    @patch("socket.socket")
    def test_send(self, mock_socket_class):
        """Test sending data."""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket

        client = SyncTCPClient("127.0.0.1", 8080)
        client.connect()
        client.send(b"test data")

        mock_socket.sendall.assert_called_once_with(b"test data")

    def test_send_not_connected(self):
        """Test sending when not connected raises error."""
        client = SyncTCPClient("127.0.0.1", 8080)

        with pytest.raises(ConnectionError, match="Not connected"):
            client.send(b"data")

    @patch("socket.socket")
    def test_receive(self, mock_socket_class):
        """Test receiving data."""
        mock_socket = Mock()
        mock_socket.recv.return_value = b"response data"
        mock_socket_class.return_value = mock_socket

        client = SyncTCPClient("127.0.0.1", 8080)
        client.connect()
        data = client.receive()

        assert data == b"response data"
        mock_socket.recv.assert_called_once_with(4096)

    @patch("socket.socket")
    def test_receive_custom_buffer_size(self, mock_socket_class):
        """Test receiving with custom buffer size."""
        mock_socket = Mock()
        mock_socket.recv.return_value = b"data"
        mock_socket_class.return_value = mock_socket

        client = SyncTCPClient("127.0.0.1", 8080)
        client.connect()
        client.receive(buffer_size=8192)

        mock_socket.recv.assert_called_once_with(8192)

    def test_receive_not_connected(self):
        """Test receiving when not connected raises error."""
        client = SyncTCPClient("127.0.0.1", 8080)

        with pytest.raises(ConnectionError, match="Not connected"):
            client.receive()

    @patch("socket.socket")
    def test_close(self, mock_socket_class):
        """Test closing connection."""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket

        client = SyncTCPClient("127.0.0.1", 8080)
        client.connect()
        client.close()

        mock_socket.close.assert_called_once()
        assert client.socket is None

    def test_close_when_not_connected(self):
        """Test closing when not connected does nothing."""
        client = SyncTCPClient("127.0.0.1", 8080)
        client.close()  # Should not raise

        assert client.socket is None

    @patch("socket.socket")
    def test_context_manager(self, mock_socket_class):
        """Test using client as context manager."""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket

        with SyncTCPClient("127.0.0.1", 8080) as client:
            assert client.socket is not None

        mock_socket.connect.assert_called_once()
        mock_socket.close.assert_called_once()

    @patch("socket.socket")
    def test_context_manager_exception(self, mock_socket_class):
        """Test context manager cleanup on exception."""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket

        with pytest.raises(ValueError):
            with SyncTCPClient("127.0.0.1", 8080) as client:
                raise ValueError("Test error")

        # Should still close
        mock_socket.close.assert_called_once()

    @patch("socket.socket")
    def test_multiple_sends(self, mock_socket_class):
        """Test multiple send operations."""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket

        client = SyncTCPClient("127.0.0.1", 8080)
        client.connect()

        client.send(b"data1")
        client.send(b"data2")
        client.send(b"data3")

        assert mock_socket.sendall.call_count == 3

    @patch("socket.socket")
    def test_send_empty_data(self, mock_socket_class):
        """Test sending empty data."""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket

        client = SyncTCPClient("127.0.0.1", 8080)
        client.connect()
        client.send(b"")

        mock_socket.sendall.assert_called_once_with(b"")

    @patch("socket.socket")
    def test_receive_empty_response(self, mock_socket_class):
        """Test receiving empty response."""
        mock_socket = Mock()
        mock_socket.recv.return_value = b""
        mock_socket_class.return_value = mock_socket

        client = SyncTCPClient("127.0.0.1", 8080)
        client.connect()
        data = client.receive()

        assert data == b""

    @patch("socket.socket")
    def test_connection_refused(self, mock_socket_class):
        """Test connection refused error."""
        mock_socket = Mock()
        mock_socket.connect.side_effect = ConnectionRefusedError("Connection refused")
        mock_socket_class.return_value = mock_socket

        client = SyncTCPClient("127.0.0.1", 8080)

        with pytest.raises(ConnectionRefusedError):
            client.connect()

    @patch("socket.socket")
    def test_timeout_error(self, mock_socket_class):
        """Test socket timeout error."""
        mock_socket = Mock()
        mock_socket.recv.side_effect = socket.timeout("Timeout")
        mock_socket_class.return_value = mock_socket

        client = SyncTCPClient("127.0.0.1", 8080, timeout=1.0)
        client.connect()

        with pytest.raises(socket.timeout):
            client.receive()
