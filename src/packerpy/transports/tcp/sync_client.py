"""Synchronous TCP client implementation."""

import socket
from typing import Optional


class SyncTCPClient:
    """Synchronous TCP client."""

    def __init__(self, host: str, port: int, timeout: float = 30.0):
        """
        Initialize TCP client.
        
        Args:
            host: Server hostname or IP
            port: Server port
            timeout: Socket timeout in seconds
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.socket: Optional[socket.socket] = None

    def connect(self) -> None:
        """Establish connection to server."""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(self.timeout)
        self.socket.connect((self.host, self.port))

    def send(self, data: bytes) -> None:
        """
        Send data to server.
        
        Args:
            data: Bytes to send
            
        Raises:
            ConnectionError: If not connected
        """
        if not self.socket:
            raise ConnectionError("Not connected")
        self.socket.sendall(data)

    def receive(self, buffer_size: int = 4096) -> bytes:
        """
        Receive data from server.
        
        Args:
            buffer_size: Size of receive buffer
            
        Returns:
            Received bytes
            
        Raises:
            ConnectionError: If not connected
        """
        if not self.socket:
            raise ConnectionError("Not connected")
        return self.socket.recv(buffer_size)

    def close(self) -> None:
        """Close connection."""
        if self.socket:
            self.socket.close()
            self.socket = None

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
