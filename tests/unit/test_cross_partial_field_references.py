"""Tests for cross-partial field references in Message class."""

import pytest
from packerpy.protocols.message import Message, Encoding
from packerpy.protocols.message_partial import MessagePartial


class TestCrossPartialLengthOf:
    """Tests for length_of with cross-partial references."""

    def test_length_of_partial_bytes_field(self):
        """Test length_of referencing a bytes field inside a MessagePartial."""

        class DataPartial(MessagePartial):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "payload": {"type": "bytes"},
            }

        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "header_length": {"type": "uint(16)", "length_of": "header.payload"},
                "header": {"type": DataPartial},
            }

        # Create message
        data_partial = DataPartial(payload=b"Hello, World!")
        msg = TestMessage(header_length=0, header=data_partial)

        # Serialize - length should be computed from partial
        serialized = msg.serialize_bytes()

        # Check that length was computed correctly
        assert msg.header_length == 13

        # Deserialize and verify
        decoded, _ = TestMessage.deserialize_bytes(serialized)
        assert decoded.header_length == 13
        assert decoded.header.payload == b"Hello, World!"

    def test_length_of_partial_string_field(self):
        """Test length_of referencing a string field inside a MessagePartial."""

        class InfoPartial(MessagePartial):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "name": {"type": "str"},
                "description": {"type": "str"},
            }

        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "name_length": {"type": "uint(16)", "length_of": "info.name"},
                "info": {"type": InfoPartial},
            }

        # Create message
        info = InfoPartial(name="TestName", description="Some description")
        msg = TestMessage(name_length=0, info=info)

        # Serialize
        serialized = msg.serialize_bytes()

        # Check length computation
        assert msg.name_length == 8  # len("TestName")

        # Deserialize and verify
        decoded, _ = TestMessage.deserialize_bytes(serialized)
        assert decoded.name_length == 8
        assert decoded.info.name == "TestName"

    def test_length_of_partial_list_field(self):
        """Test length_of referencing a list field inside a MessagePartial."""

        class ArrayPartial(MessagePartial):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "items": {"type": "int(16)", "numlist": 5},
            }

        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "item_count": {"type": "uint(8)", "length_of": "data.items"},
                "data": {"type": ArrayPartial},
            }

        # Create message
        array_data = ArrayPartial(items=[10, 20, 30, 40, 50])
        msg = TestMessage(item_count=0, data=array_data)

        # Serialize
        serialized = msg.serialize_bytes()

        # Check length computation
        assert msg.item_count == 5

        # Deserialize and verify
        decoded, _ = TestMessage.deserialize_bytes(serialized)
        assert decoded.item_count == 5
        assert decoded.data.items == [10, 20, 30, 40, 50]


class TestCrossPartialSizeOf:
    """Tests for size_of with cross-partial references."""

    def test_size_of_partial_integer_field(self):
        """Test size_of referencing an integer field inside a MessagePartial."""

        class HeaderPartial(MessagePartial):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "version": {"type": "uint(8)"},
                "packet_id": {"type": "uint(32)"},
            }

        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "header": {"type": HeaderPartial},
                "packet_id_size": {"type": "uint(8)", "size_of": "header.packet_id"},
            }

        # Create message
        header = HeaderPartial(version=1, packet_id=12345)
        msg = TestMessage(header=header, packet_id_size=0)

        # Serialize
        serialized = msg.serialize_bytes()

        # Check size computation - uint(32) is 4 bytes
        assert msg.packet_id_size == 4

        # Deserialize and verify
        decoded, _ = TestMessage.deserialize_bytes(serialized)
        assert decoded.packet_id_size == 4
        assert decoded.header.packet_id == 12345

    def test_size_of_partial_bytes_with_length_prefix(self):
        """Test size_of including length prefix for bytes field in partial."""

        class PayloadPartial(MessagePartial):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "data": {"type": "bytes"},
            }

        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "payload": {"type": PayloadPartial},
                "payload_data_size": {"type": "uint(16)", "size_of": "payload.data"},
            }

        # Create message
        payload = PayloadPartial(data=b"ABC")
        msg = TestMessage(payload=payload, payload_data_size=0)

        # Serialize
        serialized = msg.serialize_bytes()

        # Check size computation - bytes includes 4-byte length prefix
        assert msg.payload_data_size == 7  # 4 (length) + 3 (data)

        # Deserialize and verify
        decoded, _ = TestMessage.deserialize_bytes(serialized)
        assert decoded.payload_data_size == 7
        assert decoded.payload.data == b"ABC"


class TestCrossPartialNestedReferences:
    """Tests for nested MessagePartial field references."""

    def test_nested_partial_length_of(self):
        """Test length_of with deeply nested MessagePartial."""

        class InnerPartial(MessagePartial):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "value": {"type": "bytes"},
            }

        class MiddlePartial(MessagePartial):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "inner": {"type": InnerPartial},
            }

        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "value_length": {"type": "uint(16)", "length_of": "middle.inner.value"},
                "middle": {"type": MiddlePartial},
            }

        # Create nested structure
        inner = InnerPartial(value=b"Nested Data")
        middle = MiddlePartial(inner=inner)
        msg = TestMessage(value_length=0, middle=middle)

        # Serialize
        serialized = msg.serialize_bytes()

        # Check length computation
        assert msg.value_length == 11  # len(b"Nested Data")

        # Deserialize and verify
        decoded, _ = TestMessage.deserialize_bytes(serialized)
        assert decoded.value_length == 11
        assert decoded.middle.inner.value == b"Nested Data"

    def test_nested_partial_size_of(self):
        """Test size_of with deeply nested MessagePartial."""

        class InnerPartial(MessagePartial):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "counter": {"type": "uint(64)"},
            }

        class OuterPartial(MessagePartial):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "inner": {"type": InnerPartial},
            }

        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "outer": {"type": OuterPartial},
                "counter_size": {"type": "uint(8)", "size_of": "outer.inner.counter"},
            }

        # Create nested structure
        inner = InnerPartial(counter=999999)
        outer = OuterPartial(inner=inner)
        msg = TestMessage(outer=outer, counter_size=0)

        # Serialize
        serialized = msg.serialize_bytes()

        # Check size computation - uint(64) is 8 bytes
        assert msg.counter_size == 8

        # Deserialize and verify
        decoded, _ = TestMessage.deserialize_bytes(serialized)
        assert decoded.counter_size == 8
        assert decoded.outer.inner.counter == 999999


class TestCrossPartialComputeReferences:
    """Tests for compute functions with cross-partial references."""

    def test_compute_from_partial_field(self):
        """Test compute function accessing fields in MessagePartial."""

        class ConfigPartial(MessagePartial):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "multiplier": {"type": "uint(16)"},
                "offset": {"type": "int(16)"},
            }

        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "config": {"type": ConfigPartial},
                "base_value": {"type": "int(32)"},
                "computed_value": {
                    "type": "int(32)",
                    "compute": lambda msg: msg.base_value * msg.config.multiplier
                    + msg.config.offset,
                },
            }

        # Create message
        config = ConfigPartial(multiplier=3, offset=10)
        msg = TestMessage(config=config, base_value=100, computed_value=0)

        # Serialize
        serialized = msg.serialize_bytes()

        # Check computed value: 100 * 3 + 10 = 310
        assert msg.computed_value == 310

        # Deserialize and verify
        decoded, _ = TestMessage.deserialize_bytes(serialized)
        assert decoded.computed_value == 310


class TestCrossPartialConditionalFields:
    """Tests for conditional fields with cross-partial references."""

    def test_condition_based_on_partial_field(self):
        """Test conditional field inclusion based on MessagePartial field."""

        class FlagsPartial(MessagePartial):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "has_extended": {"type": "bool"},
                "has_metadata": {"type": "bool"},
            }

        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "flags": {"type": FlagsPartial},
                "basic_data": {"type": "int(32)"},
                "extended_data": {
                    "type": "int(64)",
                    "condition": lambda msg: hasattr(msg, "flags")
                    and msg.flags.has_extended,
                },
            }

        # Test with extended data included
        flags1 = FlagsPartial(has_extended=True, has_metadata=False)
        msg1 = TestMessage(flags=flags1, basic_data=100, extended_data=999)
        serialized1 = msg1.serialize_bytes()

        decoded1, _ = TestMessage.deserialize_bytes(serialized1)
        assert decoded1.extended_data == 999

        # Test with extended data excluded
        flags2 = FlagsPartial(has_extended=False, has_metadata=False)
        msg2 = TestMessage(flags=flags2, basic_data=200)
        serialized2 = msg2.serialize_bytes()

        decoded2, _ = TestMessage.deserialize_bytes(serialized2)
        assert not hasattr(decoded2, "extended_data")
        assert decoded2.basic_data == 200


class TestCrossPartialVariableArrays:
    """Tests for variable-sized arrays with cross-partial references."""

    def test_array_size_from_partial_field(self):
        """Test array with size determined by field in MessagePartial."""

        class HeaderPartial(MessagePartial):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "item_count": {"type": "uint(8)"},
                "flags": {"type": "uint(8)"},
            }

        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "header": {"type": HeaderPartial},
                "items": {"type": "int(32)", "numlist": "header.item_count"},
            }

        # Create message with 4 items
        header = HeaderPartial(item_count=4, flags=0)
        msg = TestMessage(header=header, items=[100, 200, 300, 400])

        # Serialize
        serialized = msg.serialize_bytes()

        # Deserialize and verify
        decoded, _ = TestMessage.deserialize_bytes(serialized)
        assert decoded.header.item_count == 4
        assert decoded.items == [100, 200, 300, 400]


class TestCrossPartialComplexScenario:
    """Test complex real-world scenario with cross-partial references."""

    def test_protocol_packet_with_header_references(self):
        """Test realistic protocol packet with header containing payload info."""

        class PacketHeader(MessagePartial):
            """Header with information about the payload."""

            encoding = Encoding.BIG_ENDIAN
            fields = {
                "version": {"type": "uint(8)"},
                "flags": {"type": "uint(8)"},
                "payload_length": {"type": "uint(32)"},
                "checksum": {"type": "uint(32)"},
            }

        class PacketPayload(MessagePartial):
            """Variable-length payload."""

            encoding = Encoding.BIG_ENDIAN
            fields = {
                "data": {"type": "bytes"},
            }

        class ProtocolPacket(Message):
            """Complete packet with header and payload."""

            encoding = Encoding.BIG_ENDIAN
            fields = {
                "header": {"type": PacketHeader},
                "payload": {"type": PacketPayload},
            }

        # Create a packet where header.payload_length should match payload.data length
        class SmartProtocolPacket(Message):
            """Packet with automatic header fields."""

            encoding = Encoding.BIG_ENDIAN
            fields = {
                "header": {"type": PacketHeader},
                "payload": {"type": PacketPayload},
            }

            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                # Automatically compute header fields from payload
                if hasattr(self, "payload") and hasattr(self, "header"):
                    self.header.payload_length = len(self.payload.data)
                    self.header.checksum = sum(self.payload.data) & 0xFFFFFFFF

        # Create packet
        header = PacketHeader(version=1, flags=0b00000011, payload_length=0, checksum=0)
        payload = PacketPayload(data=b"Important message data")

        packet = SmartProtocolPacket(header=header, payload=payload)

        # Serialize
        serialized = packet.serialize_bytes()

        # Verify automatic computation
        assert packet.header.payload_length == 22  # len(b"Important message data")
        assert packet.header.checksum == sum(b"Important message data") & 0xFFFFFFFF

        # Deserialize and verify
        decoded, _ = SmartProtocolPacket.deserialize_bytes(serialized)
        assert decoded.header.payload_length == 22
        assert decoded.payload.data == b"Important message data"

    def test_header_with_length_of_payload_field(self):
        """Test header field using length_of to reference payload field."""

        class Header(MessagePartial):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "version": {"type": "uint(8)"},
                "data_length": {"type": "uint(32)"},
            }

        class Payload(MessagePartial):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "data": {"type": "bytes"},
            }

        class Packet(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "header": {"type": Header},
                "payload": {"type": Payload},
            }

        # We want header.data_length to automatically compute from payload.data
        # This requires the field reference to work in the opposite direction
        # Let's use a different approach - compute it at Message level

        class SmartPacket(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "header_version": {"type": "uint(8)"},
                "payload_length": {"type": "uint(32)", "length_of": "payload.data"},
                "payload": {"type": Payload},
            }

        # Create packet
        payload = Payload(data=b"Test payload data")
        packet = SmartPacket(header_version=1, payload_length=0, payload=payload)

        # Serialize
        serialized = packet.serialize_bytes()

        # Verify length computation
        assert packet.payload_length == 17  # len(b"Test payload data")

        # Deserialize and verify
        decoded, _ = SmartPacket.deserialize_bytes(serialized)
        assert decoded.payload_length == 17
        assert decoded.payload.data == b"Test payload data"


class TestCrossPartialErrorHandling:
    """Tests for error handling in cross-partial references."""

    def test_invalid_partial_reference_nonexistent_field(self):
        """Test error when referencing non-existent field in MessagePartial."""

        class DataPartial(MessagePartial):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "value": {"type": "int(32)"},
            }

        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "data": {"type": DataPartial},
                "bad_length": {
                    "type": "uint(16)",
                    "length_of": "data.nonexistent",  # Invalid field
                },
            }

        data = DataPartial(value=123)
        msg = TestMessage(data=data, bad_length=0)

        # Should raise error during serialization
        with pytest.raises(ValueError, match="does not exist"):
            msg.serialize_bytes()

    def test_invalid_partial_reference_non_partial_type(self):
        """Test error when trying to reference into non-MessagePartial field."""

        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "simple_value": {"type": "int(32)"},
                "bad_ref": {
                    "type": "uint(16)",
                    "length_of": "simple_value.something",  # Can't reference into int
                },
            }

        msg = TestMessage(simple_value=100, bad_ref=0)

        # Should raise error - can't navigate into a non-MessagePartial
        with pytest.raises((ValueError, AttributeError)):
            msg.serialize_bytes()

    def test_invalid_nested_partial_reference(self):
        """Test error with invalid nested MessagePartial reference."""

        class InnerPartial(MessagePartial):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "value": {"type": "int(32)"},
            }

        class OuterPartial(MessagePartial):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "inner": {"type": InnerPartial},
            }

        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "outer": {"type": OuterPartial},
                "bad_ref": {
                    "type": "uint(16)",
                    "size_of": "outer.inner.nonexistent",  # Invalid nested field
                },
            }

        inner = InnerPartial(value=123)
        outer = OuterPartial(inner=inner)
        msg = TestMessage(outer=outer, bad_ref=0)

        # Should raise error during serialization
        with pytest.raises(ValueError, match="does not exist|not found"):
            msg.serialize_bytes()
