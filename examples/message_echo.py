"""Example: Message-based echo server and client with multiple serialization formats."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from packerpy import Server, Client
from packerpy.protocols.message import Message, StringPartial, IntPartial


def handle_message(message: Message, address) -> Message:
    """
    Handle incoming messages.

    Args:
        message: Received message
        address: Sender address

    Returns:
        Response message
    """
    print(f"Received {message.message_type} from {address}")
    print(f"Payload: {message.payload}")
    print(f"Partials: {len(message.partials)}")

    # Create response with partials
    response = Message(
        message_type="echo_response",
        payload={
            "original": message.payload,
            "echo": f"Echoing: {message.payload.get('text', '')}",
        },
        message_id=message.message_id,
    )

    # Add partials to demonstrate composable structures
    response.add_partial(StringPartial(value="Server response"))
    response.add_partial(IntPartial(value=42))

    return response


async def run_server():
    """Run the message server."""
    server = Server(host="127.0.0.1", port=8080, message_handler=handle_message)

    print(f"Server using BYTES serialization")

    try:
        await server.start()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        await server.stop()


async def run_client():
    """Run the message client."""
    async with Client("127.0.0.1", 8080) as client:
        print(f"Client using BYTES serialization")

        # Create a message with partials
        message = Message(
            message_type="greeting",
            payload={"text": "Hello, Server!"},
            message_id="msg-001",
        )

        # Add partials to demonstrate composable structures
        message.add_partial(StringPartial(value="Client message"))
        message.add_partial(IntPartial(value=123))

        print(f"Sending: {message}")
        print(f"With {len(message.partials)} partials")

        response = await client.send_message(message)

        if response:
            print(f"Received: {response}")
            print(f"Response payload: {response.payload}")
            print(f"Response partials: {len(response.partials)}")
        else:
            print("Failed to receive response")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "client":
        asyncio.run(run_client())
    else:
        asyncio.run(run_server())
