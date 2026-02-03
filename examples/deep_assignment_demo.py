"""
Demonstration of deep assignment in cross-partial field references.

This example shows how to use deep assignments to automatically set
nested fields within MessagePartial objects from the parent Message level.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from packerpy.protocols.message import Message, Encoding
from packerpy.protocols.message_partial import MessagePartial
from packerpy.protocols.serializer import BytesSerializer, JSONSerializer


print("=" * 70)
print("DEEP ASSIGNMENT IN CROSS-PARTIAL FIELD REFERENCES")
print("=" * 70)
print()
print("Deep assignments allow you to set nested fields within MessagePartials")
print("directly from the parent Message's field specification.")
print()


# Example 1: Basic Deep Assignment
# ================================

print("=" * 70)
print("Example 1: Basic Deep Assignment - User's Exact Syntax")
print("=" * 70)
print()


class HelloHeader(MessagePartial):
    encoding = Encoding.BIG_ENDIAN
    fields = {"id": {"type": "int(8)"}, "payload_length": {"type": "int(16)"}}


class HelloPayload(MessagePartial):
    encoding = Encoding.BIG_ENDIAN
    fields = {"greeting": {"type": "str"}, "target": {"type": "str"}}


class HelloMessage(Message):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "header": {
            "type": HelloHeader,
            "header.payload_length": {"length_of": "payload"},
            "serializer": BytesSerializer(),
        },
        "payload": {"type": HelloPayload, "serializer": JSONSerializer()},
    }


# Create the message
header = HelloHeader(id=1, payload_length=0)
payload = HelloPayload(greeting="Hello", target="World")
message = HelloMessage(header=header, payload=payload)

print("Original message:")
print(f"  Header ID: {message.header.id}")
print(
    f"  Header payload_length (before serialization): {message.header.payload_length}"
)
print(f"  Payload greeting: {message.payload.greeting}")
print(f"  Payload target: {message.payload.target}")
print()

# Serialize - this automatically computes header.payload_length
serialized = message.serialize_bytes()

print(f"After serialization:")
print(f"  Header payload_length (auto-computed): {message.header.payload_length}")
print(f"  Total serialized size: {len(serialized)} bytes")
print()

# Deserialize and verify
decoded, _ = HelloMessage.deserialize_bytes(serialized)
print("Decoded message:")
print(f"  Header ID: {decoded.header.id}")
print(f"  Header payload_length: {decoded.header.payload_length}")
print(f"  Payload greeting: {decoded.payload.greeting}")
print(f"  Payload target: {decoded.payload.target}")
print()


# Example 2: Multiple Deep Assignments
# ====================================

print("=" * 70)
print("Example 2: Multiple Deep Assignments")
print("=" * 70)
print()


class PacketHeader(MessagePartial):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "magic": {"type": "uint(16)"},
        "version": {"type": "uint(8)"},
        "payload_size": {"type": "uint(32)"},
        "checksum": {"type": "uint(32)"},
    }


class PacketPayload(MessagePartial):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "data": {"type": "bytes"},
    }


class SmartPacket(Message):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "header": {
            "type": PacketHeader,
            "header.payload_size": {"length_of": "payload"},
            "header.checksum": {
                "compute": lambda msg: sum(msg.payload.data) & 0xFFFFFFFF
            },
        },
        "payload": {"type": PacketPayload},
    }


# Create packet
header = PacketHeader(magic=0xABCD, version=1, payload_size=0, checksum=0)
payload = PacketPayload(data=b"Important protocol data")
packet = SmartPacket(header=header, payload=payload)

print("Original packet:")
print(f"  Magic: 0x{packet.header.magic:04X}")
print(f"  Version: {packet.header.version}")
print(f"  Payload size (before): {packet.header.payload_size}")
print(f"  Checksum (before): {packet.header.checksum}")
print()

# Serialize - both header fields are computed automatically
serialized = packet.serialize_bytes()

print("After serialization:")
print(f"  Payload size (auto): {packet.header.payload_size}")
print(f"  Checksum (auto): 0x{packet.header.checksum:08X}")
print(f"  Total size: {len(serialized)} bytes")
print()

# Deserialize and verify
decoded, _ = SmartPacket.deserialize_bytes(serialized)
print("Decoded packet:")
print(f"  Magic: 0x{decoded.header.magic:04X}")
print(f"  Payload size: {decoded.header.payload_size}")
print(f"  Checksum: 0x{decoded.header.checksum:08X}")
print(f"  Payload data: {decoded.payload.data}")
print()


# Example 3: Nested Deep Assignment
# =================================

print("=" * 70)
print("Example 3: Deeply Nested Deep Assignment")
print("=" * 70)
print()


class InnerConfig(MessagePartial):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "item_count": {"type": "uint(16)"},
    }


class OuterConfig(MessagePartial):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "inner": {"type": InnerConfig},
    }


class ConfiguredMessage(Message):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "config": {
            "type": OuterConfig,
            "config.inner.item_count": {"length_of": "items"},
        },
        "items": {"type": "int(32)", "numlist": 5},
    }


# Create message
inner = InnerConfig(item_count=0)
outer = OuterConfig(inner=inner)
msg = ConfiguredMessage(config=outer, items=[100, 200, 300, 400, 500])

print("Original message:")
print(f"  Config.inner.item_count (before): {msg.config.inner.item_count}")
print(f"  Items: {msg.items}")
print()

# Serialize
serialized = msg.serialize_bytes()

print("After serialization:")
print(f"  Config.inner.item_count (auto): {msg.config.inner.item_count}")
print(f"  Serialized size: {len(serialized)} bytes")
print()

# Deserialize and verify
decoded, _ = ConfiguredMessage.deserialize_bytes(serialized)
print("Decoded message:")
print(f"  Config.inner.item_count: {decoded.config.inner.item_count}")
print(f"  Items: {decoded.items}")
print()


# Example 4: Deep Assignment with Cross-Partial Reference
# =======================================================

print("=" * 70)
print("Example 4: Deep Assignment with Cross-Partial Reference")
print("=" * 70)
print()


class FrameHeader(MessagePartial):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "sequence": {"type": "uint(32)"},
        "data_length": {"type": "uint(32)"},
    }


class FramePayload(MessagePartial):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "data": {"type": "bytes"},
        "padding": {"type": "bytes"},
    }


class DataFrame(Message):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "header": {
            "type": FrameHeader,
            "header.data_length": {"length_of": "payload.data"},  # Cross-partial!
        },
        "payload": {"type": FramePayload},
    }


# Create frame
header = FrameHeader(sequence=1234, data_length=0)
payload = FramePayload(data=b"Frame data content", padding=b"\x00" * 10)
frame = DataFrame(header=header, payload=payload)

print("Original frame:")
print(f"  Sequence: {frame.header.sequence}")
print(f"  Data length (before): {frame.header.data_length}")
print(f"  Payload data: {frame.payload.data}")
print(f"  Payload padding: {len(frame.payload.padding)} bytes")
print()

# Serialize
serialized = frame.serialize_bytes()

print("After serialization:")
print(f"  Data length (auto): {frame.header.data_length}")
print(f"  (Only counts payload.data, not padding)")
print(f"  Serialized size: {len(serialized)} bytes")
print()

# Deserialize and verify
decoded, _ = DataFrame.deserialize_bytes(serialized)
print("Decoded frame:")
print(f"  Sequence: {decoded.header.sequence}")
print(f"  Data length: {decoded.header.data_length}")
print(f"  Payload data: {decoded.payload.data}")
print()


# Example 5: Real-World Protocol with Mixed Serialization
# =======================================================

print("=" * 70)
print("Example 5: Real-World Protocol (Binary + JSON)")
print("=" * 70)
print()


class ProtocolHeader(MessagePartial):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "protocol_version": {"type": "uint(8)"},
        "message_type": {"type": "uint(8)"},
        "flags": {"type": "uint(16)"},
        "payload_length": {"type": "uint(32)"},
        "crc32": {"type": "uint(32)"},
    }


class SensorData(MessagePartial):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "sensor_id": {"type": "str"},
        "temperature": {"type": "float"},
        "humidity": {"type": "float"},
        "pressure": {"type": "float"},
        "timestamp": {"type": "int"},
    }


class SensorMessage(Message):
    encoding = Encoding.BIG_ENDIAN
    fields = {
        "header": {
            "type": ProtocolHeader,
            "serializer": BytesSerializer(),
            "header.payload_length": {"length_of": "payload"},
            "header.crc32": {
                "compute": lambda msg: hash(str(msg.payload.__dict__)) & 0xFFFFFFFF
            },
        },
        "payload": {"type": SensorData, "serializer": JSONSerializer()},
    }


# Create sensor message
header = ProtocolHeader(
    protocol_version=2,
    message_type=1,
    flags=0b0000001100000000,
    payload_length=0,
    crc32=0,
)

payload = SensorData(
    sensor_id="TEMP-SENSOR-001",
    temperature=23.5,
    humidity=65.0,
    pressure=1013.25,
    timestamp=1234567890,
)

sensor_msg = SensorMessage(header=header, payload=payload)

print("Original sensor message:")
print(f"  Protocol version: {sensor_msg.header.protocol_version}")
print(f"  Message type: {sensor_msg.header.message_type}")
print(f"  Flags: 0b{sensor_msg.header.flags:016b}")
print(f"  Payload length (before): {sensor_msg.header.payload_length}")
print(f"  CRC32 (before): {sensor_msg.header.crc32}")
print(f"  Sensor ID: {sensor_msg.payload.sensor_id}")
print(f"  Temperature: {sensor_msg.payload.temperature}°C")
print()

# Serialize
serialized = sensor_msg.serialize_bytes()

print("After serialization:")
print(f"  Payload length (auto): {sensor_msg.header.payload_length} bytes (JSON size)")
print(f"  CRC32 (auto): 0x{sensor_msg.header.crc32:08X}")
print(f"  Total message size: {len(serialized)} bytes")
print(f"    - Binary header: ~{len(header.serialize_bytes())} bytes")
print(f"    - JSON payload: {sensor_msg.header.payload_length} bytes")
print()

# Deserialize and verify
decoded, _ = SensorMessage.deserialize_bytes(serialized)
print("Decoded sensor message:")
print(f"  Payload length: {decoded.header.payload_length}")
print(f"  CRC32: 0x{decoded.header.crc32:08X}")
print(f"  Sensor ID: {decoded.payload.sensor_id}")
print(f"  Temperature: {decoded.payload.temperature}°C")
print(f"  Humidity: {decoded.payload.humidity}%")
print(f"  Pressure: {decoded.payload.pressure} hPa")
print()


print("=" * 70)
print("DEMONSTRATION COMPLETE")
print("=" * 70)
print()
print("Key Features Demonstrated:")
print("  ✓ Basic deep assignment syntax: 'header.field_name': {...}")
print("  ✓ Multiple deep assignments in one field spec")
print("  ✓ Deeply nested assignments: 'outer.inner.field': {...}")
print("  ✓ Cross-partial references in deep assignments")
print("  ✓ Mixed serialization with deep assignments")
print("  ✓ Real-world protocol packet examples")
print()
