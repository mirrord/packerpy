"""Unit tests for transports.udp.async_socket module."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from packerpy.transports.udp.async_socket import AsyncUDPSocket, AsyncUDPProtocol


class TestAsyncUDPProtocol:
    """Test suite for AsyncUDPProtocol."""

    def test_initialization(self):
        """Test protocol initialization."""
        protocol = AsyncUDPProtocol()

        assert protocol.transport is None
        assert isinstance(protocol.received_data, asyncio.Queue)

    def test_connection_made(self):
        """Test connection_made callback."""
        protocol = AsyncUDPProtocol()
        mock_transport = Mock()

        protocol.connection_made(mock_transport)

        assert protocol.transport == mock_transport

    def test_datagram_received(self):
        """Test datagram_received callback."""
        protocol = AsyncUDPProtocol()

        protocol.datagram_received(b"test data", ("127.0.0.1", 9000))

        # Data should be in queue
        assert not protocol.received_data.empty()

    @pytest.mark.asyncio
    async def test_datagram_received_can_be_retrieved(self):
        """Test that received datagrams can be retrieved from queue."""
        protocol = AsyncUDPProtocol()

        protocol.datagram_received(b"data1", ("127.0.0.1", 9000))
        protocol.datagram_received(b"data2", ("127.0.0.1", 9001))

        data1, addr1 = await protocol.received_data.get()
        data2, addr2 = await protocol.received_data.get()

        assert data1 == b"data1"
        assert addr1 == ("127.0.0.1", 9000)
        assert data2 == b"data2"
        assert addr2 == ("127.0.0.1", 9001)

    def test_error_received(self, capsys):
        """Test error_received callback."""
        protocol = AsyncUDPProtocol()

        protocol.error_received(Exception("Test error"))

        captured = capsys.readouterr()
        assert "UDP error" in captured.out


@pytest.mark.asyncio
class TestAsyncUDPSocket:
    """Test suite for AsyncUDPSocket."""

    async def test_initialization(self):
        """Test socket initialization."""
        sock = AsyncUDPSocket("0.0.0.0", 8080)

        assert sock.host == "0.0.0.0"
        assert sock.port == 8080
        assert sock.transport is None
        assert sock.protocol is None

    async def test_initialization_auto_port(self):
        """Test initialization with auto-assigned port."""
        sock = AsyncUDPSocket("0.0.0.0", 0)

        assert sock.port == 0

    @patch("asyncio.get_event_loop")
    async def test_bind(self, mock_get_loop):
        """Test binding socket."""
        mock_transport = Mock()
        mock_protocol = AsyncUDPProtocol()

        mock_loop = Mock()
        mock_loop.create_datagram_endpoint = AsyncMock(
            return_value=(mock_transport, mock_protocol)
        )
        mock_get_loop.return_value = mock_loop

        sock = AsyncUDPSocket("0.0.0.0", 8080)
        await sock.bind()

        mock_loop.create_datagram_endpoint.assert_called_once()
        assert sock.transport == mock_transport
        assert isinstance(sock.protocol, AsyncUDPProtocol)

    async def test_send_to_not_bound(self):
        """Test sending when not bound raises error."""
        sock = AsyncUDPSocket("0.0.0.0", 8080)

        with pytest.raises(ConnectionError, match="Socket not bound"):
            await sock.send_to(b"data", ("127.0.0.1", 9000))

    @patch("asyncio.get_event_loop")
    async def test_send_to(self, mock_get_loop):
        """Test sending data to address."""
        mock_transport = Mock()
        mock_protocol = AsyncUDPProtocol()

        mock_loop = Mock()
        mock_loop.create_datagram_endpoint = AsyncMock(
            return_value=(mock_transport, mock_protocol)
        )
        mock_get_loop.return_value = mock_loop

        sock = AsyncUDPSocket("0.0.0.0", 8080)
        await sock.bind()
        await sock.send_to(b"test data", ("127.0.0.1", 9000))

        mock_transport.sendto.assert_called_once_with(b"test data", ("127.0.0.1", 9000))

    async def test_receive_from_not_bound(self):
        """Test receiving when not bound raises error."""
        sock = AsyncUDPSocket("0.0.0.0", 8080)

        with pytest.raises(ConnectionError, match="Socket not bound"):
            await sock.receive_from()

    @patch("asyncio.get_event_loop")
    async def test_receive_from(self, mock_get_loop):
        """Test receiving data from sender."""
        mock_transport = Mock()
        mock_protocol = AsyncUDPProtocol()

        mock_loop = Mock()
        mock_loop.create_datagram_endpoint = AsyncMock(
            return_value=(mock_transport, mock_protocol)
        )
        mock_get_loop.return_value = mock_loop

        sock = AsyncUDPSocket("0.0.0.0", 8080)
        await sock.bind()

        # Simulate received data
        sock.protocol.datagram_received(b"response data", ("127.0.0.1", 9000))

        data, address = await sock.receive_from()

        assert data == b"response data"
        assert address == ("127.0.0.1", 9000)

    @patch("asyncio.get_event_loop")
    async def test_close(self, mock_get_loop):
        """Test closing socket."""
        mock_transport = Mock()
        mock_protocol = AsyncUDPProtocol()

        mock_loop = Mock()
        mock_loop.create_datagram_endpoint = AsyncMock(
            return_value=(mock_transport, mock_protocol)
        )
        mock_get_loop.return_value = mock_loop

        sock = AsyncUDPSocket("0.0.0.0", 8080)
        await sock.bind()
        await sock.close()

        mock_transport.close.assert_called_once()
        assert sock.transport is None
        assert sock.protocol is None

    async def test_close_when_not_bound(self):
        """Test closing when not bound does nothing."""
        sock = AsyncUDPSocket("0.0.0.0", 8080)
        await sock.close()  # Should not raise

        assert sock.transport is None
        assert sock.protocol is None

    @patch("asyncio.get_event_loop")
    async def test_async_context_manager(self, mock_get_loop):
        """Test using socket as async context manager."""
        mock_transport = Mock()
        mock_protocol = AsyncUDPProtocol()

        mock_loop = Mock()
        mock_loop.create_datagram_endpoint = AsyncMock(
            return_value=(mock_transport, mock_protocol)
        )
        mock_get_loop.return_value = mock_loop

        async with AsyncUDPSocket("0.0.0.0", 8080) as sock:
            assert sock.transport is not None

        mock_transport.close.assert_called_once()

    @patch("asyncio.get_event_loop")
    async def test_async_context_manager_exception(self, mock_get_loop):
        """Test context manager cleanup on exception."""
        mock_transport = Mock()
        mock_protocol = AsyncUDPProtocol()

        mock_loop = Mock()
        mock_loop.create_datagram_endpoint = AsyncMock(
            return_value=(mock_transport, mock_protocol)
        )
        mock_get_loop.return_value = mock_loop

        with pytest.raises(ValueError):
            async with AsyncUDPSocket("0.0.0.0", 8080) as sock:
                raise ValueError("Test error")

        # Should still close
        mock_transport.close.assert_called_once()

    @patch("asyncio.get_event_loop")
    async def test_multiple_sends(self, mock_get_loop):
        """Test multiple send operations."""
        mock_transport = Mock()
        mock_protocol = AsyncUDPProtocol()

        mock_loop = Mock()
        mock_loop.create_datagram_endpoint = AsyncMock(
            return_value=(mock_transport, mock_protocol)
        )
        mock_get_loop.return_value = mock_loop

        sock = AsyncUDPSocket("0.0.0.0", 8080)
        await sock.bind()

        await sock.send_to(b"data1", ("127.0.0.1", 9000))
        await sock.send_to(b"data2", ("127.0.0.1", 9001))
        await sock.send_to(b"data3", ("192.168.1.1", 8080))

        assert mock_transport.sendto.call_count == 3

    @patch("asyncio.get_event_loop")
    async def test_send_empty_data(self, mock_get_loop):
        """Test sending empty data."""
        mock_transport = Mock()
        mock_protocol = AsyncUDPProtocol()

        mock_loop = Mock()
        mock_loop.create_datagram_endpoint = AsyncMock(
            return_value=(mock_transport, mock_protocol)
        )
        mock_get_loop.return_value = mock_loop

        sock = AsyncUDPSocket("0.0.0.0", 8080)
        await sock.bind()
        await sock.send_to(b"", ("127.0.0.1", 9000))

        mock_transport.sendto.assert_called_once_with(b"", ("127.0.0.1", 9000))

    @patch("asyncio.get_event_loop")
    async def test_receive_empty_data(self, mock_get_loop):
        """Test receiving empty data."""
        mock_transport = Mock()
        mock_protocol = AsyncUDPProtocol()

        mock_loop = Mock()
        mock_loop.create_datagram_endpoint = AsyncMock(
            return_value=(mock_transport, mock_protocol)
        )
        mock_get_loop.return_value = mock_loop

        sock = AsyncUDPSocket("0.0.0.0", 8080)
        await sock.bind()

        sock.protocol.datagram_received(b"", ("127.0.0.1", 9000))

        data, address = await sock.receive_from()

        assert data == b""
        assert address == ("127.0.0.1", 9000)

    @patch("asyncio.get_event_loop")
    async def test_multiple_receives(self, mock_get_loop):
        """Test receiving multiple datagrams."""
        mock_transport = Mock()
        mock_protocol = AsyncUDPProtocol()

        mock_loop = Mock()
        mock_loop.create_datagram_endpoint = AsyncMock(
            return_value=(mock_transport, mock_protocol)
        )
        mock_get_loop.return_value = mock_loop

        sock = AsyncUDPSocket("0.0.0.0", 8080)
        await sock.bind()

        # Simulate multiple received datagrams
        sock.protocol.datagram_received(b"data1", ("127.0.0.1", 9000))
        sock.protocol.datagram_received(b"data2", ("127.0.0.1", 9001))
        sock.protocol.datagram_received(b"data3", ("192.168.1.1", 8080))

        results = []
        for _ in range(3):
            results.append(await sock.receive_from())

        assert len(results) == 3
        assert results[0] == (b"data1", ("127.0.0.1", 9000))
        assert results[1] == (b"data2", ("127.0.0.1", 9001))
        assert results[2] == (b"data3", ("192.168.1.1", 8080))
