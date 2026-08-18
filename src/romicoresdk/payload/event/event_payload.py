from enum import StrEnum
from pydantic import Discriminator, TypeAdapter
from typing import Annotated, Literal

from ..generic_payload import EventPayloadBase
from .data.requested_tool_call import RequestedToolCall
from .data.conversation_streaming_event import ConversationStreamingEventData


class EventType(StrEnum):
    """
    SDK <-> Romi の通信で使用するイベントのタイプ
    """

    # Romi -> SDK へ送られてくるイベント
    TOOL_CALL_INVOKED = "tool_call_invoked"
    CONVERSATION_STREAMING = "conversation_streaming"


class ToolCallInvokedEventPayload(
    EventPayloadBase[Literal[EventType.TOOL_CALL_INVOKED], RequestedToolCall]
):
    """tool_call_invoked event のペイロード。"""


class ConversationStreamingEventPayload(
    EventPayloadBase[
        Literal[EventType.CONVERSATION_STREAMING], ConversationStreamingEventData
    ]
):
    """conversation_streaming event のペイロード。"""


EventPayload = Annotated[
    ToolCallInvokedEventPayload | ConversationStreamingEventPayload,
    Discriminator("type"),
]

DEFAULT_EVENT_ADAPTER = TypeAdapter(EventPayload)
