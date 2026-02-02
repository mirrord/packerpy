"""Example: Synchronous UDP echo server and client."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from packerpy.transports.udp.sync_socket import SyncUDPSocket


def run_server():
    """Run the UDP echo server."""
    with SyncUDPSocket("127.0.0.1", 9999) as sock:
        print(f"UDP server listening on 127.0.0.1:9999")
        try:
            while True:
                data, addr = sock.receive_from()
                print(f"Received from {addr}: {data.decode()}")
                sock.send_to(data, addr)
        except KeyboardInterrupt:
            print("\nShutting down server...")


def run_client():
    """Run the UDP echo client."""
    with SyncUDPSocket() as sock:
        server_addr = ("127.0.0.1", 9999)
        message = b"Hello, UDP Server!"
        print(f"Sending: {message.decode()}")
        sock.send_to(message, server_addr)
        response, _ = sock.receive_from()
        print(f"Received: {response.decode()}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "client":
        run_client()
    else:
        run_server()
