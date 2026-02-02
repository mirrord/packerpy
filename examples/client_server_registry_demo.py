"""Example showing Client/Server with protocol registry."""

import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from packerpy import Client, Server
from packerpy.protocols import Message, Protocol, protocol
from packerpy.protocols.message import Encoding


# Create shared protocol for client and server
SharedProtocol = Protocol()


# Register message types with the protocol
@protocol(SharedProtocol)
class PingMessage(Message):
    """Ping request message."""

    encoding = Encoding.BIG_ENDIAN
    fields = {
        "sequence": {"type": "int(32)"},
        "timestamp": {"type": "int(64)"},
    }


@protocol(SharedProtocol)
class PongMessage(Message):
    """Pong response message."""

    encoding = Encoding.BIG_ENDIAN
    fields = {
        "sequence": {"type": "int(32)"},
        "timestamp": {"type": "int(64)"},
        "server_time": {"type": "int(64)"},
    }


def message_handler(msg, address):
    """Handle incoming messages on the server."""
    print(f"[Server] Received {type(msg).__name__} from {address}")

    if isinstance(msg, PingMessage):
        # Respond with pong
        response = PongMessage(
            sequence=msg.sequence,
            timestamp=msg.timestamp,
            server_time=int(time.time() * 1000),
        )
        print(f"[Server] Sending PongMessage (seq={msg.sequence})")
        return response

    return None


def demo_client_server():
    """Demonstrate client-server with protocol registry."""
    print("=== Client/Server with Protocol Registry ===\n")

    # Create server with shared protocol
    print("Starting server...")
    server = Server(
        host="127.0.0.1",
        port=9999,
        message_handler=message_handler,
        protocol=SharedProtocol,
    )
    server.start()
    time.sleep(0.5)  # Wait for server to start

    # Create client with shared protocol
    print("Connecting client...")
    client = Client(host="127.0.0.1", port=9999, protocol=SharedProtocol)
    client.connect()
    time.sleep(0.5)  # Wait for connection

    # Send ping messages
    print("\nSending ping messages...\n")
    for i in range(3):
        ping = PingMessage(sequence=i, timestamp=int(time.time() * 1000))
        print(f"[Client] Sending PingMessage (seq={i})")
        client.send(ping)
        time.sleep(0.2)

        # Receive pong response
        pong = client.receive(timeout=1.0)
        if pong:
            print(f"[Client] Received {type(pong).__name__} (seq={pong.sequence})")
            print(f"         Round-trip time: {pong.server_time - pong.timestamp}ms\n")
        else:
            print("[Client] No response received\n")

    # Cleanup
    print("Shutting down...")
    client.close()
    server.stop()
    time.sleep(0.2)

    print("Demo complete!")


if __name__ == "__main__":
    demo_client_server()
