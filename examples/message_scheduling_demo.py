"""Demo of Protocol message scheduling feature."""

import time
from packerpy.protocols.message import Message
from packerpy.protocols.message_partial import Encoding
from packerpy.protocols.protocol import Protocol, protocol


# Create a protocol instance
MyProtocol = Protocol()


# Define a simple heartbeat message
@protocol(MyProtocol)
class HeartbeatMessage(Message):
    """Periodic heartbeat message."""

    encoding = Encoding.BIG_ENDIAN
    fields = {"timestamp": {"type": "int(64)"}, "status": {"type": "str"}}


# Define a status update message
@protocol(MyProtocol)
class StatusUpdate(Message):
    """Status update message."""

    encoding = Encoding.BIG_ENDIAN
    fields = {"cpu_usage": {"type": "float"}, "memory_usage": {"type": "float"}}


def main():
    """Demonstrate message scheduling."""

    # Create messages
    heartbeat = HeartbeatMessage(timestamp=0, status="alive")
    status = StatusUpdate(cpu_usage=25.5, memory_usage=60.0)

    # Create a simple callback that prints the encoded data
    def print_callback(data: bytes):
        print(f"[{time.time():.2f}] Sending {len(data)} bytes: {data[:50]}...")

    print("Starting message scheduling demo...")
    print("=" * 60)

    # Schedule heartbeat every 1 second
    heartbeat_id = MyProtocol.schedule_message(
        msg=heartbeat, interval=1.0, send_callback=print_callback
    )
    print(f"Scheduled heartbeat message (ID: {heartbeat_id})")

    # Schedule status update every 2 seconds
    status_id = MyProtocol.schedule_message(
        msg=status, interval=2.0, send_callback=print_callback
    )
    print(f"Scheduled status update message (ID: {status_id})")

    print("\nMessages will be sent for 5 seconds...")
    print("=" * 60)

    # Let them run for 5 seconds
    time.sleep(5)

    print("\n" + "=" * 60)
    print("Cancelling heartbeat message...")
    MyProtocol.cancel_scheduled_message(heartbeat_id)

    print("Status updates will continue for 3 more seconds...")
    time.sleep(3)

    print("\n" + "=" * 60)
    print("Cancelling all scheduled messages...")
    MyProtocol.cancel_all_scheduled_messages()

    print("Demo complete!")

    # Check that no messages are scheduled
    scheduled = MyProtocol.get_scheduled_messages()
    print(f"\nCurrently scheduled messages: {len(scheduled)}")


if __name__ == "__main__":
    main()
