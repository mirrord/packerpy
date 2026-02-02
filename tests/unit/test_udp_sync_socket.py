"""Unit tests for transports.udp.sync_socket module."""

import pytest
import socket
from unittest.mock import Mock, patch

from packerpy.transports.udp.sync_socket import SyncUDPSocket


class TestSyncUDPSocket:
    """Test suite for SyncUDPSocket."""

    def test_initialization(self):
        """Test socket initialization."""
        sock = SyncUDPSocket("0.0.0.0", 8080)

        assert sock.host == "0.0.0.0"
        assert sock.port == 8080
        assert sock.socket is None

    def test_initialization_auto_port(self):
        """Test initialization with auto-assigned port."""
        sock = SyncUDPSocket("0.0.0.0", 0)

        assert sock.port == 0

    @patch("socket.socket")
    def test_bind(self, mock_socket_class):
        """Test binding socket."""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket

        sock = SyncUDPSocket("0.0.0.0", 8080)
        sock.bind()

        mock_socket_class.assert_called_once_with(socket.AF_INET, socket.SOCK_DGRAM)
        mock_socket.bind.assert_called_once_with(("0.0.0.0", 8080))
        assert sock.socket == mock_socket

    @patch("socket.socket")
    def test_bind_auto_port(self, mock_socket_class):
        """Test binding with auto-assigned port."""
        mock_socket = Mock()
        mock_socket.getsockname.return_value = ("0.0.0.0", 54321)
        mock_socket_class.return_value = mock_socket

        sock = SyncUDPSocket("0.0.0.0", 0)
        sock.bind()

        # Port should be updated from getsockname
        assert sock.port == 54321

    def test_send_to_not_bound(self):
        """Test sending when not bound raises error."""
        sock = SyncUDPSocket("0.0.0.0", 8080)

        with pytest.raises(ConnectionError, match="Socket not bound"):
            sock.send_to(b"data", ("127.0.0.1", 9000))

    @patch("socket.socket")
    def test_send_to(self, mock_socket_class):
        """Test sending data to address."""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket

        sock = SyncUDPSocket("0.0.0.0", 8080)
        sock.bind()
        sock.send_to(b"test data", ("127.0.0.1", 9000))

        mock_socket.sendto.assert_called_once_with(b"test data", ("127.0.0.1", 9000))

    def test_receive_from_not_bound(self):
        """Test receiving when not bound raises error."""
        sock = SyncUDPSocket("0.0.0.0", 8080)

        with pytest.raises(ConnectionError, match="Socket not bound"):
            sock.receive_from()

    @patch("socket.socket")
    def test_receive_from(self, mock_socket_class):
        """Test receiving data from sender."""
        mock_socket = Mock()
        mock_socket.recvfrom.return_value = (b"response data", ("127.0.0.1", 9000))
        mock_socket_class.return_value = mock_socket

        sock = SyncUDPSocket("0.0.0.0", 8080)
        sock.bind()
        data, address = sock.receive_from()

        assert data == b"response data"
        assert address == ("127.0.0.1", 9000)
        mock_socket.recvfrom.assert_called_once_with(4096)

    @patch("socket.socket")
    def test_receive_from_custom_buffer_size(self, mock_socket_class):
        """Test receiving with custom buffer size."""
        mock_socket = Mock()
        mock_socket.recvfrom.return_value = (b"data", ("127.0.0.1", 9000))
        mock_socket_class.return_value = mock_socket

        sock = SyncUDPSocket("0.0.0.0", 8080)
        sock.bind()
        sock.receive_from(buffer_size=8192)

        mock_socket.recvfrom.assert_called_once_with(8192)

    @patch("socket.socket")
    def test_close(self, mock_socket_class):
        """Test closing socket."""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket

        sock = SyncUDPSocket("0.0.0.0", 8080)
        sock.bind()
        sock.close()

        mock_socket.close.assert_called_once()
        assert sock.socket is None

    def test_close_when_not_bound(self):
        """Test closing when not bound does nothing."""
        sock = SyncUDPSocket("0.0.0.0", 8080)
        sock.close()  # Should not raise

        assert sock.socket is None

    @patch("socket.socket")
    def test_context_manager(self, mock_socket_class):
        """Test using socket as context manager."""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket

        with SyncUDPSocket("0.0.0.0", 8080) as sock:
            assert sock.socket is not None

        mock_socket.bind.assert_called_once()
        mock_socket.close.assert_called_once()

    @patch("socket.socket")
    def test_context_manager_exception(self, mock_socket_class):
        """Test context manager cleanup on exception."""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket

        with pytest.raises(ValueError):
            with SyncUDPSocket("0.0.0.0", 8080) as sock:
                raise ValueError("Test error")

        # Should still close
        mock_socket.close.assert_called_once()

    @patch("socket.socket")
    def test_multiple_sends(self, mock_socket_class):
        """Test multiple send operations."""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket

        sock = SyncUDPSocket("0.0.0.0", 8080)
        sock.bind()

        sock.send_to(b"data1", ("127.0.0.1", 9000))
        sock.send_to(b"data2", ("127.0.0.1", 9001))
        sock.send_to(b"data3", ("192.168.1.1", 8080))

        assert mock_socket.sendto.call_count == 3

    @patch("socket.socket")
    def test_send_empty_data(self, mock_socket_class):
        """Test sending empty data."""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket

        sock = SyncUDPSocket("0.0.0.0", 8080)
        sock.bind()
        sock.send_to(b"", ("127.0.0.1", 9000))

        mock_socket.sendto.assert_called_once_with(b"", ("127.0.0.1", 9000))

    @patch("socket.socket")
    def test_receive_empty_data(self, mock_socket_class):
        """Test receiving empty data."""
        mock_socket = Mock()
        mock_socket.recvfrom.return_value = (b"", ("127.0.0.1", 9000))
        mock_socket_class.return_value = mock_socket

        sock = SyncUDPSocket("0.0.0.0", 8080)
        sock.bind()
        data, address = sock.receive_from()

        assert data == b""
        assert address == ("127.0.0.1", 9000)

    @patch("socket.socket")
    def test_bind_error(self, mock_socket_class):
        """Test bind error handling."""
        mock_socket = Mock()
        mock_socket.bind.side_effect = OSError("Address already in use")
        mock_socket_class.return_value = mock_socket

        sock = SyncUDPSocket("0.0.0.0", 8080)

        with pytest.raises(OSError, match="Address already in use"):
            sock.bind()

    @patch("socket.socket")
    def test_send_to_different_addresses(self, mock_socket_class):
        """Test sending to different addresses."""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket

        sock = SyncUDPSocket("0.0.0.0", 8080)
        sock.bind()

        addresses = [("127.0.0.1", 9000), ("192.168.1.1", 8080), ("10.0.0.1", 5555)]

        for i, addr in enumerate(addresses):
            sock.send_to(f"data{i}".encode(), addr)

        assert mock_socket.sendto.call_count == 3

    @patch("socket.socket")
    def test_receive_from_different_senders(self, mock_socket_class):
        """Test receiving from different senders."""
        mock_socket = Mock()
        responses = [
            (b"data1", ("127.0.0.1", 9000)),
            (b"data2", ("192.168.1.1", 8080)),
            (b"data3", ("10.0.0.1", 5555)),
        ]
        mock_socket.recvfrom.side_effect = responses
        mock_socket_class.return_value = mock_socket

        sock = SyncUDPSocket("0.0.0.0", 8080)
        sock.bind()

        results = []
        for _ in range(3):
            results.append(sock.receive_from())

        assert results == responses
