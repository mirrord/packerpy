"""Serialization implementation for BYTES and JSON formats."""

import json
from typing import Optional, Dict, Any

from packerpy.protocols.message import Message


class BytesSerializer:
    """
    Binary serializer using Message's native byte serialization.\n    \n    This is the most efficient format.
    """

    def serialize(self, message: Message) -> bytes:
        """Serialize message to BYTES format."""
        return message.serialize_bytes()

    def deserialize(self, data: bytes, message_class: type = None) -> Optional[Message]:
        """
        Deserialize message from BYTES format.

        Args:
            data: Bytes to deserialize
            message_class: Optional message class to deserialize into.
                          If provided, uses that class's deserialize_bytes method.
                          If not provided, uses generic Message.deserialize_bytes.

        Returns:
            Message instance or None if deserialization fails
        """
        try:
            if message_class is not None:
                message, bytes_consumed = message_class.deserialize_bytes(data)
            else:
                message, bytes_consumed = Message.deserialize_bytes(data)
            return message
        except Exception as e:
            print(f"Bytes deserialization failed: {e}")
            return None


class JSONSerializer:
    """
    JSON serializer for human-readable message serialization.

    Provides text-based encoding/decoding with UTF-8.
    Less efficient than binary but useful for:
    - Debugging and logging
    - Web APIs and REST interfaces
    - Interoperability with JSON-based systems
    - Human-readable message inspection

    Example:
        serializer = JSONSerializer()

        # Serialize to JSON bytes
        json_bytes = serializer.serialize(message)

        # Deserialize from JSON bytes
        message = serializer.deserialize(json_bytes, MessageClass)

        # Pretty-print for debugging
        json_str = serializer.serialize_to_string(message, indent=2)
    """

    def __init__(self, ensure_ascii: bool = False, indent: Optional[int] = None):
        """
        Initialize JSON serializer.

        Args:
            ensure_ascii: If True, escape non-ASCII characters. Default False for better readability.
            indent: Pretty-print indentation. None for compact output.
        """
        self.ensure_ascii = ensure_ascii
        self.indent = indent

    def serialize(self, message: Message) -> bytes:
        """
        Serialize message to JSON format as UTF-8 bytes.

        Args:
            message: Message instance to serialize

        Returns:
            UTF-8 encoded JSON bytes
        """
        data_dict = message.to_dict()
        json_str = json.dumps(
            data_dict, ensure_ascii=self.ensure_ascii, indent=self.indent
        )
        return json_str.encode("utf-8")

    def serialize_to_string(
        self, message: Message, indent: Optional[int] = None
    ) -> str:
        """
        Serialize message to JSON string.

        Useful for debugging and logging.

        Args:
            message: Message instance to serialize
            indent: Override default indentation for this call

        Returns:
            JSON string
        """
        data_dict = message.to_dict()
        use_indent = indent if indent is not None else self.indent
        return json.dumps(data_dict, ensure_ascii=self.ensure_ascii, indent=use_indent)

    def deserialize(self, data: bytes, message_class: type) -> Optional[Message]:
        """
        Deserialize message from JSON bytes.

        Args:
            data: UTF-8 encoded JSON bytes
            message_class: Message class to deserialize into

        Returns:
            Message instance or None if deserialization fails
        """
        try:
            json_str = data.decode("utf-8")
            data_dict = json.loads(json_str)
            return message_class.from_dict(data_dict)
        except Exception as e:
            print(f"JSON deserialization failed: {e}")
            return None

    def deserialize_from_string(
        self, json_str: str, message_class: type
    ) -> Optional[Message]:
        """
        Deserialize message from JSON string.

        Args:
            json_str: JSON string
            message_class: Message class to deserialize into

        Returns:
            Message instance or None if deserialization fails
        """
        try:
            data_dict = json.loads(json_str)
            return message_class.from_dict(data_dict)
        except Exception as e:
            print(f"JSON deserialization failed: {e}")
            return None
