"""Asynchronous TCP client implementation."""

import asyncio
from typing import Optional


class AsyncTCPClient:
    """Asynchronous TCP client using asyncio."""

    def __init__(self, host: str, port: int):
        """
        Initialize async TCP client.
        
        Args:
            host: Server hostname or IP
            port: Server port
        """
        self.host = host
        self.port = port
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None

    async def connect(self) -> None:
        """Establish connection to server."""
        self.reader, self.writer = await asyncio.open_connection(
            self.host, self.port
        )

    async def send(self, data: bytes) -> None:
        """
        Send data to server.
        
        Args:
            data: Bytes to send
            
        Raises:
            ConnectionError: If not connected
        """
        if not self.writer:
            raise ConnectionError("Not connected")
        self.writer.write(data)
        await self.writer.drain()

    async def receive(self, buffer_size: int = 4096) -> bytes:
        """
        Receive data from server.
        
        Args:
            buffer_size: Size of receive buffer
            
        Returns:
            Received bytes
            
        Raises:
            ConnectionError: If not connected
        """
        if not self.reader:
            raise ConnectionError("Not connected")
        return await self.reader.read(buffer_size)

    async def close(self) -> None:
        """Close connection."""
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
            self.writer = None
            self.reader = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
