"""Client implementation with protocol support."""

import asyncio
import threading
from enum import Enum
from queue import Queue, Empty
from typing import Optional, Union

from packerpy.protocols.protocol import Protocol, InvalidMessage
from packerpy.protocols.message import Message
from packerpy.transports.tcp.async_client import AsyncTCPClient


class ConnectionStatus(Enum):
    """Client connection status."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    ERROR = "error"


class Client:
    """
    High-level client that uses the Protocol for message handling.

    This client abstracts away transport details and provides a clean
    interface for working with Message objects. Async clients run in a separate thread.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8080,
        protocol: Optional[Protocol] = None,
    ):
        """
        Initialize the client.

        Args:
            host: Server host address
            port: Server port number
            protocol: Optional Protocol instance with registered message types.
                     If None, creates a new empty Protocol instance.
        """
        self.host = host
        self.port = port
        self.protocol = protocol if protocol is not None else Protocol()
        self._transport = AsyncTCPClient(host=host, port=port)
        self._received_messages: Queue = Queue()
        self._status = ConnectionStatus.DISCONNECTED
        self._client_thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._error: Optional[Exception] = None
        self._running = False

    async def _receive_loop(self) -> None:
        """Continuously receive messages in the background."""
        source_id = "client"

        while self._running:
            try:
                data = await self._transport.receive()
                if data:
                    result = self.protocol.decode(data, source_id=source_id)
                    if result is not None:
                        message, remaining = result

                        # Handle InvalidMessage
                        if isinstance(message, InvalidMessage):
                            # Store invalid message for user to inspect
                            self._received_messages.put(message)
                            print(
                                f"Invalid message: {message.error.__class__.__name__}"
                            )
                            # Clear buffer on invalid message
                            self.protocol.clear_incomplete_buffer(source_id)
                        else:
                            # Clear buffer on successful decode
                            self.protocol.clear_incomplete_buffer(source_id)
                            self._received_messages.put(message)

                            # Check auto-replies for valid messages only
                            try:
                                self.protocol.check_auto_replies(message)
                            except Exception as reply_error:
                                print(f"Auto-reply error: {reply_error}")
                else:
                    # Empty data means connection closed
                    if self._running:
                        print("Connection closed by server")
                    break
            except Exception as e:
                if self._running:
                    self._status = ConnectionStatus.ERROR
                    self._error = e
                    print(f"Receive error: {e}")
                break

    def _run_async_client(self) -> None:
        """Run the async client in a separate thread."""
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self._async_client_main())
        except Exception as e:
            self._status = ConnectionStatus.ERROR
            self._error = e
            print(f"Client error: {e}")
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
            self._status = ConnectionStatus.DISCONNECTED

    async def _async_client_main(self) -> None:
        """Main async client coroutine."""
        await self._transport.connect()
        self._status = ConnectionStatus.CONNECTED

        # Start receive loop as a background task so it doesn't block
        receive_task = asyncio.create_task(self._receive_loop())

        # Keep the event loop alive while client is running
        try:
            while self._running:
                await asyncio.sleep(0.1)
        finally:
            # Cancel receive task if still running
            if not receive_task.done():
                receive_task.cancel()
                try:
                    await receive_task
                except asyncio.CancelledError:
                    pass

    def connect(self) -> None:
        """Establish connection to server. Starts background thread for async mode."""
        self._status = ConnectionStatus.CONNECTING
        self._running = True
        self._client_thread = threading.Thread(
            target=self._run_async_client, daemon=True
        )
        self._client_thread.start()
        # Wait a moment for connection to establish
        import time

        time.sleep(0.1)

    def send(self, message: Union[Message, bytes]) -> bool:
        """
        Send a message to the server.

        Args:
            message: Message object or raw bytes to send

        Returns:
            True if sent successfully, False otherwise
        """
        # Handle raw bytes
        if isinstance(message, (bytes, bytearray, memoryview)):
            data = bytes(message)
        else:
            # Handle Message object
            if not self.protocol.validate_message(message):
                print("Invalid message, cannot send")
                return False

            try:
                data = self.protocol.encode_message(message)
            except Exception as e:
                print(f"Encode error: {e}")
                self._status = ConnectionStatus.ERROR
                self._error = e
                return False

        try:
            if self._loop and self._status == ConnectionStatus.CONNECTED:
                # Check if loop is still running
                if self._loop.is_closed():
                    print("Event loop is closed")
                    return False

                future = asyncio.run_coroutine_threadsafe(
                    self._transport.send(data), self._loop
                )
                # Wait for the send operation to complete
                try:
                    future.result(timeout=2.0)
                except (TimeoutError, asyncio.CancelledError):
                    # Operation timed out or was cancelled
                    # Don't try to cancel - just let it complete or fail on its own
                    print("Send operation timed out or cancelled")
                    self._status = ConnectionStatus.ERROR
                    return False
                except Exception as send_err:
                    print(f"Send operation error: {send_err}")
                    return False
                return True
            return False
        except Exception as e:
            print(f"Send error: {e}")
            self._status = ConnectionStatus.ERROR
            self._error = e
            return False

    def receive(
        self, timeout: Optional[float] = None
    ) -> Optional[Union[Message, InvalidMessage]]:
        """
        Receive a message from the queue.

        Args:
            timeout: Maximum time to wait for a message (None = wait forever, 0 = non-blocking)

        Returns:
            Message, InvalidMessage, or None if no message available
        """
        try:
            return self._received_messages.get(
                timeout=timeout if timeout is not None else None
            )
        except Empty:
            return None

    def close(self) -> None:
        """Close connection to server."""
        self._running = False
        self._status = ConnectionStatus.DISCONNECTING
        if self._loop and self._transport and not self._loop.is_closed():
            # Create a task to close the transport
            future = asyncio.run_coroutine_threadsafe(
                self._transport.close(), self._loop
            )
            try:
                future.result(timeout=2.0)
            except (TimeoutError, asyncio.CancelledError, RuntimeError):
                # Timeout or loop already closed - just continue with thread join
                pass
            except Exception:
                pass
        if self._client_thread:
            self._client_thread.join(timeout=5.0)

    def get_status(self) -> ConnectionStatus:
        """
        Get the current client status.

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

    def __aenter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def register_auto_reply(self, *args, **kwargs) -> int:
        """
        Register an automatic reply with this client's protocol.

        This is a convenience wrapper that automatically uses this client's
        send method as the send_callback if not provided.

        Args:
            Same as Protocol.register_auto_reply(), but send_callback is optional.
            If send_callback is not provided, uses this client's send method.

        Returns:
            Reply ID for managing the auto-reply

        Example:
            # Auto-reply that uses client's send method
            client.register_auto_reply(
                condition_callback=lambda msg: isinstance(msg, PingMessage),
                reply_msg=pong_msg,
                update_callback=update_pong
            )
        """
        # If send_callback not provided, use this client's send method
        if "send_callback" not in kwargs:
            kwargs["send_callback"] = lambda data: self.send(data)

        return self.protocol.register_auto_reply(*args, **kwargs)
