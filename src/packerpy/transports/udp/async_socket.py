"""Asynchronous UDP socket implementation."""

import asyncio
from typing import Optional, Tuple


class AsyncUDPProtocol(asyncio.DatagramProtocol):
    """Protocol handler for async UDP."""

    def __init__(self):
        """Initialize protocol."""
        self.transport: Optional[asyncio.DatagramTransport] = None
        self.received_data: asyncio.Queue = asyncio.Queue()

    def connection_made(self, transport):
        """Called when connection is established."""
        self.transport = transport

    def datagram_received(self, data: bytes, addr: Tuple[str, int]):
        """Called when a datagram is received."""
        self.received_data.put_nowait((data, addr))

    def error_received(self, exc: Exception):
        """Called when an error occurs."""
        print(f"UDP error: {exc}")


class AsyncUDPSocket:
    """Asynchronous UDP socket using asyncio."""

    def __init__(self, host: str = "0.0.0.0", port: int = 0):
        """
        Initialize async UDP socket.
        
        Args:
            host: Bind hostname or IP
            port: Bind port (0 for automatic assignment)
        """
        self.host = host
        self.port = port
        self.transport: Optional[asyncio.DatagramTransport] = None
        self.protocol: Optional[AsyncUDPProtocol] = None

    async def bind(self) -> None:
        """Bind socket to address."""
        loop = asyncio.get_event_loop()
        self.transport, self.protocol = await loop.create_datagram_endpoint(
            lambda: AsyncUDPProtocol(),
            local_addr=(self.host, self.port)
        )

    async def send_to(self, data: bytes, address: Tuple[str, int]) -> None:
        """
        Send data to specific address.
        
        Args:
            data: Bytes to send
            address: Target address tuple (host, port)
            
        Raises:
            ConnectionError: If not bound
        """
        if not self.transport:
            raise ConnectionError("Socket not bound")
        self.transport.sendto(data, address)

    async def receive_from(self) -> Tuple[bytes, Tuple[str, int]]:
        """
        Receive data from any sender.
        
        Returns:
            Tuple of (data, sender_address)
            
        Raises:
            ConnectionError: If not bound
        """
        if not self.protocol:
            raise ConnectionError("Socket not bound")
        return await self.protocol.received_data.get()

    async def close(self) -> None:
        """Close socket."""
        if self.transport:
            self.transport.close()
            self.transport = None
            self.protocol = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.bind()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
