from typing import Annotated
from pydantic import BaseModel, Field

from .base import RequestData


class RomiResponseUserUtterance(BaseModel):
    """
    ユーザーの発話を表すクラス
    """

    utterance: Annotated[
        str,
        Field(
            title="ユーザーの発話テキスト",
            description="ユーザーの発話を設定します。",
            examples=["おはよう。"],
        ),
    ]
    should_include_in_conversation_log: Annotated[
        bool,
        Field(
            title="会話ログに含めるかどうか",
            description="user_utteranceに値を設定した場合はこのフラグも設定してください。Trueの場合、user_utteranceが会話ログに含まれます。Falseの場合、会話ログには含まれません。",
        ),
    ]


class CreateRomiResponseRequestData(RequestData):
    """
    ROMIの発話を生成するためのペイロードデータクラス
    """

    instruction: Annotated[
        str | None,
        Field(
            title="Romiの発話生成のためのインストラクション",
            description="どのような内容のレスポンスを生成するべきかを具体的に指示してください。",
            examples=[
                "朝のあいさつをしてください。明るい内容で最後にユーザーへ軽い質問を1つしてください。"
            ],
        ),
    ] = None
    user_utterance: Annotated[
        RomiResponseUserUtterance | None, Field(title="ユーザーの発話データ")
    ] = None
