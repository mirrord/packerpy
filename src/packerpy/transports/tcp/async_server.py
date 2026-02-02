"""Asynchronous TCP server implementation."""

import asyncio
from typing import Callable, Optional


class AsyncTCPServer:
    """Asynchronous TCP server using asyncio."""

    def __init__(
        self, host: str, port: int, handler: Callable[[bytes, tuple], Optional[bytes]]
    ):
        """
        Initialize async TCP server.

        Args:
            host: Bind hostname or IP
            port: Bind port
            handler: Async callback function to handle client requests.
                    Returns bytes to send back, or None if no response needed.
        """
        self.host = host
        self.port = port
        self.handler = handler
        self.server: Optional[asyncio.Server] = None

    async def start(self) -> None:
        """Start the server."""
        self.server = await asyncio.start_server(
            self._handle_client, self.host, self.port
        )
        print(f"Server listening on {self.host}:{self.port}")

        async with self.server:
            await self.server.serve_forever()

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """
        Handle a client connection.

        Args:
            reader: Stream reader for receiving data
            writer: Stream writer for sending data
        """
        try:
            address = writer.get_extra_info("peername")
            data = await reader.read(4096)
            if data:
                response = self.handler(data, address)
                if response is not None:
                    writer.write(response)
                    await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    async def stop(self) -> None:
        """Stop the server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
