from enum import StrEnum
from typing import Annotated
from pydantic import Field

from .base import RequestData


class ConversationSpeaker(StrEnum):
    """会話ストリームで扱う話者の指定"""

    ROMI = "romi"


class StartConversationStreamRequestData(RequestData):
    """会話ストリーム開始リクエストのペイロードデータクラス"""

    speaker: Annotated[
        ConversationSpeaker,
        Field(
            title="話者",
            description="会話ストリームで有効化する話者を指定します。",
            examples=["romi"],
        ),
    ]
