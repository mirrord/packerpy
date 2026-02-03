"""
Demonstration of automatic headers and footers in Protocol.

This example showcases:
1. Counting fields present in a message
2. Getting the number of items in a list field
3. Calculating CRC checksums for message validation
4. Using deep field references in headers/footers
5. Combining multiple automatic fields
"""

from packerpy.protocols.protocol import Protocol, protocol
from packerpy.protocols.message import Message
from packerpy.protocols.message_partial import MessagePartial, Encoding


# Define message partials for nested structures
class SensorData(MessagePartial):
    """Sensor reading data."""

    encoding = Encoding.BIG_ENDIAN
    fields = {
        "sensor_id": {"type": "uint(16)"},
        "temperature": {"type": "float"},
        "humidity": {"type": "float"},
    }


class Header(MessagePartial):
    """Message header with metadata."""

    encoding = Encoding.BIG_ENDIAN
    fields = {
        "version": {"type": "uint(8)"},
        "flags": {"type": "uint(8)"},
    }


# Create protocol
SensorProtocol = Protocol()


@protocol(SensorProtocol)
class SensorReadings(Message):
    """Message containing multiple sensor readings."""

    encoding = Encoding.BIG_ENDIAN
    fields = {
        "header": {"type": Header},
        "device_name": {"type": "str"},
        "readings": {"type": SensorData, "numlist": 3},
        "notes": {"type": "str"},
    }


@protocol(SensorProtocol)
class SimpleData(Message):
    """Simple message for basic demos."""

    encoding = Encoding.BIG_ENDIAN
    fields = {
        "values": {"type": "int(32)", "numlist": 5},
        "description": {"type": "str"},
    }


def demo_field_counting():
    """Demonstrate counting fields in a message."""
    print("=" * 70)
    print("DEMO 1: Field Counting")
    print("=" * 70)

    # Configure protocol with header that counts fields
    SensorProtocol.set_headers(
        {
            "field_count": {
                "type": "uint(8)",
                "compute": lambda msg: Protocol.count_fields(msg.message),
            }
        }
    )

    # Create and encode a message
    msg = SimpleData(values=[10, 20, 30, 40, 50], description="Test values")

    print(f"\nOriginal message:")
    print(f"  values: {msg.values}")
    print(f"  description: {msg.description}")
    print(f"  Total fields set: {Protocol.count_fields(msg)}")

    # Encode
    encoded = SensorProtocol.encode(msg)
    print(f"\nEncoded message: {len(encoded)} bytes")

    # Decode
    decoded, _ = SensorProtocol.decode(encoded)
    print(f"\nDecoded successfully!")
    print(f"  values: {decoded.values}")
    print(f"  description: {decoded.description}")

    # Clear headers for next demo
    SensorProtocol.clear_headers()


def demo_list_length():
    """Demonstrate getting the length of list fields."""
    print("\n" + "=" * 70)
    print("DEMO 2: List Length in Headers")
    print("=" * 70)

    # Configure protocol with header that reports list length
    SensorProtocol.set_headers(
        {
            "num_values": {
                "type": "uint(16)",
                "compute": lambda msg: Protocol.list_length(msg.message, "values"),
            }
        }
    )

    # Create and encode a message
    msg = SimpleData(values=[100, 200, 300, 400, 500], description="Five values")

    print(f"\nOriginal message:")
    print(f"  values: {msg.values} (length: {len(msg.values)})")
    print(f"  description: {msg.description}")

    # Encode
    encoded = SensorProtocol.encode(msg)
    print(f"\nEncoded message: {len(encoded)} bytes")

    # Decode
    decoded, _ = SensorProtocol.decode(encoded)
    print(f"\nDecoded successfully!")
    print(f"  values: {decoded.values}")
    print(f"  List length was validated during decoding")

    # Clear headers for next demo
    SensorProtocol.clear_headers()


def demo_crc_checksum():
    """Demonstrate CRC checksum calculation."""
    print("\n" + "=" * 70)
    print("DEMO 3: CRC Checksum Validation")
    print("=" * 70)

    # Configure protocol with CRC footer
    SensorProtocol.set_footers(
        {
            "crc32_checksum": {
                "type": "uint(32)",
                "compute": lambda msg: Protocol.crc32(msg.serialize_bytes()),
            }
        }
    )

    # Create and encode a message
    msg = SimpleData(values=[1, 2, 3, 4, 5], description="Data with CRC")

    print(f"\nOriginal message:")
    print(f"  values: {msg.values}")
    print(f"  description: {msg.description}")

    # Encode
    encoded = SensorProtocol.encode(msg)
    msg_bytes = msg.serialize_bytes()
    crc = Protocol.crc32(msg_bytes)
    print(f"\nEncoded message: {len(encoded)} bytes")
    print(f"  Message body: {len(msg_bytes)} bytes")
    print(f"  CRC32: 0x{crc:08X}")

    # Decode - CRC will be automatically validated
    decoded, _ = SensorProtocol.decode(encoded)
    print(f"\nDecoded successfully! CRC validated.")
    print(f"  values: {decoded.values}")

    # Test tampering detection
    print("\n--- Testing Tamper Detection ---")
    tampered = bytearray(encoded)
    # Find the message body (skip type header)
    # Type header is 2 bytes for length + message type name length
    # Let's corrupt a byte in the first integer value
    # Type header: 2 + len("SimpleData") = 12 bytes
    # Then the message body starts
    # First field in message is the numlist of 5 int(32) values = 20 bytes
    # Let's corrupt the first integer value
    corruption_offset = 12 + 4  # Skip type header, corrupt the second int
    original_byte = tampered[corruption_offset]
    tampered[corruption_offset] ^= 0xFF  # Flip all bits

    print(
        f"  Corrupting byte at offset {corruption_offset}: 0x{original_byte:02X} -> 0x{tampered[corruption_offset]:02X}"
    )

    try:
        result = SensorProtocol.decode(bytes(tampered))
        if result:
            decoded_tampered, _ = result
            from packerpy.protocols.protocol import InvalidMessage

            if isinstance(decoded_tampered, InvalidMessage):
                print(f"[OK] Tampering detected: Message marked as invalid")
                print(f"  Error: {decoded_tampered.error}")
            else:
                print(f"ERROR: Tampered message was not detected!")
                print(f"  Decoded values: {decoded_tampered.values}")
    except Exception as e:
        print(f"[OK] Tampering detected: {type(e).__name__}: {str(e)[:60]}")

    # Clear footers for next demo
    SensorProtocol.clear_footers()


def demo_message_size():
    """Demonstrate message size calculation."""
    print("\n" + "=" * 70)
    print("DEMO 4: Message Size in Header")
    print("=" * 70)

    # Configure protocol with header reporting message size
    SensorProtocol.set_headers(
        {
            "message_size": {
                "type": "uint(32)",
                "size_of": "body",  # Special keyword for entire message
            }
        }
    )

    # Create and encode a message
    msg = SimpleData(
        values=[10, 20, 30, 40, 50], description="Message with size header"
    )

    print(f"\nOriginal message:")
    print(f"  values: {msg.values}")
    print(f"  description: {msg.description}")

    # Encode
    encoded = SensorProtocol.encode(msg)
    msg_bytes = msg.serialize_bytes()
    print(f"\nEncoded message: {len(encoded)} bytes")
    print(f"  Header (message_size): 4 bytes")
    print(f"  Message body: {len(msg_bytes)} bytes")

    # Decode
    decoded, _ = SensorProtocol.decode(encoded)
    print(f"\nDecoded successfully!")
    print(f"  Message size was validated during decoding")

    # Clear headers for next demo
    SensorProtocol.clear_headers()


def demo_deep_field_references():
    """Demonstrate deep field references in headers."""
    print("\n" + "=" * 70)
    print("DEMO 5: Deep Field References")
    print("=" * 70)

    # Configure protocol with headers that reference nested fields
    SensorProtocol.set_headers(
        {
            "header_version": {
                "type": "uint(8)",
                "value_from": "header.version",  # Reference nested field
            },
            "num_readings": {
                "type": "uint(8)",
                "compute": lambda msg: Protocol.list_length(msg.message, "readings"),
            },
        }
    )

    # Create nested message
    header = Header(version=2, flags=0x80)
    readings = [
        SensorData(sensor_id=1, temperature=22.5, humidity=45.0),
        SensorData(sensor_id=2, temperature=23.1, humidity=48.5),
        SensorData(sensor_id=3, temperature=21.8, humidity=44.2),
    ]

    msg = SensorReadings(
        header=header,
        device_name="Climate Station Alpha",
        readings=readings,
        notes="All sensors operational",
    )

    print(f"\nOriginal message:")
    print(f"  header.version: {msg.header.version}")
    print(f"  header.flags: 0x{msg.header.flags:02X}")
    print(f"  device_name: {msg.device_name}")
    print(f"  readings: {len(msg.readings)} sensor readings")
    print(f"  notes: {msg.notes}")

    # Encode
    encoded = SensorProtocol.encode(msg)
    print(f"\nEncoded message: {len(encoded)} bytes")

    # Decode
    decoded, _ = SensorProtocol.decode(encoded)
    print(f"\nDecoded successfully!")
    print(f"  Header version validated from nested field")
    print(f"  Number of readings validated: {len(decoded.readings)}")

    # Clear headers for next demo
    SensorProtocol.clear_headers()


def demo_combined_headers_and_footers():
    """Demonstrate using both headers and footers together."""
    print("\n" + "=" * 70)
    print("DEMO 6: Combined Headers and Footers")
    print("=" * 70)

    # Configure comprehensive protocol protection
    SensorProtocol.set_headers(
        {
            "protocol_version": {"type": "uint(8)", "static": 1},  # Protocol version
            "field_count": {
                "type": "uint(8)",
                "compute": lambda msg: Protocol.count_fields(msg.message),
            },
            "message_size": {"type": "uint(32)", "size_of": "body"},
        }
    )

    SensorProtocol.set_footers(
        {
            "crc32": {
                "type": "uint(32)",
                "compute": lambda msg: Protocol.crc32(msg.serialize_bytes()),
            },
            "end_marker": {
                "type": "uint(16)",
                "static": 0xFFFF,  # End-of-message marker
            },
        }
    )

    # Create and encode a message
    msg = SimpleData(
        values=[111, 222, 333, 444, 555], description="Fully protected message"
    )

    print(f"\nOriginal message:")
    print(f"  values: {msg.values}")
    print(f"  description: {msg.description}")

    # Encode
    encoded = SensorProtocol.encode(msg)
    print(f"\nEncoded message structure:")
    print(f"  Total size: {len(encoded)} bytes")
    print(f"  - Type header: variable")
    print(f"  - Protocol headers: 6 bytes (version + count + size)")
    print(f"  - Message body: {len(msg.serialize_bytes())} bytes")
    print(f"  - Protocol footers: 6 bytes (crc32 + end_marker)")

    # Decode
    decoded, _ = SensorProtocol.decode(encoded)
    print(f"\nDecoded successfully!")
    print(f"  [OK] Protocol version validated")
    print(f"  [OK] Field count validated")
    print(f"  [OK] Message size validated")
    print(f"  [OK] CRC32 checksum validated")
    print(f"  [OK] End marker validated")
    print(f"\n  values: {decoded.values}")

    # Clean up
    SensorProtocol.clear_headers()
    SensorProtocol.clear_footers()


def demo_partial_crc():
    """Demonstrate CRC over a subset of the message."""
    print("\n" + "=" * 70)
    print("DEMO 7: Partial CRC (Critical Fields Only)")
    print("=" * 70)

    # Configure footer with CRC over just the values field
    def compute_values_crc(msg):
        """Compute CRC only over the values field."""
        # Serialize just the values
        values_bytes = b""
        for val in msg.message.values:
            values_bytes += val.to_bytes(4, "big", signed=True)
        return Protocol.crc32(values_bytes)

    SensorProtocol.set_footers(
        {"values_crc": {"type": "uint(32)", "compute": compute_values_crc}}
    )

    # Create and encode a message
    msg = SimpleData(
        values=[10, 20, 30, 40, 50], description="CRC protects only values field"
    )

    print(f"\nOriginal message:")
    print(f"  values: {msg.values}")
    print(f"  description: {msg.description}")

    # Calculate CRC manually for display
    values_bytes = b""
    for val in msg.values:
        values_bytes += val.to_bytes(4, "big", signed=True)
    values_crc = Protocol.crc32(values_bytes)

    print(f"\nCRC calculation:")
    print(f"  Protected data: values field only")
    print(f"  Values CRC32: 0x{values_crc:08X}")

    # Encode
    encoded = SensorProtocol.encode(msg)
    print(f"\nEncoded message: {len(encoded)} bytes")

    # Decode
    decoded, _ = SensorProtocol.decode(encoded)
    print(f"\nDecoded successfully!")
    print(f"  [OK] Values CRC validated")
    print(f"  Note: Description field is not protected by CRC")

    # Clean up
    SensorProtocol.clear_footers()


def main():
    """Run all demonstrations."""
    print("\n" + "=" * 70)
    print(" AUTOMATIC HEADERS AND FOOTERS DEMONSTRATION")
    print("=" * 70)
    print("\nThis demo showcases the automatic headers and footers feature")
    print("which allows adding computed fields before and after messages.")

    try:
        demo_field_counting()
        demo_list_length()
        demo_crc_checksum()
        demo_message_size()
        demo_deep_field_references()
        demo_combined_headers_and_footers()
        demo_partial_crc()

        print("\n" + "=" * 70)
        print(" ALL DEMONSTRATIONS COMPLETED SUCCESSFULLY")
        print("=" * 70)

    except Exception as e:
        print(f"\n!!! Error during demonstration: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
