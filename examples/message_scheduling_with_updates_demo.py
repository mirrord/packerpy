"""Demo of Protocol message scheduling with update callbacks."""

import time
from packerpy.protocols.message import Message
from packerpy.protocols.message_partial import Encoding
from packerpy.protocols.protocol import Protocol, protocol


# Create a protocol instance
MyProtocol = Protocol()


# Define a heartbeat message with timestamp and sequence
@protocol(MyProtocol)
class HeartbeatMessage(Message):
    """Periodic heartbeat message with dynamic fields."""

    encoding = Encoding.BIG_ENDIAN
    fields = {
        "timestamp": {"type": "int(64)"},
        "sequence": {"type": "int(32)"},
        "status": {"type": "str"},
    }


# Define a counter message
@protocol(MyProtocol)
class CounterMessage(Message):
    """Message with an incrementing counter."""

    encoding = Encoding.BIG_ENDIAN
    fields = {"counter": {"type": "int(32)"}, "value": {"type": "int(32)"}}


def main():
    """Demonstrate message scheduling with update callbacks."""

    print("Message Scheduling with Update Callbacks Demo")
    print("=" * 60)

    # Example 1: Heartbeat with timestamp updates
    print("\n1. Heartbeat with timestamp updates")
    print("-" * 60)

    heartbeat = HeartbeatMessage(timestamp=0, sequence=0, status="alive")

    # Callback to print sent messages
    def print_heartbeat(data: bytes):
        decoded = MyProtocol.decode(data)
        print(
            f"  [Heartbeat] seq={decoded.sequence}, "
            f"timestamp={decoded.timestamp}, status={decoded.status}"
        )

    # Update callback to refresh timestamp and increment sequence
    def update_heartbeat(msg):
        msg.timestamp = int(time.time() * 1000)  # milliseconds
        msg.sequence += 1

    heartbeat_id = MyProtocol.schedule_message(
        msg=heartbeat,
        interval=1.0,
        send_callback=print_heartbeat,
        update_callback=update_heartbeat,
    )

    print(f"  Scheduled heartbeat (ID: {heartbeat_id})")
    print("  Heartbeats will be sent for 3 seconds...")
    time.sleep(3.2)

    MyProtocol.cancel_scheduled_message(heartbeat_id)
    print(f"  Cancelled heartbeat. Final sequence: {heartbeat.sequence}")

    # Example 2: Counter with compound logic
    print("\n2. Counter with compound update logic")
    print("-" * 60)

    counter = CounterMessage(counter=0, value=100)

    def print_counter(data: bytes):
        decoded = MyProtocol.decode(data)
        print(f"  [Counter] count={decoded.counter}, value={decoded.value}")

    # Update callback with complex logic
    def update_counter(msg):
        msg.counter += 1
        msg.value = 100 + (msg.counter * 10)  # Value increases with counter

    counter_id = MyProtocol.schedule_message(
        msg=counter,
        interval=0.5,
        send_callback=print_counter,
        update_callback=update_counter,
    )

    print(f"  Scheduled counter (ID: {counter_id})")
    print("  Counter will run for 2.5 seconds...")
    time.sleep(2.7)

    MyProtocol.cancel_scheduled_message(counter_id)
    print(
        f"  Cancelled counter. Final count: {counter.counter}, "
        f"value: {counter.value}"
    )

    # Example 3: Message without update callback (static)
    print("\n3. Static message (no update callback)")
    print("-" * 60)

    static_heartbeat = HeartbeatMessage(timestamp=99999, sequence=42, status="static")

    def print_static(data: bytes):
        decoded = MyProtocol.decode(data)
        print(f"  [Static] seq={decoded.sequence}, " f"timestamp={decoded.timestamp}")

    # No update callback - message stays the same
    static_id = MyProtocol.schedule_message(
        msg=static_heartbeat, interval=0.8, send_callback=print_static
    )

    print(f"  Scheduled static message (ID: {static_id})")
    print("  Static messages will be sent for 2 seconds...")
    time.sleep(2.5)

    MyProtocol.cancel_scheduled_message(static_id)
    print(
        f"  Cancelled static message. Values unchanged: "
        f"seq={static_heartbeat.sequence}, ts={static_heartbeat.timestamp}"
    )

    # Example 4: Multiple messages with different update patterns
    print("\n4. Multiple messages with different update patterns")
    print("-" * 60)

    hb1 = HeartbeatMessage(timestamp=0, sequence=0, status="fast")
    hb2 = HeartbeatMessage(timestamp=0, sequence=0, status="slow")

    def print_multi(data: bytes):
        decoded = MyProtocol.decode(data)
        print(f"  [{decoded.status}] seq={decoded.sequence}")

    def update_fast(msg):
        msg.sequence += 1
        msg.timestamp = int(time.time() * 1000)

    def update_slow(msg):
        msg.sequence += 10  # Increment by 10
        msg.timestamp = int(time.time() * 1000)

    fast_id = MyProtocol.schedule_message(hb1, 0.5, print_multi, update_fast)
    slow_id = MyProtocol.schedule_message(hb2, 1.0, print_multi, update_slow)

    print(f"  Scheduled fast (ID: {fast_id}) and slow (ID: {slow_id})")
    print("  Both will run for 3 seconds...")
    time.sleep(3.2)

    MyProtocol.cancel_all_scheduled_messages()
    print(f"  Cancelled all. Fast seq: {hb1.sequence}, Slow seq: {hb2.sequence}")

    # Final summary
    print("\n" + "=" * 60)
    print("Demo complete!")
    print(
        f"Currently scheduled messages: " f"{len(MyProtocol.get_scheduled_messages())}"
    )


if __name__ == "__main__":
    main()
