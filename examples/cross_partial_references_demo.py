"""
Demonstration of cross-partial field references.

This example shows how to use field references that span across MessagePartial
objects. This is particularly useful for protocol headers that need to contain
information about the payload.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from packerpy.protocols import Message, Protocol, protocol
from packerpy.protocols.message import Encoding
from packerpy.protocols.message_partial import MessagePartial


# Create a protocol instance
NetworkProtocol = Protocol()


# Example 1: Header with payload length reference
class PayloadData(MessagePartial):
    """Payload with variable-length data."""

    encoding = Encoding.BIG_ENDIAN
    fields = {
        "data": {"type": "bytes"},
    }


@protocol(NetworkProtocol)
class PacketWithHeader(Message):
    """
    Packet where the header's payload_length field is automatically computed
    from the payload's data field.
    """

    encoding = Encoding.BIG_ENDIAN
    fields = {
        "version": {"type": "uint(8)"},
        "payload_length": {
            "type": "uint(32)",
            "length_of": "payload.data",  # Cross-partial reference
        },
        "payload": {"type": PayloadData},
    }


# Example 2: Array size from header field
class ArrayHeader(MessagePartial):
    """Header containing array metadata."""

    encoding = Encoding.BIG_ENDIAN
    fields = {
        "magic": {"type": "uint(16)"},
        "item_count": {"type": "uint(8)"},
        "flags": {"type": "uint(8)"},
    }


@protocol(NetworkProtocol)
class ArrayMessage(Message):
    """
    Message with array size determined by a field in the header.
    """

    encoding = Encoding.BIG_ENDIAN
    fields = {
        "header": {"type": ArrayHeader},
        "items": {
            "type": "int(32)",
            "numlist": "header.item_count",  # Cross-partial reference
        },
    }


# Example 3: Complex protocol packet with nested partials
class ProtocolHeader(MessagePartial):
    """Protocol header with metadata."""

    encoding = Encoding.BIG_ENDIAN
    fields = {
        "version": {"type": "uint(8)"},
        "flags": {"type": "uint(8)"},
        "data_length": {"type": "uint(32)"},
        "checksum": {"type": "uint(32)"},
    }


class SensorPayload(MessagePartial):
    """Sensor data payload."""

    encoding = Encoding.BIG_ENDIAN
    fields = {
        "sensor_id": {"type": "str"},
        "temperature": {"type": "float"},
        "humidity": {"type": "float"},
        "pressure": {"type": "float"},
    }


@protocol(NetworkProtocol)
class SensorPacket(Message):
    """
    Complete sensor packet with automatic header field computation.
    """

    encoding = Encoding.BIG_ENDIAN
    fields = {
        "header": {"type": ProtocolHeader},
        "payload": {"type": SensorPayload},
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Automatically compute header fields from payload if both exist
        if hasattr(self, "payload") and hasattr(self, "header"):
            # Compute the byte size of the payload
            payload_bytes = self.payload.serialize_bytes()
            self.header.data_length = len(payload_bytes)
            # Compute a simple checksum
            self.header.checksum = sum(payload_bytes) & 0xFFFFFFFF


# Example 4: Conditional fields based on partial flags
class ControlFlags(MessagePartial):
    """Control flags determining message structure."""

    encoding = Encoding.BIG_ENDIAN
    fields = {
        "has_timestamp": {"type": "bool"},
        "has_metadata": {"type": "bool"},
        "has_extended": {"type": "bool"},
        "reserved": {"type": "uint(8)"},
    }


@protocol(NetworkProtocol)
class ConditionalMessage(Message):
    """
    Message with conditional fields based on flags in a MessagePartial.
    """

    encoding = Encoding.BIG_ENDIAN
    fields = {
        "flags": {"type": ControlFlags},
        "basic_data": {"type": "int(32)"},
        "timestamp": {
            "type": "uint(64)",
            "condition": lambda msg: hasattr(msg, "flags") and msg.flags.has_timestamp,
        },
        "metadata": {
            "type": "str",
            "condition": lambda msg: hasattr(msg, "flags") and msg.flags.has_metadata,
        },
        "extended_data": {
            "type": "bytes",
            "condition": lambda msg: hasattr(msg, "flags") and msg.flags.has_extended,
        },
    }


# Example 5: Nested partials with deep references
class InnerData(MessagePartial):
    """Inner-most data structure."""

    encoding = Encoding.BIG_ENDIAN
    fields = {
        "value": {"type": "bytes"},
    }


class MiddleLayer(MessagePartial):
    """Middle layer containing inner data."""

    encoding = Encoding.BIG_ENDIAN
    fields = {
        "inner": {"type": InnerData},
    }


@protocol(NetworkProtocol)
class NestedPacket(Message):
    """
    Message with nested MessagePartial references.
    """

    encoding = Encoding.BIG_ENDIAN
    fields = {
        "middle": {"type": MiddleLayer},
        "value_length": {
            "type": "uint(32)",
            "length_of": "middle.inner.value",  # Deep nested reference
        },
    }


def demo_basic_cross_partial_reference():
    """Demonstrate basic cross-partial field reference."""
    print("=" * 70)
    print("Example 1: Basic Cross-Partial Reference")
    print("=" * 70)

    # Create payload
    payload = PayloadData(data=b"Hello, PackerPy with cross-partial refs!")

    # Create packet - payload_length will be computed automatically
    packet = PacketWithHeader(version=1, payload_length=0, payload=payload)

    print(f"\nOriginal packet:")
    print(f"  Version: {packet.version}")
    print(f"  Payload data: {packet.payload.data}")
    print(f"  Payload length (before serialization): {packet.payload_length}")

    # Serialize - this is when the cross-partial reference is computed
    serialized = packet.serialize_bytes()
    print(f"\n  Payload length (after serialization): {packet.payload_length}")
    print(f"\nSerialized: {len(serialized)} bytes")

    # Deserialize
    decoded, _ = PacketWithHeader.deserialize_bytes(serialized)
    print(f"\nDecoded packet:")
    print(f"  Version: {decoded.version}")
    print(f"  Payload length: {decoded.payload_length}")
    print(f"  Payload data: {decoded.payload.data}")


def demo_array_size_from_header():
    """Demonstrate array size determined by header field."""
    print("\n" + "=" * 70)
    print("Example 2: Array Size from Header Field")
    print("=" * 70)

    # Create header
    header = ArrayHeader(magic=0xABCD, item_count=5, flags=0x01)

    # Create message with array - size determined by header.item_count
    message = ArrayMessage(header=header, items=[100, 200, 300, 400, 500])

    print(f"\nOriginal message:")
    print(f"  Header magic: 0x{message.header.magic:04X}")
    print(f"  Header item_count: {message.header.item_count}")
    print(f"  Items: {message.items}")

    # Serialize
    serialized = message.serialize_bytes()
    print(f"\nSerialized: {len(serialized)} bytes")

    # Deserialize - array size read from header.item_count
    decoded, _ = ArrayMessage.deserialize_bytes(serialized)
    print(f"\nDecoded message:")
    print(f"  Header item_count: {decoded.header.item_count}")
    print(f"  Items: {decoded.items}")


def demo_sensor_packet():
    """Demonstrate complex sensor packet with automatic header computation."""
    print("\n" + "=" * 70)
    print("Example 3: Sensor Packet with Auto-Computed Header")
    print("=" * 70)

    # Create header and payload
    header = ProtocolHeader(version=2, flags=0b00000011, data_length=0, checksum=0)
    payload = SensorPayload(
        sensor_id="SENSOR-001",
        temperature=23.5,
        humidity=65.0,
        pressure=1013.25,
    )

    # Create packet - header fields computed automatically
    packet = SensorPacket(header=header, payload=payload)

    print(f"\nOriginal packet:")
    print(f"  Header version: {packet.header.version}")
    print(f"  Header flags: 0b{packet.header.flags:08b}")
    print(f"  Header data_length (auto): {packet.header.data_length}")
    print(f"  Header checksum (auto): {packet.header.checksum}")
    print(f"  Sensor ID: {packet.payload.sensor_id}")
    print(f"  Temperature: {packet.payload.temperature}°C")
    print(f"  Humidity: {packet.payload.humidity}%")
    print(f"  Pressure: {packet.payload.pressure} hPa")

    # Serialize
    serialized = packet.serialize_bytes()
    print(f"\nSerialized: {len(serialized)} bytes")

    # Deserialize
    decoded, _ = SensorPacket.deserialize_bytes(serialized)
    print(f"\nDecoded packet:")
    print(f"  Header data_length: {decoded.header.data_length}")
    print(f"  Header checksum: {decoded.header.checksum}")
    print(f"  Sensor ID: {decoded.payload.sensor_id}")
    print(f"  Temperature: {decoded.payload.temperature}°C")


def demo_conditional_fields():
    """Demonstrate conditional fields based on partial flags."""
    print("\n" + "=" * 70)
    print("Example 4: Conditional Fields Based on Partial Flags")
    print("=" * 70)

    # Create message with all optional fields
    flags1 = ControlFlags(
        has_timestamp=True, has_metadata=True, has_extended=True, reserved=0
    )
    msg1 = ConditionalMessage(
        flags=flags1,
        basic_data=12345,
        timestamp=1234567890,
        metadata="Important metadata",
        extended_data=b"Extended information",
    )

    print(f"\nMessage 1 (all fields included):")
    print(
        f"  Flags: timestamp={msg1.flags.has_timestamp}, "
        f"metadata={msg1.flags.has_metadata}, extended={msg1.flags.has_extended}"
    )
    print(f"  Basic data: {msg1.basic_data}")
    print(f"  Timestamp: {msg1.timestamp}")
    print(f"  Metadata: {msg1.metadata}")
    print(f"  Extended data: {msg1.extended_data}")

    serialized1 = msg1.serialize_bytes()
    print(f"  Serialized: {len(serialized1)} bytes")

    # Create message with only basic fields
    flags2 = ControlFlags(
        has_timestamp=False, has_metadata=False, has_extended=False, reserved=0
    )
    msg2 = ConditionalMessage(flags=flags2, basic_data=67890)

    print(f"\nMessage 2 (minimal fields):")
    print(
        f"  Flags: timestamp={msg2.flags.has_timestamp}, "
        f"metadata={msg2.flags.has_metadata}, extended={msg2.flags.has_extended}"
    )
    print(f"  Basic data: {msg2.basic_data}")
    print(f"  Has timestamp field: {hasattr(msg2, 'timestamp')}")
    print(f"  Has metadata field: {hasattr(msg2, 'metadata')}")
    print(f"  Has extended_data field: {hasattr(msg2, 'extended_data')}")

    serialized2 = msg2.serialize_bytes()
    print(f"  Serialized: {len(serialized2)} bytes (much smaller!)")

    # Deserialize both
    decoded1, _ = ConditionalMessage.deserialize_bytes(serialized1)
    decoded2, _ = ConditionalMessage.deserialize_bytes(serialized2)
    print(
        f"\nDecoded message 1 has {len([k for k in decoded1.__dict__ if not k.startswith('_')])} fields"
    )
    print(
        f"Decoded message 2 has {len([k for k in decoded2.__dict__ if not k.startswith('_')])} fields"
    )


def demo_nested_references():
    """Demonstrate deeply nested cross-partial references."""
    print("\n" + "=" * 70)
    print("Example 5: Nested Cross-Partial References")
    print("=" * 70)

    # Create deeply nested structure
    inner = InnerData(value=b"Deeply nested data content")
    middle = MiddleLayer(inner=inner)
    packet = NestedPacket(middle=middle, value_length=0)

    print(f"\nOriginal packet:")
    print(f"  Middle.inner.value: {packet.middle.inner.value}")
    print(f"  Value length (auto-computed): {packet.value_length}")

    # Serialize
    serialized = packet.serialize_bytes()
    print(f"\nSerialized: {len(serialized)} bytes")

    # Deserialize
    decoded, _ = NestedPacket.deserialize_bytes(serialized)
    print(f"\nDecoded packet:")
    print(f"  Value length: {decoded.value_length}")
    print(f"  Middle.inner.value: {decoded.middle.inner.value}")
    print(
        f"  Length matches: {decoded.value_length == len(decoded.middle.inner.value)}"
    )


def main():
    """Run all demonstrations."""
    print("\n" + "=" * 70)
    print("CROSS-PARTIAL FIELD REFERENCES DEMONSTRATION")
    print("=" * 70)
    print("\nCross-partial field references allow you to reference fields")
    print("inside MessagePartial objects using dot notation.")
    print("This is useful for protocol headers that need information about payloads.")
    print()

    demo_basic_cross_partial_reference()
    demo_array_size_from_header()
    demo_sensor_packet()
    demo_conditional_fields()
    demo_nested_references()

    print("\n" + "=" * 70)
    print("DEMONSTRATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
