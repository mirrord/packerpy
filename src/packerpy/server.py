"""Server implementation with protocol support."""

import asyncio
import threading
from enum import Enum
from queue import Queue, Empty
from typing import Callable, Optional, Tuple, Union

from packerpy.protocols.protocol import Protocol, InvalidMessage
from packerpy.protocols.message import Message
from packerpy.transports.tcp.async_server import AsyncTCPServer


class ConnectionStatus(Enum):
    """Server connection status."""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


class Server:
    """
    High-level server that uses the Protocol for message handling.

    This server abstracts away transport details and provides a clean
    interface for working with Message objects. Async servers run in a separate thread.
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8080,
        message_handler: Optional[
            Callable[[Message, Tuple[str, int]], Optional[Message]]
        ] = None,
        protocol: Optional[Protocol] = None,
    ):
        """
        Initialize the server.

        Args:
            host: Host address to bind to
            port: Port number to listen on
            message_handler: Optional callback function that takes a Message and address.
                           If it returns a Message, that will be sent as a response.
            protocol: Optional Protocol instance with registered message types.
                     If None, creates a new empty Protocol instance.
        """
        self.host = host
        self.port = port
        self.protocol = protocol if protocol is not None else Protocol()
        self.message_handler = message_handler
        self._received_messages: Queue = Queue()
        self._status = ConnectionStatus.STOPPED
        self._server_thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._transport: Optional[AsyncTCPServer] = None
        self._error: Optional[Exception] = None

    def _handle_raw_data(
        self, data: bytes, address: Tuple[str, int]
    ) -> Optional[bytes]:
        """
        Internal handler that converts bytes to/from Messages.

        Args:
            data: Raw bytes from transport
            address: Sender address

        Returns:
            Response bytes if message_handler provides one, else None
        """
        # Use address as source_id for incomplete buffer tracking
        source_id = f"{address[0]}:{address[1]}"

        # Decode bytes to Message
        result = self.protocol.decode(data, source_id=source_id)
        if result is None:
            # Incomplete message - buffered for later
            return None

        message, remaining = result

        # Handle InvalidMessage
        if isinstance(message, InvalidMessage):
            # Store invalid message in queue for user to inspect
            self._received_messages.put((message, address))
            print(f"Invalid message from {address}: {message.error.__class__.__name__}")
            # Clear buffer on invalid message to avoid corruption
            self.protocol.clear_incomplete_buffer(source_id)
            return None

        # Validate message
        if not self.protocol.validate_message(message):
            # Invalid message - wrap it
            invalid_msg = InvalidMessage(
                raw_data=data,
                error=ValueError("Message validation failed"),
                partial_type=message.__class__.__name__,
            )
            self._received_messages.put((invalid_msg, address))
            return None

        # Clear incomplete buffer on successful decode
        self.protocol.clear_incomplete_buffer(source_id)

        # Store received message in queue for user to consume
        self._received_messages.put((message, address))

        # Check auto-replies for this message (only for valid messages)
        try:
            self.protocol.check_auto_replies(message)
        except Exception as reply_error:
            print(f"Auto-reply error: {reply_error}")

        # Call handler if provided and return response if any
        if self.message_handler:
            response_message = self.message_handler(message, address)
            if response_message:
                return self.protocol.encode_message(response_message)

        return None

    def _run_async_server(self) -> None:
        """Run the async server in a separate thread."""
        try:
            self._status = ConnectionStatus.STARTING
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

            self._transport = AsyncTCPServer(
                host=self.host, port=self.port, handler=self._handle_raw_data
            )

            self._status = ConnectionStatus.RUNNING
            self._loop.run_until_complete(self._transport.start())
        except asyncio.CancelledError:
            # Normal shutdown - don't print error
            pass
        except Exception as e:
            self._status = ConnectionStatus.ERROR
            self._error = e
            print(f"Server error: {e}")
        finally:
            if self._loop and not self._loop.is_closed():
                # Cancel all pending tasks before closing the loop
                try:
                    pending = asyncio.all_tasks(self._loop)
                    for task in pending:
                        task.cancel()
                    # Give tasks a chance to handle cancellation
                    self._loop.run_until_complete(
                        asyncio.gather(*pending, return_exceptions=True)
                    )
                except Exception:
                    pass
                self._loop.close()
            self._status = ConnectionStatus.STOPPED

    def start(self) -> None:
        """Start the server. Runs in a background thread for async mode."""
        self._server_thread = threading.Thread(
            target=self._run_async_server, daemon=True
        )
        self._server_thread.start()
        print(f"Server starting on {self.host}:{self.port}")

    def stop(self) -> None:
        """Stop the server."""
        self._status = ConnectionStatus.STOPPING
        if self._loop and self._transport:
            # Stop the server in its event loop
            future = asyncio.run_coroutine_threadsafe(
                self._transport.stop(), self._loop
            )
            try:
                future.result(timeout=5.0)
            except Exception:
                pass
        if self._server_thread:
            self._server_thread.join(timeout=5.0)

    def get_status(self) -> ConnectionStatus:
        """
        Get the current server status.

        Returns:
            Current ConnectionStatus
        """
        return self._status

    def get_error(self) -> Optional[Exception]:
        """
        Get the last error if status is ERROR.

        Returns:
            Last exception or None
        """
        return self._error

    def receive(
        self, timeout: Optional[float] = None
    ) -> Optional[Tuple[Union[Message, InvalidMessage], Tuple[str, int]]]:
        """
        Receive a message from the queue.

        Args:
            timeout: Maximum time to wait for a message (None = wait forever, 0 = non-blocking)

        Returns:
            Tuple of (Message or InvalidMessage, sender_address) or None if no message available
        """
        try:
            return self._received_messages.get(
                timeout=timeout if timeout is not None else None
            )
        except Empty:
            return None

    def send(self, message: Union[Message, bytes], address: Tuple[str, int]) -> bool:
        """
        Send a message to a specific address.

        Note: For TCP servers, this functionality is limited as connections
        are typically one-way (client to server). This is mainly useful
        for UDP servers or for implementing custom connection tracking.

        Args:
            message: Message object or raw bytes to send
            address: Target address

        Returns:
            True if sent successfully, False otherwise
        """
        # Handle raw bytes
        if isinstance(message, (bytes, bytearray, memoryview)):
            pass  # data is already bytes
        else:
            # Handle Message object
            if not self.protocol.validate_message(message):
                print("Invalid message, cannot send")
                return False

        # This is a simplified implementation
        # In a real TCP server, you'd need to maintain client connections
        print("Warning: Direct send() on server requires connection management")
        return False

    def register_auto_reply(
        self,
        condition_callback: Callable[[Message], bool],
        reply_msg: Message,
        send_callback: Optional[Callable[[bytes], None]] = None,
        update_callback: Optional[Callable[[Message, Message], None]] = None,
    ) -> int:
        """
        Register an automatic reply with this server's protocol.

        Important: For auto-replies to work properly in a server context, you need
        to provide a send_callback that knows how to send data back to the client.
        The message handler's return value is one way, but auto-replies provide
        another mechanism for request-response patterns.

        Args:
            condition_callback: Function that determines if reply should be sent
            reply_msg: Message template to send as reply
            send_callback: Function to send encoded reply data. If None, a warning
                         is printed as server send requires connection tracking.
            update_callback: Optional function to update reply based on incoming message

        Returns:
            Reply ID for managing the auto-reply

        Example:
            # For servers, you typically need to track connections and provide
            # a send_callback that can route to the right client
            def send_to_client(data):
                # Custom logic to send to appropriate client
                pass

            server.register_auto_reply(
                condition_callback=lambda msg: isinstance(msg, PingMessage),
                reply_msg=pong_msg,
                send_callback=send_to_client,
                update_callback=update_pong
            )
        """
        if send_callback is None:
            # Provide a default that prints a warning
            def warning_callback(data):
                print(
                    "Warning: Auto-reply triggered but no send_callback provided. "
                    "Server auto-replies require custom send logic for connection routing."
                )

            send_callback = warning_callback

        return self.protocol.register_auto_reply(
            condition_callback, reply_msg, send_callback, update_callback
        )
