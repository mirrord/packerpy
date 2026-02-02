"""Simple test to verify no coroutine warnings are produced."""

import time
import warnings
from packerpy.client import Client
from packerpy.server import Server
from packerpy.protocols.protocol import Protocol
from packerpy.protocols.message import Message, Encoding


class SimpleMessage(Message):
    """Simple test message."""

    encoding = Encoding.BIG_ENDIAN
    fields = {"data": {"type": "str"}}


def main():
    # Catch all warnings
    warnings.simplefilter("error", RuntimeWarning)

    protocol = Protocol()
    protocol.register(SimpleMessage)

    # Test 1: Normal operation
    print("Test 1: Normal send and receive")
    server = Server(host="127.0.0.1", port=9999, protocol=protocol)
    server.start()
    time.sleep(0.2)

    client = Client(host="127.0.0.1", port=9999, protocol=protocol)
    client.connect()
    time.sleep(0.2)

    msg = SimpleMessage()
    msg.data = "test"
    client.send(msg)
    time.sleep(0.1)

    client.close()
    server.stop()
    time.sleep(0.2)
    print("✓ Test 1 passed - no warnings\n")

    # Test 2: Send raw bytes
    print("Test 2: Send raw bytes")
    server2 = Server(host="127.0.0.1", port=9998, protocol=protocol)
    server2.start()
    time.sleep(0.2)

    client2 = Client(host="127.0.0.1", port=9998, protocol=protocol)
    client2.connect()
    time.sleep(0.2)

    msg2 = SimpleMessage()
    msg2.data = "raw bytes test"
    raw_data = protocol.encode_message(msg2)
    client2.send(raw_data)
    time.sleep(0.1)

    client2.close()
    server2.stop()
    time.sleep(0.2)
    print("✓ Test 2 passed - no warnings\n")

    print("=" * 50)
    print("All tests passed! No coroutine warnings detected.")
    print("=" * 50)


if __name__ == "__main__":
    try:
        main()
    except RuntimeWarning as e:
        print(f"❌ FAILED: RuntimeWarning detected: {e}")
        raise
