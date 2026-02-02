"""Protocol definitions and interfaces."""

from packerpy.protocols.message import Message
from packerpy.protocols.message_partial import MessagePartial
from packerpy.protocols.protocol import Protocol, protocol, InvalidMessage
from packerpy.protocols.serializer import BytesSerializer

__all__ = [
    "Message",
    "MessagePartial",
    "Protocol",
    "protocol",
    "InvalidMessage",
    "BytesSerializer",
]
