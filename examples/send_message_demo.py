"""Demo showing that Client and Server send() methods accept both Message and bytes."""

import time
from packerpy.client import Client
from packerpy.server import Server
from packerpy.protocols.protocol import Protocol
from packerpy.protocols.message import Message, Encoding


# Define a simple message class
class TextMessage(Message):
    """Simple text message."""

    encoding = Encoding.BIG_ENDIAN
    fields = {"text": {"type": "str"}}


def main():
    # Create protocol and register message type
    protocol = Protocol()
    protocol.register(TextMessage)

    # Create and start server
    def echo_handler(msg, addr):
        print(f"Server received: {msg}")
        return msg

    server = Server(
        host="127.0.0.1", port=8888, message_handler=echo_handler, protocol=protocol
    )
    server.start()
    time.sleep(0.2)

    # Create and connect client
    client = Client(host="127.0.0.1", port=8888, protocol=protocol)
    client.connect()
    time.sleep(0.2)

    # Test 1: Send a Message object
    print("\n=== Test 1: Sending Message object ===")
    msg = TextMessage()
    msg.text = "Hello from Message object!"
    success = client.send(msg)
    print(f"Send Message object: {'Success' if success else 'Failed'}")

    time.sleep(0.1)
    response = client.receive(timeout=1.0)
    if response:
        print(f"Client received response: {response}")

    # Test 2: Send raw bytes
    print("\n=== Test 2: Sending raw bytes ===")
    # Encode a message to bytes first, then send the bytes directly
    msg2 = TextMessage()
    msg2.text = "Hello from raw bytes!"
    raw_bytes = protocol.encode_message(msg2)
    success = client.send(raw_bytes)
    print(f"Send raw bytes: {'Success' if success else 'Failed'}")

    time.sleep(0.1)
    response2 = client.receive(timeout=1.0)
    if response2:
        print(f"Client received response: {response2}")

    # Cleanup
    time.sleep(0.2)
    client.close()
    server.stop()
    print("\n=== Demo complete ===")


if __name__ == "__main__":
    main()
