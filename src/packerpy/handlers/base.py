"""Base handler interface."""

from abc import ABC, abstractmethod
from typing import Any, Tuple


class BaseHandler(ABC):
    """Base interface for message handlers."""

    @abstractmethod
    def handle(self, data: bytes, address: Tuple[str, int]) -> bytes:
        """
        Handle incoming message.
        
        Args:
            data: Received data
            address: Sender address
            
        Returns:
            Response data
        """
        pass

    def on_connect(self, address: Tuple[str, int]) -> None:
        """
        Called when a client connects (TCP only).
        
        Args:
            address: Client address
        """
        pass

    def on_disconnect(self, address: Tuple[str, int]) -> None:
        """
        Called when a client disconnects (TCP only).
        
        Args:
            address: Client address
        """
        pass
