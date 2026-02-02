"""Demonstration of Protocol message registry with decorator."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from packerpy.protocols import Message, Protocol, protocol
from packerpy.protocols.message import Encoding


# Create a protocol instance
BakerProtocol = Protocol()


# Register message types using the decorator
@protocol(BakerProtocol)
class InitDough(Message):
    """Message for initializing dough preparation."""

    encoding = Encoding.BIG_ENDIAN
    fields = {
        "flour_grams": {"type": "int(32)"},
        "water_ml": {"type": "int(32)"},
        "yeast_grams": {"type": "float"},
    }


@protocol(BakerProtocol)
class BakeCommand(Message):
    """Message for baking command."""

    encoding = Encoding.BIG_ENDIAN
    fields = {
        "temperature_c": {"type": "int(16)"},
        "duration_minutes": {"type": "int(16)"},
        "fan_enabled": {"type": "bool"},
    }


@protocol(BakerProtocol)
class StatusReport(Message):
    """Message for status reporting."""

    encoding = Encoding.BIG_ENDIAN
    fields = {
        "oven_temp": {"type": "int(16)"},
        "timer_remaining": {"type": "int(16)"},
        "message": {"type": "str"},
    }


def demo_protocol_registry():
    """Demonstrate protocol registration and automatic type discrimination."""
    print("=== Protocol Registry Demo ===\n")

    # Create different message types
    dough_msg = InitDough(flour_grams=500, water_ml=300, yeast_grams=7.5)
    bake_msg = BakeCommand(temperature_c=220, duration_minutes=25, fan_enabled=True)
    status_msg = StatusReport(
        oven_temp=218, timer_remaining=23, message="Baking in progress"
    )

    # Encode messages
    print("Encoding messages...")
    dough_data = BakerProtocol.encode(dough_msg)
    bake_data = BakerProtocol.encode(bake_msg)
    status_data = BakerProtocol.encode(status_msg)

    print(f"  InitDough: {len(dough_data)} bytes")
    print(f"  BakeCommand: {len(bake_data)} bytes")
    print(f"  StatusReport: {len(status_data)} bytes")

    # Decode messages - automatically get correct types
    print("\nDecoding messages (automatic type discrimination)...")

    decoded_dough = BakerProtocol.decode(dough_data)
    print(f"\n  Decoded type: {type(decoded_dough).__name__}")
    print(f"  flour_grams: {decoded_dough.flour_grams}")
    print(f"  water_ml: {decoded_dough.water_ml}")
    print(f"  yeast_grams: {decoded_dough.yeast_grams}")

    decoded_bake = BakerProtocol.decode(bake_data)
    print(f"\n  Decoded type: {type(decoded_bake).__name__}")
    print(f"  temperature_c: {decoded_bake.temperature_c}")
    print(f"  duration_minutes: {decoded_bake.duration_minutes}")
    print(f"  fan_enabled: {decoded_bake.fan_enabled}")

    decoded_status = BakerProtocol.decode(status_data)
    print(f"\n  Decoded type: {type(decoded_status).__name__}")
    print(f"  oven_temp: {decoded_status.oven_temp}")
    print(f"  timer_remaining: {decoded_status.timer_remaining}")
    print(f"  message: {decoded_status.message}")

    # Demonstrate that the types are preserved
    print("\n=== Type Verification ===")
    print(
        f"  isinstance(decoded_dough, InitDough): {isinstance(decoded_dough, InitDough)}"
    )
    print(
        f"  isinstance(decoded_bake, BakeCommand): {isinstance(decoded_bake, BakeCommand)}"
    )
    print(
        f"  isinstance(decoded_status, StatusReport): {isinstance(decoded_status, StatusReport)}"
    )


def demo_unregistered_message():
    """Demonstrate what happens with unregistered messages."""
    print("\n\n=== Unregistered Message Demo ===\n")

    # Create a message type that's NOT registered
    class UnregisteredMessage(Message):
        fields = {
            "value": {"type": "int(32)"},
        }

    msg = UnregisteredMessage(value=42)

    try:
        BakerProtocol.encode(msg)
        print("  ERROR: Should have raised ValueError")
    except ValueError as e:
        print(f"  Expected error: {e}")


if __name__ == "__main__":
    demo_protocol_registry()
    demo_unregistered_message()
