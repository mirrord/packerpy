"""Unit tests for protocols.serializer module."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from packerpy.protocols.serializer import BytesSerializer
from packerpy.protocols.message import Message


class TestBytesSerializer:
    """Test suite for BytesSerializer."""

    def test_initialization(self):
        """Test BytesSerializer initialization."""
        serializer = BytesSerializer()
        assert serializer is not None

    @patch("packerpy.protocols.message.Message")
    def test_serialize_calls_message_serialize_bytes(self, mock_message_class):
        """Test serialize calls Message.serialize_bytes()."""
        serializer = BytesSerializer()
        mock_message = Mock()
        mock_message.serialize_bytes.return_value = b"serialized_data"

        result = serializer.serialize(mock_message)

        assert result == b"serialized_data"
        mock_message.serialize_bytes.assert_called_once()

    @patch("packerpy.protocols.message.Message")
    def test_serialize_returns_bytes(self, mock_message_class):
        """Test serialize returns bytes."""
        serializer = BytesSerializer()
        mock_message = Mock()
        mock_message.serialize_bytes.return_value = b"test_bytes"

        result = serializer.serialize(mock_message)

        assert isinstance(result, bytes)

    @patch("packerpy.protocols.message.Message.deserialize_bytes")
    def test_deserialize_calls_message_deserialize_bytes(self, mock_deserialize):
        """Test deserialize calls Message.deserialize_bytes()."""
        serializer = BytesSerializer()
        mock_message = Mock()
        mock_deserialize.return_value = (mock_message, 10)

        result = serializer.deserialize(b"test_data")

        assert result == mock_message
        mock_deserialize.assert_called_once_with(b"test_data")

    @patch("packerpy.protocols.message.Message.deserialize_bytes")
    def test_deserialize_handles_exception(self, mock_deserialize):
        """Test deserialize handles exceptions and returns None."""
        serializer = BytesSerializer()
        mock_deserialize.side_effect = ValueError("Invalid data")

        result = serializer.deserialize(b"invalid_data")

        assert result is None

    @patch("packerpy.protocols.message.Message.deserialize_bytes")
    def test_deserialize_returns_none_on_any_exception(self, mock_deserialize):
        """Test deserialize returns None for any exception."""
        serializer = BytesSerializer()
        mock_deserialize.side_effect = Exception("Generic error")

        result = serializer.deserialize(b"bad_data")

        assert result is None

    @patch("packerpy.protocols.message.Message.deserialize_bytes")
    def test_deserialize_with_empty_data(self, mock_deserialize):
        """Test deserialize with empty data."""
        serializer = BytesSerializer()
        mock_deserialize.side_effect = ValueError("Empty data")

        result = serializer.deserialize(b"")

        assert result is None

    @patch("packerpy.protocols.message.Message")
    def test_serialize_with_complex_message(self, mock_message_class):
        """Test serialization with complex message data."""
        serializer = BytesSerializer()
        mock_message = Mock()
        complex_data = b"\x00\x01\x02\x03\xff\xfe\xfd"
        mock_message.serialize_bytes.return_value = complex_data

        result = serializer.serialize(mock_message)

        assert result == complex_data

    @patch("packerpy.protocols.message.Message.deserialize_bytes")
    def test_deserialize_ignores_bytes_consumed(self, mock_deserialize):
        """Test deserialize only returns the message, not bytes consumed."""
        serializer = BytesSerializer()
        mock_message = Mock()
        # deserialize_bytes returns (message, bytes_consumed)
        mock_deserialize.return_value = (mock_message, 42)

        result = serializer.deserialize(b"test_data")

        # Should only return the message, not the tuple
        assert result == mock_message
        assert not isinstance(result, tuple)

    def test_serialize_and_deserialize_are_independent(self):
        """Test that serialize and deserialize can be used independently."""
        serializer = BytesSerializer()

        # These methods don't share state
        assert hasattr(serializer, "serialize")
        assert hasattr(serializer, "deserialize")
        assert callable(serializer.serialize)
        assert callable(serializer.deserialize)

    @patch("packerpy.protocols.message.Message.deserialize_bytes")
    def test_deserialize_prints_error_message(self, mock_deserialize, capsys):
        """Test that deserialize prints error message on failure."""
        serializer = BytesSerializer()
        mock_deserialize.side_effect = ValueError("Test error")

        result = serializer.deserialize(b"bad_data")

        captured = capsys.readouterr()
        assert "Bytes deserialization failed:" in captured.out
        assert result is None
