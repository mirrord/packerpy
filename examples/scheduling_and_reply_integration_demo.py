"""Demo showing integration of message scheduling and auto-reply features."""

import time
from packerpy.protocols.message import Message
from packerpy.protocols.message_partial import Encoding
from packerpy.protocols.protocol import Protocol, protocol


# Create a protocol instance
MyProtocol = Protocol()


# Define message types for a simple monitoring system
@protocol(MyProtocol)
class HeartbeatMessage(Message):
    """Periodic heartbeat sent by client."""

    encoding = Encoding.BIG_ENDIAN
    fields = {"client_id": {"type": "int(32)"}, "timestamp": {"type": "int(64)"}}


@protocol(MyProtocol)
class HeartbeatAckMessage(Message):
    """Acknowledgment of heartbeat by server."""

    encoding = Encoding.BIG_ENDIAN
    fields = {"client_id": {"type": "int(32)"}, "server_time": {"type": "int(64)"}}


@protocol(MyProtocol)
class StatusRequestMessage(Message):
    """Request for status information."""

    encoding = Encoding.BIG_ENDIAN
    fields = {"req_id": {"type": "int(32)"}}


@protocol(MyProtocol)
class StatusResponseMessage(Message):
    """Response with status information."""

    encoding = Encoding.BIG_ENDIAN
    fields = {
        "req_id": {"type": "int(32)"},
        "active_clients": {"type": "int(32)"},
        "uptime": {"type": "int(64)"},
    }


# Simulated state
class ServerState:
    """Simulate server state."""

    def __init__(self):
        self.active_clients = 0
        self.start_time = int(time.time())
        self.last_heartbeat = {}


server_state = ServerState()


def main():
    """Demonstrate combined scheduling and auto-reply."""

    print("Message Scheduling + Auto-Reply Integration Demo")
    print("=" * 60)
    print("\nSimulating a client-server monitoring system:")
    print("- Client sends periodic heartbeats (scheduling)")
    print("- Server auto-replies with ACKs (auto-reply)")
    print("- Client can request status (auto-reply)")
    print("=" * 60)

    # Setup: Client side
    print("\n[CLIENT SETUP]")

    client_id = 100
    heartbeat = HeartbeatMessage(client_id=client_id, timestamp=0)

    def send_from_client(data: bytes):
        """Simulate sending from client to server."""
        decoded = MyProtocol.decode(data)
        print(f"  CLIENT -> SERVER: {decoded.__class__.__name__}")

        # Simulate server receiving and processing
        server_receive(data)

    def update_heartbeat(msg):
        """Update timestamp before each heartbeat send."""
        msg.timestamp = int(time.time() * 1000)

    # Schedule periodic heartbeat every 1 second
    heartbeat_schedule_id = MyProtocol.schedule_message(
        msg=heartbeat,
        interval=1.0,
        send_callback=send_from_client,
        update_callback=update_heartbeat,
    )

    print(f"  ✓ Scheduled heartbeat (ID: {heartbeat_schedule_id})")

    # Setup: Server side auto-reply for heartbeats
    print("\n[SERVER SETUP]")

    heartbeat_ack = HeartbeatAckMessage(client_id=0, server_time=0)

    def send_from_server(data: bytes):
        """Simulate sending from server to client."""
        decoded = MyProtocol.decode(data)
        print(f"  SERVER -> CLIENT: {decoded.__class__.__name__}")

        # Simulate client receiving
        client_receive(data)

    def update_heartbeat_ack(heartbeat_msg, ack_msg):
        """Update ACK based on incoming heartbeat."""
        ack_msg.client_id = heartbeat_msg.client_id
        ack_msg.server_time = int(time.time() * 1000)

        # Track active clients
        server_state.last_heartbeat[heartbeat_msg.client_id] = time.time()
        server_state.active_clients = len(server_state.last_heartbeat)

    heartbeat_reply_id = MyProtocol.register_auto_reply(
        condition_callback=lambda msg: isinstance(msg, HeartbeatMessage),
        reply_msg=heartbeat_ack,
        send_callback=send_from_server,
        update_callback=update_heartbeat_ack,
    )

    print(f"  ✓ Registered heartbeat ACK auto-reply (ID: {heartbeat_reply_id})")

    # Setup: Server side auto-reply for status requests
    status_response = StatusResponseMessage(req_id=0, active_clients=0, uptime=0)

    def update_status_response(request_msg, response_msg):
        """Update status response with current server state."""
        response_msg.req_id = request_msg.req_id
        response_msg.active_clients = server_state.active_clients
        response_msg.uptime = int(time.time()) - server_state.start_time

    status_reply_id = MyProtocol.register_auto_reply(
        condition_callback=lambda msg: isinstance(msg, StatusRequestMessage),
        reply_msg=status_response,
        send_callback=send_from_server,
        update_callback=update_status_response,
    )

    print(f"  ✓ Registered status response auto-reply (ID: {status_reply_id})")

    # Helper functions
    def server_receive(data: bytes):
        """Process incoming messages on server."""
        incoming = MyProtocol.decode(data)
        if incoming:
            MyProtocol.check_auto_replies(incoming)

    def client_receive(data: bytes):
        """Process incoming messages on client."""
        decoded = MyProtocol.decode(data)
        if decoded and isinstance(decoded, HeartbeatAckMessage):
            print(f"    ✓ Received ACK (server_time={decoded.server_time})")
        elif decoded and isinstance(decoded, StatusResponseMessage):
            print(
                f"    ✓ Status: {decoded.active_clients} clients, "
                f"uptime={decoded.uptime}s"
            )

    # Run simulation
    print("\n[SIMULATION START]")
    print("Heartbeats will run for 3 seconds...\n")

    time.sleep(3.2)

    # Client sends a status request
    print("\n[CLIENT] Sending status request...")
    status_request = StatusRequestMessage(req_id=1001)
    encoded_request = MyProtocol.encode(status_request)
    send_from_client(encoded_request)

    time.sleep(0.5)

    # Show statistics
    print("\n[STATISTICS]")
    scheduled = MyProtocol.get_scheduled_messages()
    auto_replies = MyProtocol.get_auto_replies()
    print(f"  Active scheduled messages: {len(scheduled)}")
    print(f"  Registered auto-replies: {len(auto_replies)}")
    print(f"  Server active clients: {server_state.active_clients}")

    # Cleanup
    print("\n[CLEANUP]")
    MyProtocol.cancel_all_scheduled_messages()
    MyProtocol.unregister_all_auto_replies()
    print("  ✓ All scheduled messages cancelled")
    print("  ✓ All auto-replies unregistered")

    print("\n" + "=" * 60)
    print("Demo complete!")
    print("\nThis demo showed:")
    print("  • Scheduled heartbeats (time-based)")
    print("  • Auto-reply ACKs (event-based)")
    print("  • Status request-response (on-demand)")
    print("  • Dynamic state updates in replies")


if __name__ == "__main__":
    main()
