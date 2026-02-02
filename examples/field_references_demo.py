"""Demonstration of field references for length prefixes and conditional fields."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from packerpy.protocols import Message, Protocol, protocol
from packerpy.protocols.message import Encoding


# Create a protocol instance
NetworkProtocol = Protocol()


@protocol(NetworkProtocol)
class LengthPrefixedMessage(Message):
    """
    Message with automatic length prefix.

    The 'data_length' field is automatically computed from the 'data' field.
    """

    encoding = Encoding.BIG_ENDIAN
    fields = {
        "data_length": {"type": "uint(16)", "length_of": "data"},
        "data": {"type": "bytes"},
    }


@protocol(NetworkProtocol)
class VariableSizeArray(Message):
    """
    Message with array size determined by another field.

    The 'items' array size is determined by the 'count' field.
    """

    encoding = Encoding.BIG_ENDIAN
    fields = {
        "count": {"type": "uint(8)"},
        "items": {"type": "int(32)", "numlist": "count"},
    }


@protocol(NetworkProtocol)
class ConditionalFieldMessage(Message):
    """
    Message with conditional fields based on flags.

    The 'extended_data' field is only included if 'has_extended' is True.
    """

    encoding = Encoding.BIG_ENDIAN
    fields = {
        "has_extended": {"type": "bool"},
        "basic_data": {"type": "int(32)"},
        "extended_data": {
            "type": "int(64)",
            "condition": lambda msg: hasattr(msg, "has_extended") and msg.has_extended,
        },
    }


@protocol(NetworkProtocol)
class PacketWithChecksum(Message):
    """
    Message with computed checksum field.

    The 'checksum' field is computed from the 'data' field.
    """

    encoding = Encoding.BIG_ENDIAN
    fields = {
        "data": {"type": "bytes"},
        "checksum": {
            "type": "uint(32)",
            "compute": lambda msg: sum(msg.data) & 0xFFFFFFFF,
        },
    }


@protocol(NetworkProtocol)
class ComplexProtocolMessage(Message):
    """
    Complex message demonstrating multiple field reference features.

    - header_size: Automatically computed from header bytes
    - payload_length: Automatically computed from payload data
    - has_metadata: Flag for conditional metadata field
    - metadata: Only included if has_metadata is True
    """

    encoding = Encoding.BIG_ENDIAN
    fields = {
        "message_id": {"type": "uint(16)"},
        "flags": {"type": "uint(8)"},
        "header_size": {"type": "uint(16)", "size_of": "message_id"},  # Will be 2
        "payload_length": {"type": "uint(32)", "length_of": "payload"},
        "payload": {"type": "bytes"},
        "has_metadata": {"type": "bool"},
        "metadata": {
            "type": "str",
            "condition": lambda msg: hasattr(msg, "has_metadata") and msg.has_metadata,
        },
    }


def demo_length_prefix():
    """Demonstrate automatic length prefix computation."""
    print("=== Length Prefix Demo ===\n")

    # Create message with data (data_length will be computed during serialization)
    msg = LengthPrefixedMessage(data=b"Hello, World!")

    # The data_length field is automatically computed during serialization
    print("Original message:")
    print(f"  data: {msg.data}")
    print("  data_length: (will be computed)")

    # Encode - length is auto-computed
    encoded = NetworkProtocol.encode(msg)
    print(f"\nEncoded: {encoded.hex()}")

    # After serialization, the field is computed
    print(f"  data_length (after serialization): {msg.data_length}")

    # Decode
    decoded = NetworkProtocol.decode(encoded)
    print("\nDecoded message:")
    print(f"  data: {decoded.data}")
    print(f"  data_length: {decoded.data_length}")


def demo_variable_array():
    """Demonstrate array size from field reference."""
    print("\n=== Variable Array Size Demo ===\n")

    # Create message with array
    items = [100, 200, 300, 400, 500]
    msg = VariableSizeArray(count=len(items), items=items)

    print("Original message:")
    print(f"  count: {msg.count}")
    print(f"  items: {msg.items}")

    # Encode
    encoded = NetworkProtocol.encode(msg)
    print(f"\nEncoded: {encoded.hex()}")
    print(f"  Size: {len(encoded)} bytes")

    # Decode - array size determined by count field
    decoded = NetworkProtocol.decode(encoded)
    print("\nDecoded message:")
    print(f"  count: {decoded.count}")
    print(f"  items: {decoded.items}")


def demo_conditional_fields():
    """Demonstrate conditional field inclusion."""
    print("\n=== Conditional Fields Demo ===\n")

    # Message without extended data
    msg1 = ConditionalFieldMessage(
        has_extended=False, basic_data=12345, extended_data=None  # Won't be serialized
    )

    print("Message 1 (no extended data):")
    print(f"  has_extended: {msg1.has_extended}")
    print(f"  basic_data: {msg1.basic_data}")

    encoded1 = NetworkProtocol.encode(msg1)
    print(f"  Encoded size: {len(encoded1)} bytes")

    # Message with extended data
    msg2 = ConditionalFieldMessage(
        has_extended=True, basic_data=12345, extended_data=9876543210
    )

    print("\nMessage 2 (with extended data):")
    print(f"  has_extended: {msg2.has_extended}")
    print(f"  basic_data: {msg2.basic_data}")
    print(f"  extended_data: {msg2.extended_data}")

    encoded2 = NetworkProtocol.encode(msg2)
    print(f"  Encoded size: {len(encoded2)} bytes")

    # Decode both
    decoded1 = NetworkProtocol.decode(encoded1)
    decoded2 = NetworkProtocol.decode(encoded2)

    print("\nDecoded message 1:")
    print(f"  has_extended: {decoded1.has_extended}")
    print(f"  basic_data: {decoded1.basic_data}")
    print(f"  has extended_data attr: {hasattr(decoded1, 'extended_data')}")

    print("\nDecoded message 2:")
    print(f"  has_extended: {decoded2.has_extended}")
    print(f"  basic_data: {decoded2.basic_data}")
    print(f"  extended_data: {decoded2.extended_data}")


def demo_computed_checksum():
    """Demonstrate computed field values."""
    print("\n=== Computed Checksum Demo ===\n")

    data = b"Test data for checksum"
    msg = PacketWithChecksum(data=data)  # checksum will be computed

    print("Original message:")
    print(f"  data: {msg.data}")
    print("  checksum: (will be computed)")

    # Encode - checksum is auto-computed
    encoded = NetworkProtocol.encode(msg)

    # After serialization, checksum is computed
    print(f"  checksum (auto-computed): {msg.checksum}")
    print(f"  checksum (hex): 0x{msg.checksum:08x}")

    # Decode
    decoded = NetworkProtocol.decode(encoded)
    print("\nDecoded message:")
    print(f"  data: {decoded.data}")
    print(f"  checksum: {decoded.checksum} (0x{decoded.checksum:08x})")

    # Verify checksum
    expected = sum(decoded.data) & 0xFFFFFFFF
    print("\nChecksum verification:")
    print(f"  Expected: {expected} (0x{expected:08x})")
    print(f"  Match: {decoded.checksum == expected}")


def demo_complex_protocol():
    """Demonstrate complex message with multiple features."""
    print("\n=== Complex Protocol Demo ===\n")

    # Create complex message
    msg = ComplexProtocolMessage(
        message_id=42,
        flags=0x80,
        payload=b"Important payload data",
        has_metadata=True,
        metadata="Version: 1.0, Source: Server",
    )

    print("Original message:")
    print(f"  message_id: {msg.message_id}")
    print(f"  flags: 0x{msg.flags:02x}")
    print(f"  payload: {msg.payload}")
    print(f"  has_metadata: {msg.has_metadata}")
    print(f"  metadata: {msg.metadata}")
    print("  header_size: (will be computed)")
    print("  payload_length: (will be computed)")

    # Encode - computed fields are calculated
    encoded = NetworkProtocol.encode(msg)

    # Show computed values
    print("\nComputed values:")
    print(f"  header_size: {msg.header_size}")
    print(f"  payload_length: {msg.payload_length}")

    print(f"\nEncoded size: {len(encoded)} bytes")

    # Decode
    decoded = NetworkProtocol.decode(encoded)
    print("\nDecoded message:")
    print(f"  message_id: {decoded.message_id}")
    print(f"  flags: 0x{decoded.flags:02x}")
    print(f"  header_size: {decoded.header_size}")
    print(f"  payload_length: {decoded.payload_length}")
    print(f"  payload: {decoded.payload}")
    print(f"  has_metadata: {decoded.has_metadata}")
    print(f"  metadata: {decoded.metadata}")


def main():
    """Run all demonstrations."""
    demo_length_prefix()
    demo_variable_array()
    demo_conditional_fields()
    demo_computed_checksum()
    demo_complex_protocol()

    print("\n=== Summary ===")
    print("\nField reference features demonstrated:")
    print("  ✓ length_of: Automatic length prefix computation")
    print("  ✓ size_of: Automatic byte size computation")
    print("  ✓ numlist with field reference: Variable array sizes")
    print("  ✓ condition: Conditional field inclusion")
    print("  ✓ compute: Custom computed field values")
    print("\nAll features work declaratively in the Message field definitions!")


if __name__ == "__main__":
    main()
