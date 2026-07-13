from pydantic import BaseModel, Field
from enum import StrEnum
from typing import Annotated, Literal

from .data.requested_tool_call import RequestedToolCall
from .data.conversation_streaming_event import ConversationStreamingEventData


class EventType(StrEnum):
    """
    SDKからeventを受信するタイプ
    """

    TOOL_CALL_INVOKED = "tool_call_invoked"
    CONVERSATION_STREAMING = "conversation_streaming"


class EventPayloadBase(BaseModel):
    """SDKから受信する event の共通ペイロード。"""

    event_id: Annotated[str, Field(title="イベントID")]
    type: Annotated[EventType, Field(title="イベントタイプ")]


class ToolCallInvokedEventPayload(EventPayloadBase):
    """tool_call_invoked event のペイロード。"""

    type: Annotated[
        Literal[EventType.TOOL_CALL_INVOKED], Field(title="イベントタイプ")
    ] = EventType.TOOL_CALL_INVOKED
    data: Annotated[RequestedToolCall, Field(title="イベントデータ")]


class ConversationStreamingEventPayload(EventPayloadBase):
    """conversation_streaming event のペイロード。"""

    type: Annotated[
        Literal[EventType.CONVERSATION_STREAMING], Field(title="イベントタイプ")
    ] = EventType.CONVERSATION_STREAMING
    data: Annotated[ConversationStreamingEventData, Field(title="イベントデータ")]


EventPayload = Annotated[
    ToolCallInvokedEventPayload | ConversationStreamingEventPayload,
    Field(discriminator="type"),
]

EventData = RequestedToolCall | ConversationStreamingEventData
