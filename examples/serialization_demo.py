"""Demonstration of BYTES serialization and MessagePartial composition."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from packerpy.protocols.message import Message, StringPartial, IntPartial
from packerpy.protocols.protocol import Protocol


def demo_serialization():
    """Demonstrate BYTES serialization."""
    print("\n=== BYTES Serialization ===")

    protocol = Protocol()

    # Create message with partials
    message = Message(
        message_type="sensor_data",
        payload={"sensor_id": "temp-001", "location": "warehouse"},
        message_id="reading-001",
    )
    message.add_partial(StringPartial(value="Temperature Sensor"))
    message.add_partial(IntPartial(value=25))

    # Serialize
    data = protocol.encode_message(message)
    print(f"Original message: {message}")
    print(f"Serialized to {len(data)} bytes: {str(data[:50])}...")

    # Deserialize
    decoded = protocol.decode_message(data)
    print(f"Decoded message: {decoded}")
    print(f"Payload: {decoded.payload}")


def demo_partial_validation():
    """Demonstrate MessagePartial validation."""
    print("\n=== MessagePartial Validation ===")

    message = Message(
        message_type="data",
        payload={"description": "Test data"},
    )

    # Valid partials
    try:
        message.add_partial(StringPartial(value="Valid string"))
        message.add_partial(IntPartial(value=42))
        print(f"Added {len(message.partials)} valid partials")
        print(f"Message validates: {message.validate()}")
    except ValueError as e:
        print(f"Validation error: {e}")

    # Invalid partial (simulated - IntPartial with value out of range)
    try:
        # This would fail validation if the value doesn't fit in byte_size
        huge_value = 2**100
        invalid_submsg = IntPartial(huge_value, byte_size=4, signed=True)
        print(f"Invalid partial validates: {invalid_submsg.validate()}")
    except Exception as e:
        print(f"Error creating invalid partial: {e}")


if __name__ == "__main__":
    print("BYTES Serialization Demonstration")
    print("=" * 50)

    demo_serialization()
    demo_partial_validation()

    print("\n" + "=" * 50)
    print("Demonstration complete!")
