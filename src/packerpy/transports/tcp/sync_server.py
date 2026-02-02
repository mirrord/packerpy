"""Synchronous TCP server implementation."""

import socket
from typing import Callable, Optional, Tuple


class SyncTCPServer:
    """Synchronous TCP server."""

    def __init__(
        self, host: str, port: int, handler: Callable[[bytes, Tuple[str, int]], bytes]
    ):
        """
        Initialize TCP server.

        Args:
            host: Bind hostname or IP
            port: Bind port
            handler: Callback function to handle client requests
        """
        self.host = host
        self.port = port
        self.handler = handler
        self.socket: Optional[socket.socket] = None
        self.running = False

    def start(self) -> None:
        """Start the server."""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.host, self.port))
        self.socket.listen(5)
        self.running = True
        print(f"Server listening on {self.host}:{self.port}")

        while self.running:
            try:
                client_socket, client_address = self.socket.accept()
                self._handle_client(client_socket, client_address)
            except Exception as e:
                if self.running:
                    print(f"Error handling client: {e}")

    def _handle_client(
        self, client_socket: socket.socket, client_address: Tuple[str, int]
    ) -> None:
        """
        Handle a client connection.

        Args:
            client_socket: Client socket
            client_address: Client address tuple
        """
        try:
            data = client_socket.recv(4096)
            if data:
                response = self.handler(data, client_address)
                if response is not None:
                    client_socket.sendall(response)
        finally:
            client_socket.close()

    def stop(self) -> None:
        """Stop the server."""
        self.running = False
        if self.socket:
            self.socket.close()
            self.socket = None
