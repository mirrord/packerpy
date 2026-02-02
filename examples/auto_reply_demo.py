"""Demo of Protocol automatic reply feature."""

from packerpy.protocols.message import Message
from packerpy.protocols.message_partial import Encoding
from packerpy.protocols.protocol import Protocol, protocol


# Create a protocol instance
MyProtocol = Protocol()


# Define various message types
@protocol(MyProtocol)
class PingMessage(Message):
    """Ping request message."""

    encoding = Encoding.BIG_ENDIAN
    fields = {"seq": {"type": "int(32)"}, "timestamp": {"type": "int(64)"}}


@protocol(MyProtocol)
class PongMessage(Message):
    """Pong response message."""

    encoding = Encoding.BIG_ENDIAN
    fields = {"seq": {"type": "int(32)"}, "timestamp": {"type": "int(64)"}}


@protocol(MyProtocol)
class CommandMessage(Message):
    """Command message with ID and command code."""

    encoding = Encoding.BIG_ENDIAN
    fields = {"cmd_id": {"type": "int(32)"}, "command": {"type": "int(32)"}}


@protocol(MyProtocol)
class AckMessage(Message):
    """Acknowledgment message."""

    encoding = Encoding.BIG_ENDIAN
    fields = {"cmd_id": {"type": "int(32)"}, "status": {"type": "int(32)"}}


@protocol(MyProtocol)
class DataRequestMessage(Message):
    """Data request with query parameters."""

    encoding = Encoding.BIG_ENDIAN
    fields = {"req_id": {"type": "int(32)"}, "query": {"type": "int(32)"}}


@protocol(MyProtocol)
class DataResponseMessage(Message):
    """Data response with result."""

    encoding = Encoding.BIG_ENDIAN
    fields = {"req_id": {"type": "int(32)"}, "result": {"type": "int(32)"}}


def main():
    """Demonstrate automatic reply functionality."""

    print("Automatic Reply Feature Demo")
    print("=" * 60)

    # Example 1: Simple ping-pong auto-reply
    print("\n1. Simple Ping-Pong Auto-Reply")
    print("-" * 60)

    pong_template = PongMessage(seq=0, timestamp=0)

    def send_pong(data: bytes):
        decoded = MyProtocol.decode(data)
        print(f"  -> Sent PONG: seq={decoded.seq}, timestamp={decoded.timestamp}")

    # Update callback copies data from ping to pong
    def update_pong(ping, pong):
        pong.seq = ping.seq
        pong.timestamp = ping.timestamp

    # Register auto-reply for ping messages
    pong_id = MyProtocol.register_auto_reply(
        condition_callback=lambda msg: isinstance(msg, PingMessage),
        reply_msg=pong_template,
        send_callback=send_pong,
        update_callback=update_pong,
    )

    print(f"  Registered ping-pong auto-reply (ID: {pong_id})")

    # Simulate receiving ping messages
    ping1 = PingMessage(seq=1, timestamp=1000)
    ping2 = PingMessage(seq=2, timestamp=2000)

    print(f"\n  Received PING: seq={ping1.seq}, timestamp={ping1.timestamp}")
    MyProtocol.check_auto_replies(ping1)

    print(f"  Received PING: seq={ping2.seq}, timestamp={ping2.timestamp}")
    MyProtocol.check_auto_replies(ping2)

    # Example 2: Command acknowledgment with status
    print("\n2. Command Acknowledgment Auto-Reply")
    print("-" * 60)

    ack_template = AckMessage(cmd_id=0, status=0)

    def send_ack(data: bytes):
        decoded = MyProtocol.decode(data)
        print(f"  -> Sent ACK: cmd_id={decoded.cmd_id}, status={decoded.status}")

    # Update callback sets status based on command validity
    def update_ack(cmd, ack):
        ack.cmd_id = cmd.cmd_id
        # Status 200 for valid commands (1-10), 400 otherwise
        if 1 <= cmd.command <= 10:
            ack.status = 200
        else:
            ack.status = 400

    ack_id = MyProtocol.register_auto_reply(
        condition_callback=lambda msg: isinstance(msg, CommandMessage),
        reply_msg=ack_template,
        send_callback=send_ack,
        update_callback=update_ack,
    )

    print(f"  Registered command ACK auto-reply (ID: {ack_id})")

    # Simulate receiving commands
    cmd1 = CommandMessage(cmd_id=101, command=5)
    cmd2 = CommandMessage(cmd_id=102, command=99)

    print(f"\n  Received CMD: cmd_id={cmd1.cmd_id}, command={cmd1.command}")
    MyProtocol.check_auto_replies(cmd1)

    print(f"  Received CMD: cmd_id={cmd2.cmd_id}, command={cmd2.command}")
    MyProtocol.check_auto_replies(cmd2)

    # Example 3: Conditional reply based on message content
    print("\n3. Conditional Auto-Reply (only specific commands)")
    print("-" * 60)

    special_ack = AckMessage(cmd_id=0, status=999)

    def send_special_ack(data: bytes):
        decoded = MyProtocol.decode(data)
        print(f"  -> Sent SPECIAL ACK: cmd_id={decoded.cmd_id}")

    def update_special(cmd, ack):
        ack.cmd_id = cmd.cmd_id

    # Only reply to command == 42
    special_id = MyProtocol.register_auto_reply(
        condition_callback=lambda msg: isinstance(msg, CommandMessage)
        and msg.command == 42,
        reply_msg=special_ack,
        send_callback=send_special_ack,
        update_callback=update_special,
    )

    print(f"  Registered special ACK auto-reply for cmd=42 (ID: {special_id})")

    # Test with different commands
    cmd_normal = CommandMessage(cmd_id=201, command=10)
    cmd_special = CommandMessage(cmd_id=202, command=42)

    print(f"\n  Received CMD: cmd_id={cmd_normal.cmd_id}, command={cmd_normal.command}")
    replies = MyProtocol.check_auto_replies(cmd_normal)
    print(f"  Replies sent: {replies}")

    print(f"  Received CMD: cmd_id={cmd_special.cmd_id}, command={cmd_special.command}")
    replies = MyProtocol.check_auto_replies(cmd_special)
    print(f"  Replies sent: {replies}")

    # Example 4: Data query with computed response
    print("\n4. Data Query with Computed Response")
    print("-" * 60)

    response_template = DataResponseMessage(req_id=0, result=0)

    def send_response(data: bytes):
        decoded = MyProtocol.decode(data)
        print(f"  -> Sent RESPONSE: req_id={decoded.req_id}, result={decoded.result}")

    # Compute result based on query (e.g., multiply by 10)
    def compute_response(request, response):
        response.req_id = request.req_id
        response.result = request.query * 10

    response_id = MyProtocol.register_auto_reply(
        condition_callback=lambda msg: isinstance(msg, DataRequestMessage),
        reply_msg=response_template,
        send_callback=send_response,
        update_callback=compute_response,
    )

    print(f"  Registered data response auto-reply (ID: {response_id})")

    # Simulate data requests
    req1 = DataRequestMessage(req_id=1001, query=5)
    req2 = DataRequestMessage(req_id=1002, query=8)

    print(f"\n  Received REQUEST: req_id={req1.req_id}, query={req1.query}")
    MyProtocol.check_auto_replies(req1)

    print(f"  Received REQUEST: req_id={req2.req_id}, query={req2.query}")
    MyProtocol.check_auto_replies(req2)

    # Example 5: Multiple auto-replies for same message
    print("\n5. Multiple Auto-Replies for Same Message")
    print("-" * 60)

    def send_logging(data: bytes):
        print("  -> [Logger] Message logged")

    def send_metrics(data: bytes):
        print("  -> [Metrics] Message counted")

    # Register multiple handlers for CommandMessage
    log_id = MyProtocol.register_auto_reply(
        condition_callback=lambda msg: isinstance(msg, CommandMessage),
        reply_msg=ack_template,
        send_callback=send_logging,
    )

    metrics_id = MyProtocol.register_auto_reply(
        condition_callback=lambda msg: isinstance(msg, CommandMessage),
        reply_msg=ack_template,
        send_callback=send_metrics,
    )

    print(f"  Registered logging auto-reply (ID: {log_id})")
    print(f"  Registered metrics auto-reply (ID: {metrics_id})")

    cmd_multi = CommandMessage(cmd_id=301, command=7)
    print(f"\n  Received CMD: cmd_id={cmd_multi.cmd_id}, command={cmd_multi.command}")
    replies = MyProtocol.check_auto_replies(cmd_multi)
    print(f"  Total replies sent: {replies}")

    # Show current auto-replies
    print("\n" + "=" * 60)
    auto_replies = MyProtocol.get_auto_replies()
    print(f"Total registered auto-replies: {len(auto_replies)}")

    # Clean up
    print("\nUnregistering all auto-replies...")
    MyProtocol.unregister_all_auto_replies()
    print(f"Remaining auto-replies: {len(MyProtocol.get_auto_replies())}")
    print("\nDemo complete!")


if __name__ == "__main__":
    main()
