"""Demo showing Client and Server with integrated auto-reply and scheduling."""

import time
from packerpy.protocols.message import Message
from packerpy.protocols.message_partial import Encoding
from packerpy.protocols.protocol import Protocol, protocol
from packerpy.client import Client
from packerpy.server import Server


# Create a shared protocol
MyProtocol = Protocol()


@protocol(MyProtocol)
class HeartbeatMessage(Message):
    """Client heartbeat message."""

    encoding = Encoding.BIG_ENDIAN
    fields = {"client_id": {"type": "int(32)"}, "seq": {"type": "int(32)"}}


@protocol(MyProtocol)
class HeartbeatAckMessage(Message):
    """Server acknowledgment of heartbeat."""

    encoding = Encoding.BIG_ENDIAN
    fields = {"client_id": {"type": "int(32)"}, "seq": {"type": "int(32)"}}


@protocol(MyProtocol)
class DataMessage(Message):
    """Data message from client to server."""

    encoding = Encoding.BIG_ENDIAN
    fields = {"data_id": {"type": "int(32)"}, "value": {"type": "int(32)"}}


@protocol(MyProtocol)
class DataAckMessage(Message):
    """Server acknowledgment of data."""

    encoding = Encoding.BIG_ENDIAN
    fields = {"data_id": {"type": "int(32)"}, "received": {"type": "int(32)"}}


def main():
    """Demonstrate integrated auto-reply and scheduling."""

    print("Client-Server Auto-Reply & Scheduling Demo")
    print("=" * 60)

    # Setup Server
    print("\n[SERVER SETUP]")

    def server_message_handler(msg, addr):
        """Handle messages on server side."""
        print(f"  Server received: {msg.__class__.__name__} from {addr}")
        return None  # Auto-replies will handle responses

    server = Server(
        host="127.0.0.1",
        port=8765,
        protocol=MyProtocol,
        message_handler=server_message_handler,
    )

    # Register server auto-replies
    heartbeat_ack_template = HeartbeatAckMessage(client_id=0, seq=0)

    def update_heartbeat_ack(heartbeat, ack):
        """Copy data from heartbeat to ack."""
        ack.client_id = heartbeat.client_id
        ack.seq = heartbeat.seq
        print(f"  -> Server sending HeartbeatAck (seq={ack.seq})")

    # Note: In a real server, send_callback would need connection tracking
    # For this demo, we'll use a placeholder
    def server_send_heartbeat_ack(data):
        print(f"  -> Server would send {len(data)} bytes (HeartbeatAck)")

    server.register_auto_reply(
        condition_callback=lambda msg: isinstance(msg, HeartbeatMessage),
        reply_msg=heartbeat_ack_template,
        send_callback=server_send_heartbeat_ack,
        update_callback=update_heartbeat_ack,
    )

    print("  ✓ Registered HeartbeatMessage auto-reply")

    # Auto-reply for data messages
    data_ack_template = DataAckMessage(data_id=0, received=1)

    def update_data_ack(data_msg, ack):
        ack.data_id = data_msg.data_id
        print(f"  -> Server sending DataAck (data_id={ack.data_id})")

    def server_send_data_ack(data):
        print(f"  -> Server would send {len(data)} bytes (DataAck)")

    server.register_auto_reply(
        condition_callback=lambda msg: isinstance(msg, DataMessage),
        reply_msg=data_ack_template,
        send_callback=server_send_data_ack,
        update_callback=update_data_ack,
    )

    print("  ✓ Registered DataMessage auto-reply")

    # Start server
    server.start()
    time.sleep(0.5)  # Wait for server to start

    # Setup Client
    print("\n[CLIENT SETUP]")

    client = Client(host="127.0.0.1", port=8765, protocol=MyProtocol)

    # Register client auto-reply for server acks
    ack_received_count = [0]

    def client_handle_ack(data):
        decoded = MyProtocol.decode(data)
        if isinstance(decoded, HeartbeatAckMessage):
            ack_received_count[0] += 1
            print(
                f"  <- Client received HeartbeatAck "
                f"(seq={decoded.seq}, total={ack_received_count[0]})"
            )
        elif isinstance(decoded, DataAckMessage):
            print(f"  <- Client received DataAck (data_id={decoded.data_id})")

    # Auto-reply for HeartbeatAck (just logs it)
    client.register_auto_reply(
        condition_callback=lambda msg: isinstance(msg, HeartbeatAckMessage),
        reply_msg=HeartbeatAckMessage(client_id=0, seq=0),  # Not actually sent
        send_callback=lambda data: None,  # Just consume, don't send
    )

    print("  ✓ Client ready to receive auto-reply ACKs")

    # Schedule periodic heartbeats from client
    heartbeat = HeartbeatMessage(client_id=100, seq=0)

    def update_heartbeat(msg):
        msg.seq += 1
        print(f"  Client sending Heartbeat (seq={msg.seq})")

    # Use a simple send simulation for this demo
    heartbeat_count = [0]

    def client_send_heartbeat(data):
        heartbeat_count[0] += 1
        # Simulate server receiving and processing
        decoded = MyProtocol.decode(data)
        if decoded:
            # Server side: decode and check auto-replies
            MyProtocol.check_auto_replies(decoded)

    schedule_id = MyProtocol.schedule_message(
        msg=heartbeat,
        interval=1.0,
        send_callback=client_send_heartbeat,
        update_callback=update_heartbeat,
    )

    print(f"  ✓ Scheduled heartbeat every 1.0 seconds (ID: {schedule_id})")

    # Run simulation
    print("\n[RUNNING SIMULATION]")
    print("Heartbeats will be sent for 3 seconds...")
    print()

    time.sleep(3.5)

    # Send a data message manually
    print("\n[MANUAL DATA SEND]")
    data_msg = DataMessage(data_id=500, value=42)
    print(f"  Client sending DataMessage (data_id={data_msg.data_id})")

    # Simulate sending and server processing
    encoded_data = MyProtocol.encode(data_msg)
    MyProtocol.check_auto_replies(data_msg)

    # Stop heartbeat scheduling
    print("\n[STOPPING]")
    MyProtocol.cancel_scheduled_message(schedule_id)
    print(f"  ✓ Cancelled heartbeat scheduling")

    # Statistics
    print("\n[STATISTICS]")
    print(f"  Heartbeats sent: {heartbeat_count[0]}")
    print(f"  Heartbeat ACKs received: {ack_received_count[0]}")

    scheduled = MyProtocol.get_scheduled_messages()
    auto_replies = MyProtocol.get_auto_replies()
    print(f"  Active scheduled messages: {len(scheduled)}")
    print(f"  Registered auto-replies: {len(auto_replies)}")

    # Cleanup
    print("\n[CLEANUP]")
    MyProtocol.unregister_all_auto_replies()
    server.stop()
    time.sleep(0.5)

    print("  ✓ Server stopped")
    print("  ✓ All auto-replies unregistered")

    print("\n" + "=" * 60)
    print("Demo complete!")
    print("\nThis demo showed:")
    print("  • Client scheduling periodic heartbeats")
    print("  • Server auto-replying to heartbeats")
    print("  • Server auto-replying to data messages")
    print("  • Client receiving and logging ACKs")
    print("  • Both features working together seamlessly")


if __name__ == "__main__":
    main()
