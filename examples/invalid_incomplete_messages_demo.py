"""
Demo of invalid and incomplete message handling.

This example shows how the Protocol handles:
1. Incomplete messages (buffered until complete)
2. Invalid messages (wrapped in InvalidMessage)
3. Multiple messages in a single buffer
"""

from packerpy.protocols import Protocol, Message, InvalidMessage, protocol
from packerpy.protocols.message_partial import Encoding


# Create a protocol instance
DemoProtocol = Protocol()


@protocol(DemoProtocol)
class StatusMessage(Message):
    """Status message with code and description."""

    encoding = Encoding.BIG_ENDIAN
    fields = {
        "status_code": {"type": "int(16)"},
        "description": {"type": "str"},
    }


def demo_incomplete_messages():
    """Demonstrate incomplete message buffering."""
    print("=" * 60)
    print("DEMO 1: Incomplete Message Handling")
    print("=" * 60)

    # Create a message
    msg = StatusMessage(status_code=200, description="OK")
    complete_data = DemoProtocol.encode(msg)
    print(f"\nComplete message size: {len(complete_data)} bytes")

    # Simulate receiving data in chunks (like network packets)
    chunk_size = 5
    chunks = [
        complete_data[i : i + chunk_size]
        for i in range(0, len(complete_data), chunk_size)
    ]

    print(f"Split into {len(chunks)} chunks of ~{chunk_size} bytes each")

    source_id = "client_123"

    # Process each chunk
    for i, chunk in enumerate(chunks):
        print(f"\nReceiving chunk {i+1}/{len(chunks)}: {len(chunk)} bytes")
        result = DemoProtocol.decode(chunk, source_id=source_id)

        if result is None:
            buffer_size = DemoProtocol.get_incomplete_buffer_size(source_id)
            print(f"  -> Incomplete message buffered ({buffer_size} bytes)")
        else:
            decoded_msg, remaining = result
            print(f"  -> Message decoded successfully!")
            print(f"     Status: {decoded_msg.status_code}")
            print(f"     Description: {decoded_msg.description}")
            print(f"     Remaining bytes: {len(remaining)}")


def demo_invalid_messages():
    """Demonstrate invalid message handling."""
    print("\n" + "=" * 60)
    print("DEMO 2: Invalid Message Handling")
    print("=" * 60)

    # Test 1: Unknown message type
    print("\nTest 1: Unknown message type")
    invalid_type_data = b"\x00\x0bUnknownType" + b"garbage_data"

    result = DemoProtocol.decode(invalid_type_data, source_id="test1")
    if result:
        msg, _ = result
        if isinstance(msg, InvalidMessage):
            print("  -> Invalid message detected")
            print(f"     Error: {msg.error}")
            print(f"     Partial type: {msg.partial_type}")
            print(f"     Raw data size: {len(msg.raw_data)} bytes")

    # Test 2: Corrupted data
    print("\nTest 2: Corrupted message data")
    # Create valid header but corrupted body
    valid_msg = StatusMessage(status_code=404, description="Not Found")
    valid_data = DemoProtocol.encode(valid_msg)

    # Corrupt the body
    corrupted_data = valid_data[:10] + b"CORRUPTED" + valid_data[10 + 9 :]

    result = DemoProtocol.decode(corrupted_data, source_id="test2")
    if result:
        msg, _ = result
        if isinstance(msg, InvalidMessage):
            print("  -> Invalid message detected")
            print(f"     Error: {msg.error}")
            print(f"     Message type extracted: {msg.partial_type}")


def demo_multiple_messages():
    """Demonstrate handling multiple messages in a buffer."""
    print("\n" + "=" * 60)
    print("DEMO 3: Multiple Messages in Buffer")
    print("=" * 60)

    # Create multiple messages
    messages = [
        StatusMessage(status_code=200, description="OK"),
        StatusMessage(status_code=201, description="Created"),
        StatusMessage(status_code=202, description="Accepted"),
    ]

    # Encode all messages and concatenate
    combined_data = b"".join(DemoProtocol.encode(msg) for msg in messages)
    print(f"\nCombined {len(messages)} messages: {len(combined_data)} bytes")

    # Decode all messages from the buffer
    remaining = combined_data
    source_id = "batch_client"
    decoded_count = 0

    while remaining:
        result = DemoProtocol.decode(remaining, source_id=source_id)
        if result is None:
            print(f"Incomplete message buffered ({len(remaining)} bytes remaining)")
            break

        msg, remaining = result
        if isinstance(msg, InvalidMessage):
            print(f"Invalid message encountered: {msg.error}")
            break

        decoded_count += 1
        print(
            f"  Message {decoded_count}: status={msg.status_code}, desc='{msg.description}'"
        )

    print(f"\nDecoded {decoded_count}/{len(messages)} messages successfully")


def demo_buffer_management():
    """Demonstrate incomplete buffer management."""
    print("\n" + "=" * 60)
    print("DEMO 4: Buffer Management")
    print("=" * 60)

    # Create incomplete data for multiple sources
    incomplete_data = b"\x00\x05"  # Just a partial type header

    sources = ["client_a", "client_b", "client_c"]

    print(f"\nBuffering incomplete data from {len(sources)} sources...")
    for source in sources:
        DemoProtocol.decode(incomplete_data, source_id=source)
        size = DemoProtocol.get_incomplete_buffer_size(source)
        print(f"  {source}: {size} bytes buffered")

    # Clear specific buffer
    print("\nClearing buffer for client_a...")
    cleared = DemoProtocol.clear_incomplete_buffer("client_a")
    print(f"  Cleared: {cleared}")
    print(f"  Remaining: {DemoProtocol.get_incomplete_buffer_size('client_a')} bytes")

    # Clear all buffers
    print("\nClearing all buffers...")
    count = DemoProtocol.clear_all_incomplete_buffers()
    print(f"  Cleared {count} buffers")

    # Verify all cleared
    for source in sources:
        size = DemoProtocol.get_incomplete_buffer_size(source)
        print(f"  {source}: {size} bytes")


def main():
    """Run all demos."""
    print("\n")
    print("#" * 60)
    print("# Invalid and Incomplete Message Handling Demo")
    print("#" * 60)

    demo_incomplete_messages()
    demo_invalid_messages()
    demo_multiple_messages()
    demo_buffer_management()

    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)
    print(
        """
Key takeaways:
1. Incomplete messages are automatically buffered per source
2. Invalid messages are wrapped in InvalidMessage objects
3. Buffers are automatically cleared after successful decode
4. Manual buffer management is available when needed
5. Multiple messages can be decoded from a single buffer
"""
    )


if __name__ == "__main__":
    main()
