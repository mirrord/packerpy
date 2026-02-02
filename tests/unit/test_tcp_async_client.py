"""Unit tests for transports.tcp.async_client module."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from packerpy.transports.tcp.async_client import AsyncTCPClient


def create_mock_writer():
    """Create a properly configured mock writer with sync and async methods."""
    mock_writer = Mock()
    mock_writer.write = Mock()  # Synchronous
    mock_writer.drain = AsyncMock()  # Asynchronous
    mock_writer.close = Mock()  # Synchronous
    mock_writer.wait_closed = AsyncMock()  # Asynchronous
    return mock_writer


@pytest.mark.asyncio
class TestAsyncTCPClient:
    """Test suite for AsyncTCPClient."""

    async def test_initialization(self):
        """Test client initialization."""
        client = AsyncTCPClient("127.0.0.1", 8080)

        assert client.host == "127.0.0.1"
        assert client.port == 8080
        assert client.reader is None
        assert client.writer is None

    @patch("asyncio.open_connection")
    async def test_connect(self, mock_open_connection):
        """Test connection to server."""
        mock_reader = AsyncMock()
        mock_writer = create_mock_writer()
        mock_open_connection.return_value = (mock_reader, mock_writer)

        client = AsyncTCPClient("127.0.0.1", 8080)
        await client.connect()

        mock_open_connection.assert_called_once_with("127.0.0.1", 8080)
        assert client.reader == mock_reader
        assert client.writer == mock_writer

    async def test_send_not_connected(self):
        """Test sending when not connected raises error."""
        client = AsyncTCPClient("127.0.0.1", 8080)

        with pytest.raises(ConnectionError, match="Not connected"):
            await client.send(b"data")

    @patch("asyncio.open_connection")
    async def test_send(self, mock_open_connection):
        """Test sending data."""
        mock_reader = AsyncMock()
        mock_writer = create_mock_writer()
        mock_open_connection.return_value = (mock_reader, mock_writer)

        client = AsyncTCPClient("127.0.0.1", 8080)
        await client.connect()
        await client.send(b"test data")

        mock_writer.write.assert_called_once_with(b"test data")
        mock_writer.drain.assert_called_once()

    async def test_receive_not_connected(self):
        """Test receiving when not connected raises error."""
        client = AsyncTCPClient("127.0.0.1", 8080)

        with pytest.raises(ConnectionError, match="Not connected"):
            await client.receive()

    @patch("asyncio.open_connection")
    async def test_receive(self, mock_open_connection):
        """Test receiving data."""
        mock_reader = AsyncMock()
        mock_reader.read.return_value = b"response data"
        mock_writer = create_mock_writer()
        mock_open_connection.return_value = (mock_reader, mock_writer)

        client = AsyncTCPClient("127.0.0.1", 8080)
        await client.connect()
        data = await client.receive()

        assert data == b"response data"
        mock_reader.read.assert_called_once_with(4096)

    @patch("asyncio.open_connection")
    async def test_receive_custom_buffer_size(self, mock_open_connection):
        """Test receiving with custom buffer size."""
        mock_reader = AsyncMock()
        mock_reader.read.return_value = b"data"
        mock_writer = create_mock_writer()
        mock_open_connection.return_value = (mock_reader, mock_writer)

        client = AsyncTCPClient("127.0.0.1", 8080)
        await client.connect()
        await client.receive(buffer_size=8192)

        mock_reader.read.assert_called_once_with(8192)

    @patch("asyncio.open_connection")
    async def test_close(self, mock_open_connection):
        """Test closing connection."""
        mock_reader = AsyncMock()
        mock_writer = create_mock_writer()
        mock_open_connection.return_value = (mock_reader, mock_writer)

        client = AsyncTCPClient("127.0.0.1", 8080)
        await client.connect()
        await client.close()

        mock_writer.close.assert_called_once()
        mock_writer.wait_closed.assert_called_once()
        assert client.writer is None
        assert client.reader is None

    async def test_close_when_not_connected(self):
        """Test closing when not connected does nothing."""
        client = AsyncTCPClient("127.0.0.1", 8080)
        await client.close()  # Should not raise

        assert client.writer is None
        assert client.reader is None

    @patch("asyncio.open_connection")
    async def test_async_context_manager(self, mock_open_connection):
        """Test using client as async context manager."""
        mock_reader = AsyncMock()
        mock_writer = create_mock_writer()
        mock_open_connection.return_value = (mock_reader, mock_writer)

        async with AsyncTCPClient("127.0.0.1", 8080) as client:
            assert client.writer is not None

        mock_open_connection.assert_called_once()
        mock_writer.close.assert_called_once()
        mock_writer.wait_closed.assert_called_once()

    @patch("asyncio.open_connection")
    async def test_async_context_manager_exception(self, mock_open_connection):
        """Test context manager cleanup on exception."""
        mock_reader = AsyncMock()
        mock_writer = create_mock_writer()
        mock_open_connection.return_value = (mock_reader, mock_writer)

        with pytest.raises(ValueError):
            async with AsyncTCPClient("127.0.0.1", 8080) as client:
                raise ValueError("Test error")

        # Should still close
        mock_writer.close.assert_called_once()
        mock_writer.wait_closed.assert_called_once()

    @patch("asyncio.open_connection")
    async def test_multiple_sends(self, mock_open_connection):
        """Test multiple send operations."""
        mock_reader = AsyncMock()
        mock_writer = create_mock_writer()
        mock_open_connection.return_value = (mock_reader, mock_writer)

        client = AsyncTCPClient("127.0.0.1", 8080)
        await client.connect()

        await client.send(b"data1")
        await client.send(b"data2")
        await client.send(b"data3")

        assert mock_writer.write.call_count == 3
        assert mock_writer.drain.call_count == 3

    @patch("asyncio.open_connection")
    async def test_send_empty_data(self, mock_open_connection):
        """Test sending empty data."""
        mock_reader = AsyncMock()
        mock_writer = create_mock_writer()
        mock_open_connection.return_value = (mock_reader, mock_writer)

        client = AsyncTCPClient("127.0.0.1", 8080)
        await client.connect()
        await client.send(b"")

        mock_writer.write.assert_called_once_with(b"")

    @patch("asyncio.open_connection")
    async def test_receive_empty_response(self, mock_open_connection):
        """Test receiving empty response."""
        mock_reader = AsyncMock()
        mock_reader.read.return_value = b""
        mock_writer = create_mock_writer()
        mock_open_connection.return_value = (mock_reader, mock_writer)

        client = AsyncTCPClient("127.0.0.1", 8080)
        await client.connect()
        data = await client.receive()

        assert data == b""

    @patch("asyncio.open_connection")
    async def test_connection_refused(self, mock_open_connection):
        """Test connection refused error."""
        mock_open_connection.side_effect = ConnectionRefusedError("Connection refused")

        client = AsyncTCPClient("127.0.0.1", 8080)

        with pytest.raises(ConnectionRefusedError):
            await client.connect()

    @patch("asyncio.open_connection")
    async def test_send_receive_cycle(self, mock_open_connection):
        """Test send and receive cycle."""
        mock_reader = AsyncMock()
        mock_reader.read.return_value = b"echo: test"
        mock_writer = create_mock_writer()
        mock_open_connection.return_value = (mock_reader, mock_writer)

        client = AsyncTCPClient("127.0.0.1", 8080)
        await client.connect()

        await client.send(b"test")
        response = await client.receive()

        assert response == b"echo: test"

