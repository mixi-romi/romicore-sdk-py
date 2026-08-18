from typing import Annotated

from pydantic import Field

from ...unicast.data.start_conversation_stream_request import ConversationSpeaker
from .base import EventData


class ConversationStreamingEventData(EventData):
    """conversation_streaming イベントのデータ。"""

    speaker: Annotated[ConversationSpeaker, Field(title="話者")]
    utterance_text: Annotated[str, Field(title="発話テキスト")]
    timestamp: Annotated[int, Field(title="UNIXタイムスタンプ")]
