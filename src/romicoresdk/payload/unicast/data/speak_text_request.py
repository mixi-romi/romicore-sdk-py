from typing import Annotated
from pydantic import Field

from ...types import Emotion, Language
from .base import RequestData


class SpeakTextRequestData(RequestData):
    """
    Romiに指定したテキストを発話させるためのペイロードデータクラス
    """

    emotion: Annotated[Emotion, Field(title="発話の感情")]
    lang: Annotated[Language, Field(title="発話の言語")]
    text: Annotated[
        str,
        Field(
            title="発話するテキスト",
            min_length=1,
            description="Romiに発話させるテキストを与えてください。空文字はエラーとなります。",
            examples=[
                "こんにちは、ロミィだよ！オーナーは調子どう？",
                "Hi, I am Romi! How are you?",
            ],
        ),
    ]
