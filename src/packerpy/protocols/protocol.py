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
        # Automatic headers and footers
        self._headers: Dict[str, Dict[str, Any]] = {}
        self._footers: Dict[str, Dict[str, Any]] = {}
        self._header_lock = threading.Lock()
        self._footer_lock = threading.Lock()

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

    def set_headers(self, headers: Dict[str, Dict[str, Any]]) -> None:
        """
        Set automatic header fields to be prepended to every encoded message.

        Headers are added BEFORE the message body during encoding and removed
        during decoding. Header fields support all field reference features:
        - length_of: Count fields present in message
        - size_of: Get byte size of fields
        - compute: Custom computation (e.g., CRC calculation)
        - value_from: Copy value from another field

        Args:
            headers: Dict mapping header field names to field specifications.
                    Specifications use the same format as Message.fields.

        Example:
            protocol.set_headers({
                "field_count": {
                    "type": "uint(8)",
                    "compute": lambda msg: len([f for f in msg.fields.keys()
                                                 if hasattr(msg, f)])
                },
                "payload_length": {
                    "type": "uint(32)",
                    "size_of": "body"
                },
                "checksum": {
                    "type": "uint(32)",
                    "compute": lambda msg: Protocol.crc32(msg.serialize_bytes())
                }
            })
        """
        with self._header_lock:
            self._headers = dict(headers)

    def set_footers(self, footers: Dict[str, Dict[str, Any]]) -> None:
        """
        Set automatic footer fields to be appended to every encoded message.

        Footers are added AFTER the message body during encoding and removed
        during decoding. Footer fields support all field reference features:
        - length_of: Count fields present in message
        - size_of: Get byte size of fields
        - compute: Custom computation (e.g., CRC calculation)
        - value_from: Copy value from another field

        Args:
            footers: Dict mapping footer field names to field specifications.
                    Specifications use the same format as Message.fields.

        Example:
            protocol.set_footers({
                "message_crc": {
                    "type": "uint(32)",
                    "compute": lambda msg: Protocol.crc32(msg.serialize_bytes())
                },
                "end_marker": {
                    "type": "uint(16)",
                    "static": 0xFFFF
                }
            })
        """
        with self._footer_lock:
            self._footers = dict(footers)

    def clear_headers(self) -> None:
        """Remove all automatic headers."""
        with self._header_lock:
            self._headers = {}

    def clear_footers(self) -> None:
        """Remove all automatic footers."""
        with self._footer_lock:
            self._footers = {}

    @staticmethod
    def crc32(data: bytes, initial: int = 0) -> int:
        """
        Calculate CRC-32 checksum of data.

        This is a convenience method for use in header/footer compute functions.

        Args:
            data: Bytes to calculate CRC for
            initial: Initial CRC value (default 0)

        Returns:
            CRC-32 checksum as unsigned 32-bit integer
        """
        import zlib

        return zlib.crc32(data, initial) & 0xFFFFFFFF

    @staticmethod
    def count_fields(message: Message) -> int:
        """
        Count the number of non-None fields in a message.

        This is a convenience method for use in header/footer compute functions.

        Args:
            message: Message instance to count fields in

        Returns:
            Number of fields that have been set (not None)
        """
        count = 0
        for field_name in message.fields.keys():
            if hasattr(message, field_name):
                value = getattr(message, field_name)
                if value is not None:
                    count += 1
        return count

    @staticmethod
    def list_length(message: Message, field_name: str) -> int:
        """
        Get the length of a list field in a message.

        This is a convenience method for use in header/footer compute functions.

        Args:
            message: Message instance
            field_name: Name of the list field

        Returns:
            Length of the list, or 0 if field doesn't exist or is not a list
        """
        if not hasattr(message, field_name):
            return 0
        value = getattr(message, field_name)
        if isinstance(value, list):
            return len(value)
        return 0

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

        # Add automatic headers
        header_bytes = b""
        with self._header_lock:
            if self._headers:
                header_bytes = self._serialize_auto_fields(
                    self._headers, message, message_bytes
                )

        # Add automatic footers
        footer_bytes = b""
        with self._footer_lock:
            if self._footers:
                footer_bytes = self._serialize_auto_fields(
                    self._footers, message, message_bytes
                )

        return type_header + header_bytes + message_bytes + footer_bytes

    def _serialize_auto_fields(
        self, fields: Dict[str, Dict[str, Any]], message: Message, message_bytes: bytes
    ) -> bytes:
        """
        Serialize automatic header or footer fields.

        Args:
            fields: Field specifications (headers or footers)
            message: The message being encoded
            message_bytes: The serialized message body bytes

        Returns:
            Serialized field bytes
        """
        result = b""
        byteorder = getattr(message, "encoding", None)
        if byteorder:
            byteorder = byteorder.value
        else:
            byteorder = "big"

        # Create a temporary message-like object with computed values
        class AutoFieldContext:
            """Context object for computing auto field values."""

            def __init__(self, msg: Message, msg_bytes: bytes):
                self.message = msg
                self.message_bytes = msg_bytes
                # Copy message fields to this context
                for field_name in msg.fields.keys():
                    if hasattr(msg, field_name):
                        setattr(self, field_name, getattr(msg, field_name))

            def serialize_bytes(self) -> bytes:
                """Return the message bytes."""
                return self.message_bytes

        context = AutoFieldContext(message, message_bytes)

        for field_name, field_spec in fields.items():
            # Compute field value
            value = self._compute_auto_field_value(
                field_name, field_spec, context, message, message_bytes
            )

            # Serialize the value
            field_bytes = self._serialize_auto_field_value(
                value, field_spec, byteorder, message
            )
            result += field_bytes

        return result

    def _compute_auto_field_value(
        self,
        field_name: str,
        field_spec: Dict[str, Any],
        context: Any,
        message: Message,
        message_bytes: bytes,
    ) -> Any:
        """
        Compute the value for an automatic header/footer field.

        Args:
            field_name: Name of the field
            field_spec: Field specification
            context: Context object with message data
            message: Original message instance
            message_bytes: Serialized message bytes

        Returns:
            Computed field value
        """
        # Get byteorder from message
        byteorder = getattr(message, "encoding", None)
        if byteorder:
            byteorder = byteorder.value
        else:
            byteorder = "big"

        # Static value
        if "static" in field_spec:
            return field_spec["static"]

        # Length of another field
        if "length_of" in field_spec:
            target_field = field_spec["length_of"]
            target_value = self._resolve_auto_field_reference(
                target_field, context, message
            )

            if isinstance(target_value, (bytes, str)):
                return len(target_value)
            elif isinstance(target_value, list):
                return len(target_value)
            else:
                raise ValueError(
                    f"length_of target '{target_field}' must be bytes, str, or list"
                )

        # Size of another field (in bytes)
        if "size_of" in field_spec:
            target_field = field_spec["size_of"]

            # Special case: "body" or "message" refers to the whole message
            if target_field in ("body", "message", "payload"):
                return len(message_bytes)

            target_value = self._resolve_auto_field_reference(
                target_field, context, message
            )
            target_spec = message.fields.get(target_field, {})

            # Serialize to get byte size
            serialized = message._serialize_value(target_value, target_spec, byteorder)
            return len(serialized)

        # Value from another field
        if "value_from" in field_spec:
            source_field = field_spec["value_from"]
            return self._resolve_auto_field_reference(source_field, context, message)

        # Custom compute function
        if "compute" in field_spec:
            compute_fn = field_spec["compute"]
            if not callable(compute_fn):
                raise ValueError(f"Field '{field_name}': 'compute' must be callable")
            return compute_fn(context)

        # No value specified
        raise ValueError(
            f"Auto field '{field_name}' must have one of: static, length_of, size_of, value_from, compute"
        )

    def _resolve_auto_field_reference(
        self, field_ref: str, context: Any, message: Message
    ) -> Any:
        """
        Resolve a field reference in automatic header/footer context.

        Args:
            field_ref: Field reference (may include dot notation)
            context: Context object
            message: Original message

        Returns:
            Referenced field value
        """
        # Check for cross-field reference (dot notation)
        if "." in field_ref:
            parts = field_ref.split(".")
            current = message

            # Navigate through the path
            for part in parts:
                if not hasattr(current, part):
                    raise ValueError(
                        f"Referenced field '{field_ref}' does not exist: "
                        f"'{part}' not found"
                    )
                current = getattr(current, part)

            return current

        # Simple field reference - check message first
        if hasattr(message, field_ref):
            return getattr(message, field_ref)

        # Try context
        if hasattr(context, field_ref):
            return getattr(context, field_ref)

        raise ValueError(f"Referenced field '{field_ref}' does not exist")

    def _serialize_auto_field_value(
        self, value: Any, field_spec: Dict[str, Any], byteorder: str, message: Message
    ) -> bytes:
        """
        Serialize an automatic field value to bytes.

        Args:
            value: Value to serialize
            field_spec: Field specification
            byteorder: Byte order ('big' or 'little')
            message: Original message (for _serialize_value compatibility)

        Returns:
            Serialized bytes
        """
        # Delegate to Message._serialize_value for consistency
        return message._serialize_value(value, field_spec, byteorder)

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

            # Get the data after the type header
            message_data = data[2 + type_length :]

            # Calculate header size (if any headers configured)
            header_size = 0
            with self._header_lock:
                if self._headers:
                    header_size = self._calculate_auto_fields_size(
                        self._headers, message_class
                    )

            # Check if we have enough data for headers
            if len(message_data) < header_size:
                with self._buffer_lock:
                    self._incomplete_buffers[source_id] = data
                return None

            # Skip headers for now - we'll validate them after deserializing the message
            message_body_start = header_size
            message_data_body = message_data[message_body_start:]

            # Deserialize message body
            try:
                message, body_bytes_consumed = message_class.deserialize_bytes(
                    message_data_body
                )
            except Exception as deserialize_error:
                # Check if this might be an incomplete message
                # If we have very little data, it's likely incomplete
                if len(message_data_body) < 10:  # Arbitrary threshold
                    with self._buffer_lock:
                        self._incomplete_buffers[source_id] = data
                    return None
                # Otherwise treat as invalid
                raise deserialize_error

            # Calculate footer size (if any footers configured)
            footer_size = 0
            with self._footer_lock:
                if self._footers:
                    footer_size = self._calculate_auto_fields_size(
                        self._footers, message_class
                    )

            # Check if we have enough data for footers
            footer_start = message_body_start + body_bytes_consumed
            if len(message_data) < footer_start + footer_size:
                with self._buffer_lock:
                    self._incomplete_buffers[source_id] = data
                return None

            # Validate headers (if any)
            if header_size > 0:
                header_data = message_data[0:header_size]
                with self._header_lock:
                    self._validate_auto_fields(
                        self._headers, header_data, message, message_class
                    )

            # Validate footers (if any)
            if footer_size > 0:
                footer_data = message_data[footer_start : footer_start + footer_size]
                with self._footer_lock:
                    self._validate_auto_fields(
                        self._footers, footer_data, message, message_class
                    )

            # Calculate remaining data
            total_consumed = (
                2 + type_length + header_size + body_bytes_consumed + footer_size
            )
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

    def _calculate_auto_fields_size(
        self, fields: Dict[str, Dict[str, Any]], message_class: Type[Message]
    ) -> int:
        """
        Calculate the total byte size of automatic header/footer fields.

        This is used during decoding to determine how many bytes to skip/validate.

        Args:
            fields: Field specifications (headers or footers)
            message_class: Message class being decoded

        Returns:
            Total size in bytes
        """
        total_size = 0
        byteorder = getattr(message_class, "encoding", None)
        if byteorder:
            byteorder = byteorder.value
        else:
            byteorder = "big"

        for field_name, field_spec in fields.items():
            field_type = field_spec.get("type")

            # For sized integer types like uint(8), int(32), etc.
            if isinstance(field_type, str) and (
                "int" in field_type or "uint" in field_type
            ):
                # Extract size from type string like "uint(32)"
                if "(" in field_type and ")" in field_type:
                    size_bits = int(field_type.split("(")[1].split(")")[0])
                    total_size += size_bits // 8
                else:
                    # Default int size
                    total_size += 4
            # For basic types
            elif field_type == "float":
                total_size += 4
            elif field_type == "double":
                total_size += 8
            elif field_type == "bool":
                total_size += 1
            # For custom encoders with a known size
            elif "encoder" in field_spec:
                encoder = field_spec["encoder"]
                if hasattr(encoder, "size"):
                    total_size += encoder.size
                else:
                    # Can't determine size statically
                    raise ValueError(
                        f"Cannot determine size of auto field '{field_name}' with custom encoder. "
                        f"Encoder must have a 'size' attribute."
                    )
            else:
                # Can't determine size for variable-length fields
                raise ValueError(
                    f"Cannot determine size of auto field '{field_name}'. "
                    f"Auto fields must have fixed-size types (int, uint, float, double, bool)."
                )

        return total_size

    def _validate_auto_fields(
        self,
        fields: Dict[str, Dict[str, Any]],
        field_data: bytes,
        message: Message,
        message_class: Type[Message],
    ) -> None:
        """
        Validate automatic header/footer fields during decoding.

        Deserializes the fields and checks that computed fields match expected values.

        Args:
            fields: Field specifications (headers or footers)
            field_data: Raw bytes containing the fields
            message: Decoded message instance
            message_class: Message class

        Raises:
            ValueError: If validation fails
        """
        offset = 0
        byteorder = getattr(message_class, "encoding", None)
        if byteorder:
            byteorder = byteorder.value
        else:
            byteorder = "big"

        # Get the original serialized message bytes for validation
        message_bytes = message.serialize_bytes()

        for field_name, field_spec in fields.items():
            # Deserialize the field value
            value, consumed = self._deserialize_auto_field_value(
                field_data[offset:], field_spec, byteorder, message_class
            )
            offset += consumed

            # For computed fields, verify the value matches
            if any(
                k in field_spec
                for k in ["compute", "length_of", "size_of", "value_from"]
            ):
                # Compute what the value should be
                class AutoFieldContext:
                    """Context for validation."""

                    def __init__(self, msg: Message, msg_bytes: bytes):
                        self.message = msg
                        self.message_bytes = msg_bytes
                        for fname in msg.fields.keys():
                            if hasattr(msg, fname):
                                setattr(self, fname, getattr(msg, fname))

                    def serialize_bytes(self) -> bytes:
                        return self.message_bytes

                context = AutoFieldContext(message, message_bytes)
                expected_value = self._compute_auto_field_value(
                    field_name, field_spec, context, message, message_bytes
                )

                # Compare values
                if value != expected_value:
                    raise ValueError(
                        f"Auto field '{field_name}' validation failed: "
                        f"expected {expected_value}, got {value}"
                    )

            # For static fields, verify the value matches
            elif "static" in field_spec:
                expected = field_spec["static"]
                if value != expected:
                    raise ValueError(
                        f"Auto field '{field_name}' validation failed: "
                        f"expected static value {expected}, got {value}"
                    )

    def _deserialize_auto_field_value(
        self,
        data: bytes,
        field_spec: Dict[str, Any],
        byteorder: str,
        message_class: Type[Message],
    ) -> Tuple[Any, int]:
        """
        Deserialize an automatic field value from bytes.

        Args:
            data: Bytes to deserialize from
            field_spec: Field specification
            byteorder: Byte order ('big' or 'little')
            message_class: Message class (for compatibility)

        Returns:
            Tuple of (deserialized value, bytes consumed)
        """
        field_type = field_spec.get("type")

        # For sized integer types
        if isinstance(field_type, str):
            if field_type.startswith("uint("):
                size_bits = int(field_type.split("(")[1].split(")")[0])
                size_bytes = size_bits // 8
                value = int.from_bytes(data[:size_bytes], byteorder, signed=False)
                return value, size_bytes
            elif field_type.startswith("int("):
                size_bits = int(field_type.split("(")[1].split(")")[0])
                size_bytes = size_bits // 8
                value = int.from_bytes(data[:size_bytes], byteorder, signed=True)
                return value, size_bytes
            elif field_type == "float":
                import struct

                fmt = "<f" if byteorder == "little" else ">f"
                value = struct.unpack(fmt, data[:4])[0]
                return value, 4
            elif field_type == "double":
                import struct

                fmt = "<d" if byteorder == "little" else ">d"
                value = struct.unpack(fmt, data[:8])[0]
                return value, 8
            elif field_type == "bool":
                value = bool(data[0])
                return value, 1

        # Custom encoder
        if "encoder" in field_spec:
            encoder = field_spec["encoder"]
            if hasattr(encoder, "decode"):
                value = encoder.decode(data, byteorder)
                size = getattr(encoder, "size", len(data))
                return value, size

        raise ValueError(f"Cannot deserialize auto field with type '{field_type}'")

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
