"""Unit tests for handlers.base module."""

import pytest
from abc import ABC

from packerpy.handlers.base import BaseHandler


class ConcreteHandler(BaseHandler):
    """Concrete implementation of BaseHandler for testing."""

    def __init__(self):
        self.handled_data = []
        self.connected_addresses = []
        self.disconnected_addresses = []

    def handle(self, data: bytes, address: tuple) -> bytes:
        """Handle incoming message."""
        self.handled_data.append((data, address))
        return b"response_" + data

    def on_connect(self, address: tuple) -> None:
        """Called when a client connects."""
        self.connected_addresses.append(address)

    def on_disconnect(self, address: tuple) -> None:
        """Called when a client disconnects."""
        self.disconnected_addresses.append(address)


class TestBaseHandler:
    """Test suite for BaseHandler abstract class."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that BaseHandler cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseHandler()

    def test_concrete_implementation_can_be_instantiated(self):
        """Test that concrete implementation can be instantiated."""
        handler = ConcreteHandler()
        assert handler is not None
        assert isinstance(handler, BaseHandler)

    def test_handle_method(self):
        """Test handle method receives data and address."""
        handler = ConcreteHandler()
        data = b"test data"
        address = ("127.0.0.1", 8080)

        response = handler.handle(data, address)

        assert response == b"response_test data"
        assert (data, address) in handler.handled_data

    def test_handle_multiple_messages(self):
        """Test handling multiple messages."""
        handler = ConcreteHandler()

        messages = [
            (b"message1", ("127.0.0.1", 8080)),
            (b"message2", ("127.0.0.1", 8081)),
            (b"message3", ("192.168.1.1", 9000)),
        ]

        for data, address in messages:
            handler.handle(data, address)

        assert len(handler.handled_data) == 3
        assert handler.handled_data == messages

    def test_on_connect_callback(self):
        """Test on_connect callback is called."""
        handler = ConcreteHandler()
        address = ("127.0.0.1", 8080)

        handler.on_connect(address)

        assert address in handler.connected_addresses

    def test_on_disconnect_callback(self):
        """Test on_disconnect callback is called."""
        handler = ConcreteHandler()
        address = ("127.0.0.1", 8080)

        handler.on_disconnect(address)

        assert address in handler.disconnected_addresses

    def test_connection_lifecycle(self):
        """Test connection lifecycle callbacks."""
        handler = ConcreteHandler()
        address = ("192.168.1.100", 5555)

        # Connect
        handler.on_connect(address)
        assert address in handler.connected_addresses

        # Handle some data
        handler.handle(b"data", address)
        assert len(handler.handled_data) == 1

        # Disconnect
        handler.on_disconnect(address)
        assert address in handler.disconnected_addresses

    def test_multiple_connections(self):
        """Test handling multiple client connections."""
        handler = ConcreteHandler()

        addresses = [("127.0.0.1", 8080), ("127.0.0.1", 8081), ("192.168.1.1", 9000)]

        for addr in addresses:
            handler.on_connect(addr)

        assert len(handler.connected_addresses) == 3
        for addr in addresses:
            assert addr in handler.connected_addresses

    def test_handle_empty_data(self):
        """Test handling empty data."""
        handler = ConcreteHandler()
        data = b""
        address = ("127.0.0.1", 8080)

        response = handler.handle(data, address)

        assert response == b"response_"
        assert (data, address) in handler.handled_data

    def test_handle_large_data(self):
        """Test handling large data."""
        handler = ConcreteHandler()
        data = b"x" * 10000
        address = ("127.0.0.1", 8080)

        response = handler.handle(data, address)

        assert response.startswith(b"response_")
        assert len(response) == len(b"response_") + 10000

    def test_address_format(self):
        """Test that addresses are tuples of (host, port)."""
        handler = ConcreteHandler()

        # IPv4 address
        ipv4_address = ("192.168.1.1", 8080)
        handler.on_connect(ipv4_address)
        assert ipv4_address in handler.connected_addresses

        # Localhost
        localhost_address = ("localhost", 9000)
        handler.on_connect(localhost_address)
        assert localhost_address in handler.connected_addresses

    def test_handler_is_abstract_base_class(self):
        """Test that BaseHandler is an ABC."""
        assert issubclass(BaseHandler, ABC)

    def test_missing_handle_implementation(self):
        """Test that missing handle() implementation prevents instantiation."""
        with pytest.raises(TypeError) as exc_info:

            class IncompleteHandler(BaseHandler):
                pass

            IncompleteHandler()

        assert "Can't instantiate abstract class" in str(exc_info.value)
