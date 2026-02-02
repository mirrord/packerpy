"""Example: Synchronous TCP echo server and client."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from packerpy.transports.tcp.sync_server import SyncTCPServer
from packerpy.transports.tcp.sync_client import SyncTCPClient


def echo_handler(data: bytes, address) -> bytes:
    """Echo handler that returns received data."""
    print(f"Received from {address}: {data.decode()}")
    return data


def run_server():
    """Run the echo server."""
    server = SyncTCPServer("127.0.0.1", 8888, echo_handler)
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.stop()


def run_client():
    """Run the echo client."""
    with SyncTCPClient("127.0.0.1", 8888) as client:
        message = b"Hello, Server!"
        print(f"Sending: {message.decode()}")
        client.send(message)
        response = client.receive()
        print(f"Received: {response.decode()}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "client":
        run_client()
    else:
        run_server()
