"""Protocol encoding/decoding implementation."""

import threading
from typing import Any, Callable, Dict, Optional, Type, Tuple, Union

from packerpy.protocols.message import Message


class InvalidMessage:
    """
    Wrapper for invalid messages that failed to parse correctly.

    Preserves the raw buffer while attempting to parse as much of
    the message as possible.
    """

    def __init__(
        self,
        raw_data: bytes,
        error: Exception,
        partial_type: Optional[str] = None,
        partial_data: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize InvalidMessage.

        Args:
            raw_data: The raw bytes that failed to parse
            error: The exception that occurred during parsing
            partial_type: The message type if it was successfully extracted
            partial_data: Any partial data that was successfully parsed
        """
        self.raw_data = raw_data
        self.error = error
        self.partial_type = partial_type
        self.partial_data = partial_data or {}

    def __repr__(self) -> str:
        """String representation of invalid message."""
        type_str = f"type={self.partial_type}" if self.partial_type else "type=unknown"
        return (
            f"InvalidMessage({type_str}, error={self.error.__class__.__name__}, "
            f"raw_bytes={len(self.raw_data)})"
        )


class Protocol:
    """
    Protocol encoder/decoder with message type registry.

    Maintains a registry of Message subclasses and handles automatic
    type discrimination during decoding.

    Usage:
        BakerProtocol = Protocol()

        @protocol(BakerProtocol)
        class InitDough(Message):
            fields = {...}

        # Encoding
        msg = InitDough(...)
        data = BakerProtocol.encode(msg)

        # Decoding - automatically returns correct type
        decoded = BakerProtocol.decode(data)
        # decoded is of type InitDough
    """

    def __init__(self):
        """Initialize protocol with empty message registry."""
        self._message_registry: Dict[str, Type[Message]] = {}
        self._scheduled_messages: Dict[int, Dict[str, Any]] = {}
        self._next_schedule_id: int = 0
        self._schedule_lock = threading.Lock()
        self._auto_replies: Dict[int, Dict[str, Any]] = {}
        self._next_reply_id: int = 0
        self._reply_lock = threading.Lock()
        # Buffer for incomplete messages (keyed by connection/source identifier)
        self._incomplete_buffers: Dict[str, bytes] = {}
        self._buffer_lock = threading.Lock()

    def register(self, message_class: Type[Message]) -> Type[Message]:
        """
        Register a Message subclass with this protocol.

        Args:
            message_class: Message subclass to register

        Returns:
            The same message class (for use as decorator)

        Raises:
            ValueError: If message type already registered
        """
        message_type = message_class.__name__

        if message_type in self._message_registry:
            raise ValueError(
                f"Message type '{message_type}' already registered in this protocol"
            )

        self._message_registry[message_type] = message_class
        return message_class

    def encode(self, message: Message) -> bytes:
        """
        Encode a message to bytes for transmission.

        Prepends message type information for automatic decoding.

        Args:
            message: Message instance to encode

        Returns:
            Encoded bytes with type header

        Raises:
            ValueError: If message type not registered or invalid
        """
        message_type = message.__class__.__name__

        if message_type not in self._message_registry:
            raise ValueError(
                f"Message type '{message_type}' not registered with this protocol. "
                f"Use @protocol(your_protocol) decorator on the Message class."
            )

        if not self.validate_message(message):
            raise ValueError("Cannot encode invalid message")

        # Encode message type as length-prefixed UTF-8 string
        type_bytes = message_type.encode("utf-8")
        type_length = len(type_bytes)
        type_header = type_length.to_bytes(2, "big") + type_bytes

        # Serialize message body
        message_bytes = message.serialize_bytes()

        return type_header + message_bytes

    def decode(
        self, data: bytes, source_id: str = "default"
    ) -> Optional[Tuple[Union[Message, "InvalidMessage"], bytes]]:
        """
        Decode bytes into the appropriate Message subclass.

        Uses the type header to instantiate the correct registered class.
        Handles incomplete messages by buffering them for later completion.
        Invalid messages are wrapped in InvalidMessage objects.

        Args:
            data: Bytes to decode
            source_id: Identifier for the message source (e.g., client address)
                      Used to track incomplete buffers per connection

        Returns:
            Tuple of (Message instance, remaining_data) or (InvalidMessage, remaining_data).
            Returns None if message is incomplete and buffered.
            remaining_data is any unused bytes after the message.
        """
        # Prepend any buffered incomplete data for this source
        with self._buffer_lock:
            if source_id in self._incomplete_buffers:
                data = self._incomplete_buffers[source_id] + data
                del self._incomplete_buffers[source_id]

        # Store original data for InvalidMessage if needed
        original_data = data
        partial_type = None
        partial_data = {}

        try:
            # Read message type header
            if len(data) < 2:
                # Incomplete - need more data for type header
                with self._buffer_lock:
                    self._incomplete_buffers[source_id] = data
                return None

            type_length = int.from_bytes(data[0:2], "big")

            if len(data) < 2 + type_length:
                # Incomplete - need more data for message type
                with self._buffer_lock:
                    self._incomplete_buffers[source_id] = data
                return None

            message_type = data[2 : 2 + type_length].decode("utf-8")
            partial_type = message_type

            # Look up message class in registry
            if message_type not in self._message_registry:
                raise ValueError(
                    f"Unknown message type '{message_type}'. "
                    f"Registered types: {list(self._message_registry.keys())}"
                )

            message_class = self._message_registry[message_type]

            # Deserialize message body
            message_data = data[2 + type_length :]

            try:
                message, bytes_consumed = message_class.deserialize_bytes(message_data)
            except Exception as deserialize_error:
                # Check if this might be an incomplete message
                # If we have very little data, it's likely incomplete
                if len(message_data) < 10:  # Arbitrary threshold
                    with self._buffer_lock:
                        self._incomplete_buffers[source_id] = data
                    return None
                # Otherwise treat as invalid
                raise deserialize_error

            # Calculate remaining data
            total_consumed = 2 + type_length + bytes_consumed
            remaining = data[total_consumed:]

            return (message, remaining)

        except Exception as e:
            # Failed to decode - wrap in InvalidMessage
            invalid_msg = InvalidMessage(
                raw_data=original_data,
                error=e,
                partial_type=partial_type,
                partial_data=partial_data,
            )
            # Return the invalid message with all remaining data
            # Caller can decide what to do with it
            return (invalid_msg, b"")

    # Legacy method names for backward compatibility
    def encode_message(self, message: Message) -> bytes:
        """Legacy alias for encode(). Use encode() instead."""
        return self.encode(message)

    def decode_message(self, data: bytes) -> Optional[Union[Message, "InvalidMessage"]]:
        """
        Legacy alias for decode(). Use decode() instead.

        Note: This version returns only the message (not remaining data)
        and uses a default source_id. For better control, use decode() directly.
        """
        result = self.decode(data, source_id="default")
        if result is None:
            return None
        message, _ = result
        return message

    def clear_incomplete_buffer(self, source_id: str = "default") -> bool:
        """
        Clear any incomplete message buffer for a specific source.

        Args:
            source_id: Identifier for the message source

        Returns:
            True if a buffer was cleared, False if none existed
        """
        with self._buffer_lock:
            if source_id in self._incomplete_buffers:
                del self._incomplete_buffers[source_id]
                return True
            return False

    def clear_all_incomplete_buffers(self) -> int:
        """
        Clear all incomplete message buffers.

        Returns:
            Number of buffers cleared
        """
        with self._buffer_lock:
            count = len(self._incomplete_buffers)
            self._incomplete_buffers.clear()
            return count

    def get_incomplete_buffer_size(self, source_id: str = "default") -> int:
        """
        Get the size of incomplete buffer for a specific source.

        Args:
            source_id: Identifier for the message source

        Returns:
            Number of bytes buffered, or 0 if no buffer exists
        """
        with self._buffer_lock:
            if source_id in self._incomplete_buffers:
                return len(self._incomplete_buffers[source_id])
            return 0

    @staticmethod
    def validate_message(message: Message) -> bool:
        """
        Validate a message has required fields.

        Args:
            message: Message to validate

        Returns:
            True if valid, False otherwise
        """
        return message.validate()

    def schedule_message(
        self,
        msg: Message,
        interval: float,
        send_callback: Callable[[bytes], None],
        update_callback: Optional[Callable[[Message], None]] = None,
    ) -> int:
        """
        Schedule a message to be sent automatically at regular intervals.

        Args:
            msg: Message instance to send periodically
            interval: Time interval in seconds between sends
            send_callback: Function that takes encoded bytes and sends them
                          (e.g., socket.sendall, transport.send, etc.)
            update_callback: Optional function that updates the message before
                           each send. Called with the message instance and should
                           modify it in place (e.g., update timestamp, increment counter)

        Returns:
            Schedule ID that can be used to cancel the scheduled message

        Raises:
            ValueError: If interval is not positive or message is invalid

        Example:
            def send_func(data):
                socket.sendall(data)

            # Simple scheduling
            schedule_id = protocol.schedule_message(my_msg, 1.0, send_func)

            # With update callback to refresh timestamp
            def update_timestamp(msg):
                msg.timestamp = int(time.time())

            schedule_id = protocol.schedule_message(
                my_msg, 1.0, send_func, update_timestamp
            )

            # Later, to cancel:
            protocol.cancel_scheduled_message(schedule_id)
        """
        if interval <= 0:
            raise ValueError("Interval must be positive")

        if not self.validate_message(msg):
            raise ValueError("Cannot schedule invalid message")

        with self._schedule_lock:
            schedule_id = self._next_schedule_id
            self._next_schedule_id += 1

            # Create stop event for this scheduled message
            stop_event = threading.Event()

            # Define the worker function that runs in a thread
            def worker():
                while not stop_event.is_set():
                    try:
                        # Update message if callback provided
                        if update_callback is not None:
                            update_callback(msg)

                        # Encode and send
                        encoded_data = self.encode(msg)
                        send_callback(encoded_data)
                    except Exception as e:
                        print(f"Error sending scheduled message: {e}")

                    # Wait for interval or until stop is signaled
                    stop_event.wait(interval)

            # Start the worker thread
            thread = threading.Thread(target=worker, daemon=True)
            thread.start()

            # Store schedule info
            self._scheduled_messages[schedule_id] = {
                "thread": thread,
                "stop_event": stop_event,
                "message": msg,
                "interval": interval,
                "callback": send_callback,
                "update_callback": update_callback,
            }

            return schedule_id

    def cancel_scheduled_message(self, schedule_id: int) -> bool:
        """
        Cancel a scheduled message.

        Args:
            schedule_id: The ID returned by schedule_message()

        Returns:
            True if message was cancelled, False if schedule_id not found
        """
        with self._schedule_lock:
            if schedule_id not in self._scheduled_messages:
                return False

            schedule_info = self._scheduled_messages[schedule_id]
            schedule_info["stop_event"].set()

            # Wait for thread to finish (with timeout)
            schedule_info["thread"].join(timeout=1.0)

            del self._scheduled_messages[schedule_id]
            return True

    def cancel_all_scheduled_messages(self):
        """Cancel all scheduled messages."""
        with self._schedule_lock:
            schedule_ids = list(self._scheduled_messages.keys())

        for schedule_id in schedule_ids:
            self.cancel_scheduled_message(schedule_id)

    def get_scheduled_messages(self) -> Dict[int, Dict[str, Any]]:
        """
        Get information about currently scheduled messages.

        Returns:
            Dictionary mapping schedule IDs to info dicts containing:
            - message: The Message instance
            - interval: The send interval in seconds
        """
        with self._schedule_lock:
            return {
                sid: {"message": info["message"], "interval": info["interval"]}
                for sid, info in self._scheduled_messages.items()
            }

    def register_auto_reply(
        self,
        condition_callback: Callable[[Message], bool],
        reply_msg: Message,
        send_callback: Callable[[bytes], None],
        update_callback: Optional[Callable[[Message, Message], None]] = None,
    ) -> int:
        """
        Register an automatic reply that sends when a condition is met.

        When check_auto_replies() is called with an incoming message, all registered
        auto-replies are checked. If the condition_callback returns True, the reply
        message is sent.

        Args:
            condition_callback: Function that takes an incoming message and returns
                              True if the reply should be sent
            reply_msg: Message instance to send as reply
            send_callback: Function that takes encoded bytes and sends them
            update_callback: Optional function that updates the reply message before
                           sending. Called with (incoming_msg, reply_msg) and should
                           modify reply_msg in place based on incoming_msg

        Returns:
            Reply ID that can be used to unregister the auto-reply

        Raises:
            ValueError: If reply message is invalid

        Example:
            def should_reply(incoming_msg):
                return isinstance(incoming_msg, PingMessage)

            def send_func(data):
                socket.sendall(data)

            # Simple auto-reply
            pong_msg = PongMessage(timestamp=0)
            reply_id = protocol.register_auto_reply(should_reply, pong_msg, send_func)

            # With update callback to copy timestamp from ping
            def update_pong(ping, pong):
                pong.timestamp = ping.timestamp

            reply_id = protocol.register_auto_reply(
                should_reply, pong_msg, send_func, update_pong
            )

            # Later, process incoming messages
            incoming = protocol.decode(data)
            protocol.check_auto_replies(incoming)
        """
        if not self.validate_message(reply_msg):
            raise ValueError("Cannot register invalid reply message")

        with self._reply_lock:
            reply_id = self._next_reply_id
            self._next_reply_id += 1

            self._auto_replies[reply_id] = {
                "condition": condition_callback,
                "reply_msg": reply_msg,
                "send_callback": send_callback,
                "update_callback": update_callback,
            }

            return reply_id

    def unregister_auto_reply(self, reply_id: int) -> bool:
        """
        Unregister an automatic reply.

        Args:
            reply_id: The ID returned by register_auto_reply()

        Returns:
            True if reply was unregistered, False if reply_id not found
        """
        with self._reply_lock:
            if reply_id in self._auto_replies:
                del self._auto_replies[reply_id]
                return True
            return False

    def unregister_all_auto_replies(self):
        """Unregister all automatic replies."""
        with self._reply_lock:
            self._auto_replies.clear()

    def check_auto_replies(self, incoming_msg: Message) -> int:
        """
        Check all registered auto-replies against an incoming message.

        For each registered auto-reply, if the condition callback returns True,
        the reply message is sent.

        Args:
            incoming_msg: The incoming message to check against

        Returns:
            Number of replies that were sent

        Example:
            # After receiving data
            incoming = protocol.decode(received_data)
            if incoming:
                num_replies = protocol.check_auto_replies(incoming)
                print(f"Sent {num_replies} auto-replies")
        """
        replies_sent = 0

        # Get snapshot of auto-replies to avoid holding lock during callbacks
        with self._reply_lock:
            auto_replies = list(self._auto_replies.items())

        for reply_id, reply_info in auto_replies:
            try:
                # Check condition
                if reply_info["condition"](incoming_msg):
                    # Update reply if callback provided
                    if reply_info["update_callback"] is not None:
                        reply_info["update_callback"](
                            incoming_msg, reply_info["reply_msg"]
                        )

                    # Encode and send
                    encoded_data = self.encode(reply_info["reply_msg"])
                    reply_info["send_callback"](encoded_data)
                    replies_sent += 1
            except Exception as e:
                print(f"Error processing auto-reply {reply_id}: {e}")

        return replies_sent

    def get_auto_replies(self) -> Dict[int, Dict[str, Any]]:
        """
        Get information about currently registered auto-replies.

        Returns:
            Dictionary mapping reply IDs to info dicts containing:
            - reply_msg: The Message instance that will be sent
        """
        with self._reply_lock:
            return {
                rid: {"reply_msg": info["reply_msg"]}
                for rid, info in self._auto_replies.items()
            }


def protocol(protocol_instance: Protocol):
    """
    Decorator to register a Message subclass with a Protocol.

    Usage:
        my_protocol = Protocol()

        @protocol(my_protocol)
        class MyMessage(Message):
            fields = {...}

    Args:
        protocol_instance: Protocol instance to register with

    Returns:
        Decorator function
    """

    def decorator(message_class: Type[Message]) -> Type[Message]:
        return protocol_instance.register(message_class)

    return decorator
