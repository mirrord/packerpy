"""Tests for field reference features in Message class."""

import pytest
from packerpy.protocols.message import Message, Encoding


class TestLengthPrefixedFields:
    """Tests for length_of field references."""

    def test_length_of_bytes(self):
        """Test automatic length computation for bytes field."""

        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "length": {"type": "uint(16)", "length_of": "data"},
                "data": {"type": "bytes"},
            }

        # Create message
        msg = TestMessage(length=0, data=b"Hello")

        # Serialize - length should be computed
        serialized = msg.serialize_bytes()

        # Check that length was computed
        assert msg.length == 5

        # Deserialize and verify
        decoded, consumed = TestMessage.deserialize_bytes(serialized)
        assert decoded.length == 5
        assert decoded.data == b"Hello"

    def test_length_of_string(self):
        """Test automatic length computation for string field."""

        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "str_length": {"type": "uint(32)", "length_of": "text"},
                "text": {"type": "str"},
            }

        msg = TestMessage(str_length=0, text="Test String")
        serialized = msg.serialize_bytes()

        # String length is the character count
        assert msg.str_length == 11

        decoded, _ = TestMessage.deserialize_bytes(serialized)
        assert decoded.str_length == 11
        assert decoded.text == "Test String"

    def test_length_of_list(self):
        """Test automatic length computation for list field."""

        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "count": {"type": "uint(8)", "length_of": "items"},
                "items": {"type": "int(32)", "numlist": 3},
            }

        msg = TestMessage(count=0, items=[10, 20, 30])
        serialized = msg.serialize_bytes()

        assert msg.count == 3

        decoded, _ = TestMessage.deserialize_bytes(serialized)
        assert decoded.count == 3
        assert decoded.items == [10, 20, 30]


class TestSizeOfFields:
    """Tests for size_of field references."""

    def test_size_of_integer(self):
        """Test byte size computation for integer field."""

        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "value": {"type": "int(64)"},
                "value_size": {"type": "uint(8)", "size_of": "value"},
            }

        msg = TestMessage(value=12345, value_size=0)
        serialized = msg.serialize_bytes()

        # int(64) is 8 bytes
        assert msg.value_size == 8

        decoded, _ = TestMessage.deserialize_bytes(serialized)
        assert decoded.value_size == 8
        assert decoded.value == 12345

    def test_size_of_bytes_with_length_prefix(self):
        """Test byte size includes length prefix."""

        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "data": {"type": "bytes"},
                "total_size": {"type": "uint(16)", "size_of": "data"},
            }

        msg = TestMessage(data=b"ABC", total_size=0)
        serialized = msg.serialize_bytes()

        # bytes type includes 4-byte length prefix + data
        assert msg.total_size == 7  # 4 (length) + 3 (data)

        decoded, _ = TestMessage.deserialize_bytes(serialized)
        assert decoded.total_size == 7
        assert decoded.data == b"ABC"


class TestVariableArraySize:
    """Tests for arrays with size from field references."""

    def test_array_size_from_field(self):
        """Test array with size determined by another field."""

        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "count": {"type": "uint(8)"},
                "values": {"type": "int(16)", "numlist": "count"},
            }

        # Create message with 4 items
        msg = TestMessage(count=4, values=[100, 200, 300, 400])
        serialized = msg.serialize_bytes()

        decoded, _ = TestMessage.deserialize_bytes(serialized)
        assert decoded.count == 4
        assert decoded.values == [100, 200, 300, 400]

    def test_array_size_field_reference_must_be_parsed_first(self):
        """Test that referenced field must come before array in field order."""

        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "count": {"type": "uint(8)"},
                "values": {"type": "int(16)", "numlist": "count"},
            }

        msg = TestMessage(count=2, values=[10, 20])
        serialized = msg.serialize_bytes()

        # Should deserialize successfully
        decoded, _ = TestMessage.deserialize_bytes(serialized)
        assert decoded.count == 2
        assert decoded.values == [10, 20]

    def test_variable_array_with_different_sizes(self):
        """Test multiple messages with different array sizes."""

        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "num_items": {"type": "uint(16)"},
                "items": {"type": "uint(32)", "numlist": "num_items"},
            }

        # Empty array
        msg1 = TestMessage(num_items=0, items=[])
        ser1 = msg1.serialize_bytes()
        dec1, _ = TestMessage.deserialize_bytes(ser1)
        assert dec1.num_items == 0
        assert dec1.items == []

        # Small array
        msg2 = TestMessage(num_items=2, items=[111, 222])
        ser2 = msg2.serialize_bytes()
        dec2, _ = TestMessage.deserialize_bytes(ser2)
        assert dec2.num_items == 2
        assert dec2.items == [111, 222]

        # Larger array
        msg3 = TestMessage(num_items=10, items=list(range(10)))
        ser3 = msg3.serialize_bytes()
        dec3, _ = TestMessage.deserialize_bytes(ser3)
        assert dec3.num_items == 10
        assert dec3.items == list(range(10))


class TestConditionalFields:
    """Tests for conditional field inclusion."""

    def test_conditional_field_included(self):
        """Test field included when condition is True."""

        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "has_extra": {"type": "bool"},
                "basic": {"type": "int(32)"},
                "extra": {
                    "type": "int(64)",
                    "condition": lambda msg: hasattr(msg, "has_extra")
                    and msg.has_extra,
                },
            }

        msg = TestMessage(has_extra=True, basic=100, extra=999)
        serialized = msg.serialize_bytes()

        decoded, _ = TestMessage.deserialize_bytes(serialized)
        assert decoded.has_extra is True
        assert decoded.basic == 100
        assert decoded.extra == 999

    def test_conditional_field_excluded(self):
        """Test field excluded when condition is False."""

        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "has_extra": {"type": "bool"},
                "basic": {"type": "int(32)"},
                "extra": {
                    "type": "int(64)",
                    "condition": lambda msg: hasattr(msg, "has_extra")
                    and msg.has_extra,
                },
            }

        msg = TestMessage(has_extra=False, basic=100, extra=None)
        serialized = msg.serialize_bytes()

        # Serialized size should be smaller (no extra field)
        # 1 (bool) + 4 (int32) = 5 bytes
        assert len(serialized) == 5

        decoded, _ = TestMessage.deserialize_bytes(serialized)
        assert decoded.has_extra is False
        assert decoded.basic == 100
        assert not hasattr(decoded, "extra")

    def test_conditional_field_based_on_flag_bits(self):
        """Test conditional field based on bit flags."""

        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "flags": {"type": "uint(8)"},
                "field_a": {
                    "type": "int(16)",
                    "condition": lambda msg: hasattr(msg, "flags")
                    and (msg.flags & 0x01),
                },
                "field_b": {
                    "type": "int(16)",
                    "condition": lambda msg: hasattr(msg, "flags")
                    and (msg.flags & 0x02),
                },
            }

        # Neither flag set
        msg1 = TestMessage(flags=0x00, field_a=None, field_b=None)
        ser1 = msg1.serialize_bytes()
        dec1, _ = TestMessage.deserialize_bytes(ser1)
        assert dec1.flags == 0x00
        assert not hasattr(dec1, "field_a")
        assert not hasattr(dec1, "field_b")

        # Only field_a
        msg2 = TestMessage(flags=0x01, field_a=111, field_b=None)
        ser2 = msg2.serialize_bytes()
        dec2, _ = TestMessage.deserialize_bytes(ser2)
        assert dec2.flags == 0x01
        assert dec2.field_a == 111
        assert not hasattr(dec2, "field_b")

        # Only field_b
        msg3 = TestMessage(flags=0x02, field_a=None, field_b=222)
        ser3 = msg3.serialize_bytes()
        dec3, _ = TestMessage.deserialize_bytes(ser3)
        assert dec3.flags == 0x02
        assert not hasattr(dec3, "field_a")
        assert dec3.field_b == 222

        # Both fields
        msg4 = TestMessage(flags=0x03, field_a=111, field_b=222)
        ser4 = msg4.serialize_bytes()
        dec4, _ = TestMessage.deserialize_bytes(ser4)
        assert dec4.flags == 0x03
        assert dec4.field_a == 111
        assert dec4.field_b == 222


class TestComputedFields:
    """Tests for computed field values."""

    def test_simple_computed_field(self):
        """Test basic computed field."""

        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "a": {"type": "int(32)"},
                "b": {"type": "int(32)"},
                "sum": {"type": "int(32)", "compute": lambda msg: msg.a + msg.b},
            }

        msg = TestMessage(a=10, b=20, sum=0)
        serialized = msg.serialize_bytes()

        # Sum should be computed
        assert msg.sum == 30

        decoded, _ = TestMessage.deserialize_bytes(serialized)
        assert decoded.a == 10
        assert decoded.b == 20
        assert decoded.sum == 30

    def test_checksum_computation(self):
        """Test checksum-style computation."""

        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "data": {"type": "bytes"},
                "checksum": {
                    "type": "uint(32)",
                    "compute": lambda msg: sum(msg.data) & 0xFFFFFFFF,
                },
            }

        msg = TestMessage(data=b"\x01\x02\x03\x04", checksum=0)
        serialized = msg.serialize_bytes()

        # Checksum should be sum of bytes
        assert msg.checksum == 10

        decoded, _ = TestMessage.deserialize_bytes(serialized)
        assert decoded.data == b"\x01\x02\x03\x04"
        assert decoded.checksum == 10


class TestValueFromFields:
    """Tests for value_from field references."""

    def test_value_from_another_field(self):
        """Test copying value from another field."""

        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "id": {"type": "uint(16)"},
                "id_copy": {"type": "uint(16)", "value_from": "id"},
            }

        msg = TestMessage(id=42, id_copy=0)
        serialized = msg.serialize_bytes()

        # id_copy should match id
        assert msg.id_copy == 42

        decoded, _ = TestMessage.deserialize_bytes(serialized)
        assert decoded.id == 42
        assert decoded.id_copy == 42


class TestCombinedFeatures:
    """Tests combining multiple field reference features."""

    def test_length_prefix_with_conditional_field(self):
        """Test combining length prefix and conditional fields."""

        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "has_payload": {"type": "bool"},
                "payload_length": {
                    "type": "uint(16)",
                    "length_of": "payload",
                    "condition": lambda msg: hasattr(msg, "has_payload")
                    and msg.has_payload,
                },
                "payload": {
                    "type": "bytes",
                    "condition": lambda msg: hasattr(msg, "has_payload")
                    and msg.has_payload,
                },
            }

        # With payload
        msg1 = TestMessage(has_payload=True, payload_length=0, payload=b"Test")
        ser1 = msg1.serialize_bytes()
        dec1, _ = TestMessage.deserialize_bytes(ser1)
        assert dec1.has_payload is True
        assert dec1.payload_length == 4
        assert dec1.payload == b"Test"

        # Without payload
        msg2 = TestMessage(has_payload=False, payload_length=None, payload=None)
        ser2 = msg2.serialize_bytes()
        dec2, _ = TestMessage.deserialize_bytes(ser2)
        assert dec2.has_payload is False
        assert not hasattr(dec2, "payload_length")
        assert not hasattr(dec2, "payload")

    def test_variable_array_with_computed_count(self):
        """Test array size field computed from array length."""

        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "count": {"type": "uint(8)", "length_of": "items"},
                "items": {"type": "int(32)", "numlist": "count"},
            }

        # Note: During encoding, count is computed from items
        # During decoding, count is used to read items
        msg = TestMessage(count=0, items=[1, 2, 3, 4, 5])
        serialized = msg.serialize_bytes()

        assert msg.count == 5

        decoded, _ = TestMessage.deserialize_bytes(serialized)
        assert decoded.count == 5
        assert decoded.items == [1, 2, 3, 4, 5]

    def test_complex_protocol_packet(self):
        """Test realistic protocol packet with multiple features."""

        class PacketMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "version": {"type": "uint(8)"},
                "flags": {"type": "uint(8)"},
                "payload_length": {"type": "uint(32)", "length_of": "payload"},
                "payload": {"type": "bytes"},
                "has_signature": {
                    "type": "bool",
                    "compute": lambda msg: (msg.flags & 0x80) != 0,
                },
                "signature": {
                    "type": "bytes",
                    "condition": lambda msg: hasattr(msg, "has_signature")
                    and msg.has_signature,
                },
            }

        # Packet with signature (flag 0x80 set)
        msg1 = PacketMessage(
            version=1,
            flags=0x80,
            payload_length=0,
            payload=b"Important data",
            has_signature=False,  # Will be computed
            signature=b"\xaa\xbb\xcc\xdd",
        )
        ser1 = msg1.serialize_bytes()

        assert msg1.payload_length == 14
        assert msg1.has_signature is True

        dec1, _ = PacketMessage.deserialize_bytes(ser1)
        assert dec1.version == 1
        assert dec1.flags == 0x80
        assert dec1.payload_length == 14
        assert dec1.payload == b"Important data"
        assert dec1.has_signature is True
        assert dec1.signature == b"\xaa\xbb\xcc\xdd"

        # Packet without signature (flag 0x80 not set)
        msg2 = PacketMessage(
            version=1,
            flags=0x00,
            payload_length=0,
            payload=b"Data",
            has_signature=False,
            signature=None,
        )
        ser2 = msg2.serialize_bytes()

        assert msg2.payload_length == 4
        assert msg2.has_signature is False

        dec2, _ = PacketMessage.deserialize_bytes(ser2)
        assert dec2.version == 1
        assert dec2.flags == 0x00
        assert dec2.payload_length == 4
        assert dec2.payload == b"Data"
        assert dec2.has_signature is False
        assert not hasattr(dec2, "signature")


class TestErrorHandling:
    """Tests for error handling in field references."""

    def test_invalid_field_reference(self):
        """Test error when referencing non-existent field."""

        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "length": {"type": "uint(16)", "length_of": "nonexistent"},
                "data": {"type": "bytes"},
            }

        msg = TestMessage(length=0, data=b"Test")

        with pytest.raises(
            ValueError, match="Referenced field 'nonexistent' does not exist"
        ):
            msg.serialize_bytes()

    def test_forward_reference_in_numlist(self):
        """Test error when numlist references field that hasn't been parsed yet."""

        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "items": {
                    "type": "int(32)",
                    "numlist": "count",
                },  # References count which comes after
                "count": {"type": "uint(8)"},
            }

        msg = TestMessage(items=[1, 2, 3], count=3)
        serialized = msg.serialize_bytes()

        # During deserialization, count hasn't been parsed yet when we need it
        with pytest.raises(ValueError, match="hasn't been parsed yet"):
            TestMessage.deserialize_bytes(serialized)

    def test_non_callable_condition(self):
        """Test error when condition is not callable."""

        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "flag": {"type": "bool"},
                "data": {"type": "int(32)", "condition": "not callable"},
            }

        msg = TestMessage(flag=True, data=42)

        with pytest.raises(ValueError, match="'condition' must be callable"):
            msg.serialize_bytes()

    def test_non_callable_compute(self):
        """Test error when compute is not callable."""

        class TestMessage(Message):
            encoding = Encoding.BIG_ENDIAN
            fields = {
                "value": {"type": "int(32)", "compute": 42},
            }

        msg = TestMessage(value=0)

        with pytest.raises(ValueError, match="'compute' must be callable"):
            msg.serialize_bytes()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
