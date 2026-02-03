"""Tests for deep assignment in cross-partial field references."""

import pytest
from packerpy.protocols.message import Message, Encoding
from packerpy.protocols.message_partial import MessagePartial


class TestDeepAssignmentBasic:
    """Tests for basic deep assignment functionality."""

    def test_deep_assignment_length_of_bytes(self):
        """Test deep assignment with length_of referencing bytes field."""

        class DataPartial(MessagePartial):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "length": {"type": "uint(16)"},
                "content": {"type": "bytes"},
            }

        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "header": {
                    "type": DataPartial,
                    "header.length": {"length_of": "payload"},
                },
                "payload": {"type": "bytes"},
            }

        # Create message
        header = DataPartial(length=0, content=b"Header")
        msg = TestMessage(header=header, payload=b"Test Data")

        # Serialize - header.length should be computed
        serialized = msg.serialize_bytes()

        # Check that header.length was set
        assert msg.header.length == 9  # len(b"Test Data")

        # Deserialize and verify
        decoded, _ = TestMessage.deserialize_bytes(serialized)
        assert decoded.header.length == 9
        assert decoded.payload == b"Test Data"

    def test_deep_assignment_length_of_message_partial(self):
        """Test deep assignment with length_of referencing entire MessagePartial."""

        class Header(MessagePartial):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "version": {"type": "uint(8)"},
                "payload_length": {"type": "uint(32)"},
            }

        class Payload(MessagePartial):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "data": {"type": "bytes"},
            }

        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "header": {
                    "type": Header,
                    "header.payload_length": {"length_of": "payload"},
                },
                "payload": {"type": Payload},
            }

        # Create message
        header = Header(version=1, payload_length=0)
        payload = Payload(data=b"Hello, World!")
        msg = TestMessage(header=header, payload=payload)

        # Serialize
        serialized = msg.serialize_bytes()

        # Check that header.payload_length is the serialized size of payload
        expected_length = len(payload.serialize_bytes())
        assert msg.header.payload_length == expected_length

        # Deserialize and verify
        decoded, _ = TestMessage.deserialize_bytes(serialized)
        assert decoded.header.payload_length == expected_length

    def test_deep_assignment_size_of(self):
        """Test deep assignment with size_of."""

        class Header(MessagePartial):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "data_size": {"type": "uint(32)"},
            }

        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "header": {
                    "type": Header,
                    "header.data_size": {"size_of": "data"},
                },
                "data": {"type": "bytes"},
            }

        # Create message
        header = Header(data_size=0)
        msg = TestMessage(header=header, data=b"ABC")

        # Serialize
        serialized = msg.serialize_bytes()

        # bytes type includes 4-byte length prefix + data
        assert msg.header.data_size == 7  # 4 (length) + 3 (data)

        # Deserialize and verify
        decoded, _ = TestMessage.deserialize_bytes(serialized)
        assert decoded.header.data_size == 7

    def test_deep_assignment_compute(self):
        """Test deep assignment with compute function."""

        class Header(MessagePartial):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "checksum": {"type": "uint(32)"},
            }

        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "header": {
                    "type": Header,
                    "header.checksum": {
                        "compute": lambda msg: sum(msg.payload) & 0xFFFFFFFF
                    },
                },
                "payload": {"type": "bytes"},
            }

        # Create message
        header = Header(checksum=0)
        msg = TestMessage(header=header, payload=b"Test")

        # Serialize
        serialized = msg.serialize_bytes()

        # Check checksum computation
        expected_checksum = sum(b"Test") & 0xFFFFFFFF
        assert msg.header.checksum == expected_checksum

        # Deserialize and verify
        decoded, _ = TestMessage.deserialize_bytes(serialized)
        assert decoded.header.checksum == expected_checksum


class TestDeepAssignmentNested:
    """Tests for deeply nested deep assignments."""

    def test_deep_assignment_two_levels(self):
        """Test deep assignment with two levels of nesting."""

        class InnerPartial(MessagePartial):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "count": {"type": "uint(16)"},
            }

        class OuterPartial(MessagePartial):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "inner": {"type": InnerPartial},
            }

        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "header": {
                    "type": OuterPartial,
                    "header.inner.count": {"length_of": "items"},
                },
                "items": {"type": "int(32)", "numlist": 5},
            }

        # Create message
        inner = InnerPartial(count=0)
        outer = OuterPartial(inner=inner)
        msg = TestMessage(header=outer, items=[1, 2, 3, 4, 5])

        # Serialize
        serialized = msg.serialize_bytes()

        # Check nested assignment
        assert msg.header.inner.count == 5

        # Deserialize and verify
        decoded, _ = TestMessage.deserialize_bytes(serialized)
        assert decoded.header.inner.count == 5


class TestDeepAssignmentMultiple:
    """Tests for multiple deep assignments in one field."""

    def test_multiple_deep_assignments(self):
        """Test multiple deep assignments to different nested fields."""

        class Header(MessagePartial):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "version": {"type": "uint(8)"},
                "payload_length": {"type": "uint(32)"},
                "checksum": {"type": "uint(32)"},
            }

        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "header": {
                    "type": Header,
                    "header.payload_length": {"length_of": "payload"},
                    "header.checksum": {
                        "compute": lambda msg: sum(msg.payload) & 0xFFFFFFFF
                    },
                },
                "payload": {"type": "bytes"},
            }

        # Create message
        header = Header(version=1, payload_length=0, checksum=0)
        payload_data = b"Important data"
        msg = TestMessage(header=header, payload=payload_data)

        # Serialize
        serialized = msg.serialize_bytes()

        # Check both assignments
        assert msg.header.payload_length == len(payload_data)
        assert msg.header.checksum == sum(payload_data) & 0xFFFFFFFF

        # Deserialize and verify
        decoded, _ = TestMessage.deserialize_bytes(serialized)
        assert decoded.header.payload_length == len(payload_data)
        assert decoded.header.checksum == sum(payload_data) & 0xFFFFFFFF


class TestDeepAssignmentCrossPartialReferences:
    """Tests combining deep assignments with cross-partial references."""

    def test_deep_assignment_with_cross_partial_reference(self):
        """Test deep assignment that references another partial's field."""

        class Header(MessagePartial):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "data_length": {"type": "uint(32)"},
            }

        class Payload(MessagePartial):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "data": {"type": "bytes"},
            }

        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "header": {
                    "type": Header,
                    "header.data_length": {"length_of": "payload.data"},
                },
                "payload": {"type": Payload},
            }

        # Create message
        header = Header(data_length=0)
        payload = Payload(data=b"Cross-partial reference data")
        msg = TestMessage(header=header, payload=payload)

        # Serialize
        serialized = msg.serialize_bytes()

        # Check assignment
        assert msg.header.data_length == 28  # len(b"Cross-partial reference data")

        # Deserialize and verify
        decoded, _ = TestMessage.deserialize_bytes(serialized)
        assert decoded.header.data_length == 28


class TestDeepAssignmentWithSerializers:
    """Tests for deep assignments with different serializers."""

    def test_deep_assignment_with_json_serializer(self):
        """Test deep assignment when payload uses JSON serializer."""
        from packerpy.protocols.serializer import BytesSerializer, JSONSerializer

        class Header(MessagePartial):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "version": {"type": "uint(8)"},
                "payload_length": {"type": "uint(32)"},
            }

        class Payload(MessagePartial):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "message": {"type": "str"},
                "count": {"type": "int"},
            }

        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "header": {
                    "type": Header,
                    "serializer": BytesSerializer(),
                    "header.payload_length": {"length_of": "payload"},
                },
                "payload": {"type": Payload, "serializer": JSONSerializer()},
            }

        # Create message
        header = Header(version=1, payload_length=0)
        payload = Payload(message="Hello", count=42)
        msg = TestMessage(header=header, payload=payload)

        # Serialize
        serialized = msg.serialize_bytes()

        # The payload_length should be the size of the JSON-serialized payload
        # Since we're using length_of on the MessagePartial with JSONSerializer,
        # it should compute the serialized size
        json_size = len(JSONSerializer().serialize(payload))
        assert msg.header.payload_length == json_size

        # Deserialize and verify
        decoded, _ = TestMessage.deserialize_bytes(serialized)
        assert decoded.header.payload_length == json_size
        assert decoded.payload.message == "Hello"
        assert decoded.payload.count == 42


class TestDeepAssignmentRealWorldScenario:
    """Test realistic protocol packet scenario."""

    def test_protocol_packet_with_auto_header(self):
        """Test complete protocol packet with automatic header computation."""

        class PacketHeader(MessagePartial):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "magic": {"type": "uint(16)"},
                "version": {"type": "uint(8)"},
                "flags": {"type": "uint(8)"},
                "payload_size": {"type": "uint(32)"},
                "header_checksum": {"type": "uint(16)"},
                "payload_checksum": {"type": "uint(32)"},
            }

        class PacketPayload(MessagePartial):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "data": {"type": "bytes"},
            }

        class ProtocolPacket(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "header": {
                    "type": PacketHeader,
                    "header.payload_size": {"length_of": "payload"},
                    "header.payload_checksum": {
                        "compute": lambda msg: sum(msg.payload.data) & 0xFFFFFFFF
                    },
                },
                "payload": {"type": PacketPayload},
            }

        # Create packet
        header = PacketHeader(
            magic=0xABCD,
            version=1,
            flags=0b00000011,
            payload_size=0,
            header_checksum=0,
            payload_checksum=0,
        )
        payload = PacketPayload(data=b"Critical mission data")

        packet = ProtocolPacket(header=header, payload=payload)

        # Manually set header_checksum (not auto-computed in this example)
        packet.header.header_checksum = 0x1234

        # Serialize
        serialized = packet.serialize_bytes()

        # Verify auto-computed fields
        payload_bytes = payload.serialize_bytes()
        assert packet.header.payload_size == len(payload_bytes)
        assert (
            packet.header.payload_checksum == sum(b"Critical mission data") & 0xFFFFFFFF
        )

        # Deserialize and verify
        decoded, _ = ProtocolPacket.deserialize_bytes(serialized)
        assert decoded.header.magic == 0xABCD
        assert decoded.header.version == 1
        assert decoded.header.payload_size == len(payload_bytes)
        assert (
            decoded.header.payload_checksum
            == sum(b"Critical mission data") & 0xFFFFFFFF
        )
        assert decoded.payload.data == b"Critical mission data"


class TestDeepAssignmentErrorHandling:
    """Tests for error handling in deep assignments."""

    def test_deep_assignment_nonexistent_field(self):
        """Test error when assigning to non-existent nested field."""

        class Header(MessagePartial):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "version": {"type": "uint(8)"},
            }

        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "header": {
                    "type": Header,
                    "header.nonexistent": {"length_of": "data"},
                },
                "data": {"type": "bytes"},
            }

        header = Header(version=1)
        msg = TestMessage(header=header, data=b"Test")

        # Should raise error during serialization
        with pytest.raises(ValueError, match="not found"):
            msg.serialize_bytes()

    def test_deep_assignment_invalid_nested_path(self):
        """Test error with invalid nested path."""

        class Header(MessagePartial):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "version": {"type": "uint(8)"},
            }

        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "header": {
                    "type": Header,
                    "header.version.subfield": {"length_of": "data"},
                },
                "data": {"type": "bytes"},
            }

        header = Header(version=1)
        msg = TestMessage(header=header, data=b"Test")

        # Should raise error - can't navigate into uint(8)
        with pytest.raises(ValueError, match="not found"):
            msg.serialize_bytes()

    def test_deep_assignment_non_dict_spec(self):
        """Test error when deep assignment spec is not a dictionary."""

        class Header(MessagePartial):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "length": {"type": "uint(32)"},
            }

        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "header": {
                    "type": Header,
                    "header.length": "invalid",  # Should be a dict
                },
                "data": {"type": "bytes"},
            }

        header = Header(length=0)
        msg = TestMessage(header=header, data=b"Test")

        # Should raise error
        with pytest.raises(ValueError, match="must be a dictionary"):
            msg.serialize_bytes()
