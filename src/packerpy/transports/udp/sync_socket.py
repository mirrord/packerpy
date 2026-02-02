"""Synchronous UDP socket implementation."""

import socket
from typing import Optional, Tuple


class SyncUDPSocket:
    """Synchronous UDP socket."""

    def __init__(self, host: str = "0.0.0.0", port: int = 0):
        """
        Initialize UDP socket.
        
        Args:
            host: Bind hostname or IP
            port: Bind port (0 for automatic assignment)
        """
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None

    def bind(self) -> None:
        """Bind socket to address."""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((self.host, self.port))
        # Update port if it was auto-assigned
        if self.port == 0:
            self.port = self.socket.getsockname()[1]

    def send_to(self, data: bytes, address: Tuple[str, int]) -> None:
        """
        Send data to specific address.
        
        Args:
            data: Bytes to send
            address: Target address tuple (host, port)
            
        Raises:
            ConnectionError: If socket not bound
        """
        if not self.socket:
            raise ConnectionError("Socket not bound")
        self.socket.sendto(data, address)

    def receive_from(self, buffer_size: int = 4096) -> Tuple[bytes, Tuple[str, int]]:
        """
        Receive data from any sender.
        
        Args:
            buffer_size: Size of receive buffer
            
        Returns:
            Tuple of (data, sender_address)
            
        Raises:
            ConnectionError: If socket not bound
        """
        if not self.socket:
            raise ConnectionError("Socket not bound")
        return self.socket.recvfrom(buffer_size)

    def close(self) -> None:
        """Close socket."""
        if self.socket:
            self.socket.close()
            self.socket = None

    def __enter__(self):
        """Context manager entry."""
        self.bind()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
