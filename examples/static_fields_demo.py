"""
Demo: Static Fields in Protocol Messages

This demo showcases how to use static field values in protocol messages.
Static fields are automatically set to their declared values and cannot be changed,
making them perfect for message headers, protocol version identifiers, and magic numbers.
"""

from packerpy.protocols.protocol import Protocol, protocol
from packerpy.protocols.message import Message


def demo_basic_static_field():
    """Basic example of a static field for a protocol header."""
    print("=== Basic Static Field Demo ===\n")

    proto = Protocol()

    @protocol(proto)
    class PacketMessage(Message):
        fields = {
            "magic": {"type": "uint(16)", "static": 0xCAFE},  # Magic number
            "version": {"type": "uint(8)", "static": 1},  # Protocol version
            "payload": {"type": "int(32)"},
        }

    # Create message - static fields are automatically set
    msg = PacketMessage(payload=42)
    print(f"Created message:")
    print(f"  magic: 0x{msg.magic:04X} (static)")
    print(f"  version: {msg.version} (static)")
    print(f"  payload: {msg.payload}")

    # Encode and decode
    encoded = proto.encode(msg)
    print(f"\nEncoded to {len(encoded)} bytes")

    decoded, _ = proto.decode(encoded)
    print(f"\nDecoded message:")
    print(f"  magic: 0x{decoded.magic:04X}")
    print(f"  version: {decoded.version}")
    print(f"  payload: {decoded.payload}")


def demo_message_type_discrimination():
    """Using static fields to discriminate between message types."""
    print("\n=== Message Type Discrimination Demo ===\n")

    proto = Protocol()

    @protocol(proto)
    class RequestMessage(Message):
        fields = {
            "msg_type": {"type": "uint(8)", "static": 0x01},
            "request_id": {"type": "uint(32)"},
            "data_len": {"type": "uint(16)"},
        }

    @protocol(proto)
    class ResponseMessage(Message):
        fields = {
            "msg_type": {"type": "uint(8)", "static": 0x02},
            "request_id": {"type": "uint(32)"},
            "status": {"type": "uint(8)"},
        }

    # Create and encode both types
    req = RequestMessage(request_id=100, data_len=512)
    resp = ResponseMessage(request_id=100, status=200)

    req_encoded = proto.encode(req)
    resp_encoded = proto.encode(resp)

    print(f"Request message type: {req.msg_type} (0x{req.msg_type:02X})")
    print(f"Response message type: {resp.msg_type} (0x{resp.msg_type:02X})")

    # Decode both
    req_decoded, _ = proto.decode(req_encoded)
    resp_decoded, _ = proto.decode(resp_encoded)

    print(
        f"\nDecoded request: type={req_decoded.msg_type}, id={req_decoded.request_id}"
    )
    print(
        f"Decoded response: type={resp_decoded.msg_type}, id={resp_decoded.request_id}, status={resp_decoded.status}"
    )


def demo_bitwise_static_fields():
    """Static fields work in bitwise-packed messages too."""
    print("\n=== Bitwise Static Fields Demo ===\n")

    proto = Protocol()

    @protocol(proto)
    class ControlMessage(Message):
        fields = {
            "sync": {"type": "uint(8)", "static": 0b10101010},  # Sync pattern
            "version": {"type": "uint(8)", "static": 2},  # Version 2
            "flags": {"type": "uint(8)"},
            "data": {"type": "uint(16)"},
        }

    msg = ControlMessage(flags=0xFF, data=0x1234)

    print(f"Message fields:")
    print(f"  sync: 0b{msg.sync:08b} (static)")
    print(f"  version: {msg.version} (static)")
    print(f"  flags: 0x{msg.flags:02X}")
    print(f"  data: 0x{msg.data:04X}")

    encoded = proto.encode(msg)
    decoded, _ = proto.decode(encoded)

    print(f"\nAfter encode/decode:")
    print(f"  sync: 0b{decoded.sync:08b}")
    print(f"  version: {decoded.version}")
    print(f"  flags: 0x{decoded.flags:02X}")
    print(f"  data: 0x{decoded.data:04X}")


def demo_immutability():
    """Static fields are set during initialization and shouldn't be changed."""
    print("\n=== Static Field Immutability Demo ===\n")

    proto = Protocol()

    @protocol(proto)
    class ImmutableMessage(Message):
        fields = {
            "protocol_id": {"type": "uint(32)", "static": 0xDEADBEEF},
            "sequence": {"type": "uint(32)"},
        }

    msg = ImmutableMessage(sequence=1)
    print(f"Original: protocol_id=0x{msg.protocol_id:08X}, sequence={msg.sequence}")

    # Static fields are automatically set regardless of kwargs
    msg2 = ImmutableMessage(protocol_id=0x12345678, sequence=2)
    print(
        f"Attempt to override: protocol_id=0x{msg2.protocol_id:08X}, sequence={msg2.sequence}"
    )
    print(f"  -> protocol_id remained 0xDEADBEEF (static value)")

    # You can manually change instance attributes (not recommended)
    msg.protocol_id = 0x99999999
    print(f"\nManually changed instance: protocol_id=0x{msg.protocol_id:08X}")

    # But serialization always uses the static value
    encoded = proto.encode(msg)
    decoded, _ = proto.decode(encoded)
    print(f"After encode/decode: protocol_id=0x{decoded.protocol_id:08X}")
    print(f"  -> Serialization used static value, not instance attribute")


def main():
    """Run all static field demos."""
    demo_basic_static_field()
    demo_message_type_discrimination()
    demo_bitwise_static_fields()
    demo_immutability()


if __name__ == "__main__":
    main()
