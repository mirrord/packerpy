"""
Demonstration of mixed serialization types within a single message.

This example shows:
1. JSON serializer usage
2. Mixed serialization - binary header with JSON payload
3. Different serializers for different fields in the same message
"""

from packerpy.protocols.message import Message
from packerpy.protocols.message_partial import MessagePartial, Encoding
from packerpy.protocols.serializer import BytesSerializer, JSONSerializer


# Define a header structure (compact binary format)
class PacketHeader(MessagePartial):
    """Compact binary header with metadata."""

    encoding = Encoding.BIG_ENDIAN
    fields = {
        "version": {"type": "uint(8)"},
        "packet_id": {"type": "uint(32)"},
        "flags": {"type": "uint(8)"},
    }


# Define a payload structure (human-readable JSON format)
class DataPayload(MessagePartial):
    """Rich data payload with complex structures."""

    encoding = Encoding.BIG_ENDIAN
    fields = {
        "sensor_name": {"type": "str"},
        "temperature": {"type": "float"},
        "humidity": {"type": "float"},
        "pressure": {"type": "float"},
        "location": {"type": "str"},
    }


# Message with mixed serialization
class MixedMessage(Message):
    """
    Message with binary header and JSON payload.

    The header uses compact binary serialization for efficiency,
    while the payload uses JSON for readability and flexibility.
    """

    encoding = Encoding.BIG_ENDIAN
    fields = {
        "header": {"type": PacketHeader, "serializer": BytesSerializer()},
        "payload": {"type": DataPayload, "serializer": JSONSerializer()},
    }


# Example 1: Basic JSON serialization
def demo_json_serializer():
    """Demonstrate basic JSON serialization."""
    print("=" * 60)
    print("Example 1: Basic JSON Serialization")
    print("=" * 60)

    # Create a simple message
    class SensorData(MessagePartial):
        encoding = Encoding.BIG_ENDIAN
        fields = {
            "sensor_id": {"type": "str"},
            "value": {"type": "float"},
            "unit": {"type": "str"},
        }

    # Create instance
    sensor = SensorData(sensor_id="TEMP-001", value=23.5, unit="celsius")

    # Serialize to JSON
    json_serializer = JSONSerializer(indent=2)
    json_bytes = json_serializer.serialize(sensor)
    json_str = json_serializer.serialize_to_string(sensor, indent=2)

    print("\nOriginal object:")
    print(sensor)

    print("\nJSON representation:")
    print(json_str)

    print(f"\nJSON bytes (length: {len(json_bytes)}):")
    print(json_bytes)

    # Deserialize from JSON
    restored = json_serializer.deserialize(json_bytes, SensorData)
    print("\nDeserialized object:")
    print(restored)

    # Verify
    print("\nVerification:")
    print(f"  sensor_id match: {sensor.sensor_id == restored.sensor_id}")
    print(f"  value match: {sensor.value == restored.value}")
    print(f"  unit match: {sensor.unit == restored.unit}")


# Example 2: Mixed serialization in a message
def demo_mixed_serialization():
    """Demonstrate mixed binary/JSON serialization."""
    print("\n" + "=" * 60)
    print("Example 2: Mixed Binary/JSON Serialization")
    print("=" * 60)

    # Create header (will be binary)
    header = PacketHeader(version=1, packet_id=12345, flags=0b00000011)  # Example flags

    # Create payload (will be JSON)
    payload = DataPayload(
        sensor_name="WeatherStation-Alpha",
        temperature=22.5,
        humidity=65.3,
        pressure=1013.25,
        location="Building A, Floor 3",
    )

    # Create mixed message
    message = MixedMessage(header=header, payload=payload)

    print("\nOriginal message:")
    print(f"  Header: {header}")
    print(f"  Payload: {payload}")

    # Serialize the whole message
    # Header will be binary, payload will be JSON
    serialized = message.serialize_bytes()

    print(f"\nSerialized message (length: {len(serialized)} bytes):")
    print(f"  Raw bytes: {serialized}")

    # Show what the JSON payload looks like
    json_serializer = JSONSerializer(indent=2)
    payload_json = json_serializer.serialize_to_string(payload, indent=2)
    print(f"\nPayload as JSON (embedded in message):")
    print(payload_json)

    # Deserialize
    restored_message, bytes_consumed = MixedMessage.deserialize_bytes(serialized)

    print(f"\nDeserialized message (consumed {bytes_consumed} bytes):")
    print(f"  Header: {restored_message.header}")
    print(f"  Payload: {restored_message.payload}")

    # Verify
    print("\nVerification:")
    print(f"  version match: {header.version == restored_message.header.version}")
    print(f"  packet_id match: {header.packet_id == restored_message.header.packet_id}")
    print(f"  flags match: {header.flags == restored_message.header.flags}")
    print(
        f"  sensor_name match: {payload.sensor_name == restored_message.payload.sensor_name}"
    )
    print(
        f"  temperature match: {payload.temperature == restored_message.payload.temperature}"
    )
    print(f"  location match: {payload.location == restored_message.payload.location}")


# Example 3: Compare serialization sizes
def demo_size_comparison():
    """Compare binary vs JSON serialization sizes."""
    print("\n" + "=" * 60)
    print("Example 3: Serialization Size Comparison")
    print("=" * 60)

    # Create the same payload
    payload = DataPayload(
        sensor_name="WeatherStation-Alpha",
        temperature=22.5,
        humidity=65.3,
        pressure=1013.25,
        location="Building A, Floor 3",
    )

    # Serialize with binary
    binary_serializer = BytesSerializer()
    binary_data = binary_serializer.serialize(payload)

    # Serialize with JSON (compact)
    json_compact = JSONSerializer()
    json_compact_data = json_compact.serialize(payload)

    # Serialize with JSON (pretty)
    json_pretty = JSONSerializer(indent=2)
    json_pretty_data = json_pretty.serialize(payload)

    print("\nPayload content:")
    print(payload)

    print(f"\nBinary serialization: {len(binary_data)} bytes")
    print(f"JSON compact: {len(json_compact_data)} bytes")
    print(f"JSON pretty-printed: {len(json_pretty_data)} bytes")

    print(f"\nJSON overhead vs binary:")
    print(
        f"  Compact: {len(json_compact_data) - len(binary_data):+d} bytes ({(len(json_compact_data) / len(binary_data) - 1) * 100:.1f}%)"
    )
    print(
        f"  Pretty: {len(json_pretty_data) - len(binary_data):+d} bytes ({(len(json_pretty_data) / len(binary_data) - 1) * 100:.1f}%)"
    )

    print("\nJSON compact data:")
    print(json_compact_data.decode("utf-8"))

    print("\nJSON pretty data:")
    print(json_pretty_data.decode("utf-8"))


# Example 4: Selective serialization strategy
def demo_selective_serialization():
    """Demonstrate choosing serializers based on field characteristics."""
    print("\n" + "=" * 60)
    print("Example 4: Selective Serialization Strategy")
    print("=" * 60)

    class Header(MessagePartial):
        """Small, fixed-size header - use binary."""

        encoding = Encoding.BIG_ENDIAN
        fields = {
            "msg_type": {"type": "uint(8)"},
            "seq_num": {"type": "uint(32)"},
        }

    class Body(MessagePartial):
        """Variable-size, complex data - use JSON."""

        encoding = Encoding.BIG_ENDIAN
        fields = {
            "description": {"type": "str"},
            "tags": {"type": "str"},  # Could be JSON array as string
            "metadata": {"type": "str"},  # Could be JSON object as string
        }

    class Checksum(MessagePartial):
        """Small, fixed-size footer - use binary."""

        encoding = Encoding.BIG_ENDIAN
        fields = {
            "crc32": {"type": "uint(32)"},
        }

    class OptimizedMessage(Message):
        """
        Message optimized for both efficiency and flexibility.
        - Binary for fixed-size, frequently accessed fields
        - JSON for complex, variable-size data
        """

        encoding = Encoding.BIG_ENDIAN
        fields = {
            "header": {"type": Header, "serializer": BytesSerializer()},
            "body": {"type": Body, "serializer": JSONSerializer()},
            "footer": {"type": Checksum, "serializer": BytesSerializer()},
        }

    # Create message
    message = OptimizedMessage(
        header=Header(msg_type=42, seq_num=1001),
        body=Body(
            description="Complex sensor reading with multiple parameters",
            tags='["temperature", "humidity", "pressure"]',
            metadata='{"location": "warehouse", "device_id": "ABC123"}',
        ),
        footer=Checksum(crc32=0xDEADBEEF),
    )

    print("\nMessage structure:")
    print(f"  Header (binary): {message.header}")
    print(f"  Body (JSON): {message.body}")
    print(f"  Footer (binary): {message.footer}")

    # Serialize
    data = message.serialize_bytes()

    print(f"\nSerialized message: {len(data)} bytes")

    # Show the JSON body separately
    json_serializer = JSONSerializer(indent=2)
    body_json = json_serializer.serialize_to_string(message.body, indent=2)
    print("\nBody as JSON:")
    print(body_json)

    # Deserialize
    restored, consumed = OptimizedMessage.deserialize_bytes(data)

    print(f"\nRestored message:")
    print(f"  Header: {restored.header}")
    print(f"  Body: {restored.body}")
    print(f"  Footer: {restored.footer}")

    print("\nStrategy summary:")
    print("  ✓ Header: Binary (5 bytes) - efficient for fixed data")
    print("  ✓ Body: JSON (~170+ bytes) - flexible for complex data")
    print("  ✓ Footer: Binary (4 bytes) - efficient for fixed data")


if __name__ == "__main__":
    demo_json_serializer()
    demo_mixed_serialization()
    demo_size_comparison()
    demo_selective_serialization()

    print("\n" + "=" * 60)
    print("All demonstrations completed successfully!")
    print("=" * 60)
