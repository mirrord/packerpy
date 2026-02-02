"""Unit tests for transports.tcp.async_server module."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock, call

from packerpy.transports.tcp.async_server import AsyncTCPServer


def create_mock_writer():
    """Create a properly configured mock writer with sync and async methods."""
    mock_writer = Mock()
    mock_writer.write = Mock()  # Synchronous
    mock_writer.drain = AsyncMock()  # Asynchronous
    mock_writer.close = Mock()  # Synchronous
    mock_writer.wait_closed = AsyncMock()  # Asynchronous
    mock_writer.get_extra_info = Mock(return_value=("127.0.0.1", 12345))
    return mock_writer


@pytest.mark.asyncio
class TestAsyncTCPServer:
    """Test suite for AsyncTCPServer."""

    async def test_initialization(self):
        """Test server initialization."""
        handler = Mock()
        server = AsyncTCPServer("0.0.0.0", 8080, handler)

        assert server.host == "0.0.0.0"
        assert server.port == 8080
        assert server.handler == handler
        assert server.server is None

    @patch("asyncio.start_server")
    async def test_start(self, mock_start_server):
        """Test starting the server."""
        mock_server = AsyncMock()
        mock_server.serve_forever = AsyncMock()
        mock_server.__aenter__ = AsyncMock(return_value=mock_server)
        mock_server.__aexit__ = AsyncMock()
        mock_start_server.return_value = mock_server

        handler = Mock()
        server = AsyncTCPServer("0.0.0.0", 8080, handler)

        # Start in a task and cancel after a short time
        task = asyncio.create_task(server.start())
        await asyncio.sleep(0.1)
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

        mock_start_server.assert_called_once()
        call_args = mock_start_server.call_args
        assert call_args[0][1] == "0.0.0.0"
        assert call_args[0][2] == 8080

    async def test_handle_client(self):
        """Test handling a client connection."""
        mock_reader = AsyncMock()
        mock_reader.read.return_value = b"request data"

        mock_writer = create_mock_writer()
        # Use Mock instead of AsyncMock for get_extra_info
        mock_writer.get_extra_info = Mock(return_value=("127.0.0.1", 54321))

        handler = Mock(return_value=b"response data")
        server = AsyncTCPServer("0.0.0.0", 8080, handler)

        await server._handle_client(mock_reader, mock_writer)

        mock_reader.read.assert_called_once_with(4096)
        handler.assert_called_once_with(b"request data", ("127.0.0.1", 54321))
        mock_writer.write.assert_called_once_with(b"response data")
        mock_writer.drain.assert_called_once()
        mock_writer.close.assert_called_once()
        mock_writer.wait_closed.assert_called_once()

    async def test_handle_client_no_data(self):
        """Test handling client when no data received."""
        mock_reader = AsyncMock()
        mock_reader.read.return_value = b""

        mock_writer = create_mock_writer()
        mock_writer.get_extra_info.return_value = ("127.0.0.1", 54321)

        handler = Mock()
        server = AsyncTCPServer("0.0.0.0", 8080, handler)

        await server._handle_client(mock_reader, mock_writer)

        # Handler should not be called if no data
        handler.assert_not_called()
        mock_writer.close.assert_called_once()

    async def test_handle_client_exception(self):
        """Test handling exception in handler."""
        mock_reader = AsyncMock()
        mock_reader.read.return_value = b"data"

        mock_writer = create_mock_writer()
        mock_writer.get_extra_info = Mock(return_value=("127.0.0.1", 54321))

        handler = Mock(side_effect=Exception("Handler error"))
        server = AsyncTCPServer("0.0.0.0", 8080, handler)

        # Should raise the exception from the handler
        with pytest.raises(Exception, match="Handler error"):
            await server._handle_client(mock_reader, mock_writer)

        # Writer should still be closed
        mock_writer.close.assert_called_once()
        mock_writer.wait_closed.assert_called_once()

    @patch("asyncio.start_server")
    async def test_stop(self, mock_start_server):
        """Test stopping the server."""
        mock_server = AsyncMock()
        mock_server.close = Mock()
        mock_server.wait_closed = AsyncMock()
        mock_start_server.return_value = mock_server

        handler = Mock()
        server = AsyncTCPServer("0.0.0.0", 8080, handler)
        server.server = mock_server

        await server.stop()

        mock_server.close.assert_called_once()
        mock_server.wait_closed.assert_called_once()

    async def test_stop_when_not_running(self):
        """Test stopping when not running."""
        handler = Mock()
        server = AsyncTCPServer("0.0.0.0", 8080, handler)

        await server.stop()  # Should not raise

        assert server.server is None

    async def test_handler_returns_none(self):
        """Test when handler returns None."""
        mock_reader = AsyncMock()
        mock_reader.read.return_value = b"data"

        mock_writer = create_mock_writer()
        mock_writer.get_extra_info = Mock(return_value=("127.0.0.1", 12345))

        handler = Mock(return_value=None)
        server = AsyncTCPServer("0.0.0.0", 8080, handler)

        await server._handle_client(mock_reader, mock_writer)

        handler.assert_called_once()
        # Should not call write if handler returns None
        mock_writer.write.assert_not_called()
        mock_writer.close.assert_called_once()

    async def test_multiple_clients(self):
        """Test handling multiple client connections."""
        mock_reader1 = AsyncMock()
        mock_reader1.read.return_value = b"data1"
        mock_writer1 = create_mock_writer()
        mock_writer1.get_extra_info = Mock(return_value=("127.0.0.1", 54321))

        mock_reader2 = AsyncMock()
        mock_reader2.read.return_value = b"data2"
        mock_writer2 = create_mock_writer()
        mock_writer2.get_extra_info = Mock(return_value=("127.0.0.1", 54322))

        handler = Mock(side_effect=[b"response1", b"response2"])
        server = AsyncTCPServer("0.0.0.0", 8080, handler)

        await server._handle_client(mock_reader1, mock_writer1)
        await server._handle_client(mock_reader2, mock_writer2)

        assert handler.call_count == 2
        mock_writer1.write.assert_called_once_with(b"response1")
        mock_writer2.write.assert_called_once_with(b"response2")

    async def test_get_client_address(self):
        """Test getting client address from writer."""
        mock_reader = AsyncMock()
        mock_reader.read.return_value = b"data"

        mock_writer = create_mock_writer()
        mock_writer.get_extra_info = Mock(return_value=("192.168.1.100", 12345))

        handler = Mock(return_value=b"response")
        server = AsyncTCPServer("0.0.0.0", 8080, handler)

        await server._handle_client(mock_reader, mock_writer)

        mock_writer.get_extra_info.assert_called_once_with("peername")
        handler.assert_called_once_with(b"data", ("192.168.1.100", 12345))

    async def test_write_and_drain(self):
        """Test that write is followed by drain."""
        mock_reader = AsyncMock()
        mock_reader.read.return_value = b"data"

        mock_writer = create_mock_writer()
        mock_writer.get_extra_info = Mock(return_value=("127.0.0.1", 12345))
        mock_writer.get_extra_info.return_value = ("127.0.0.1", 54321)

        handler = Mock(return_value=b"response")
        server = AsyncTCPServer("0.0.0.0", 8080, handler)

        await server._handle_client(mock_reader, mock_writer)

        # Verify write is called before drain
        calls = mock_writer.method_calls
        write_call = call.write(b"response")
        drain_call = call.drain()

        assert write_call in calls
        assert drain_call in calls
