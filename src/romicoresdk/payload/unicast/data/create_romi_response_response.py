from typing import Annotated
from pydantic import BaseModel, Field

from .base import ResponseData


class CreateRomiResponseUtterance(BaseModel):
    """
    ROMIの発話単位（text, emotion）を表すデータクラス
    """

    text: Annotated[str, Field(title="Romiの発話テキスト")]
    emotion: Annotated[str | None, Field(title="Romiの発話の感情")] = None


class CreateRomiResponseResponseData(ResponseData):
    """
    ROMIの発話を表すレスポンスデータクラス (v1, baseline)

    v2登場前の仕様はtext/emotion単体だったが、現行FWはこの request_type
    (バージョンサフィックス無し)に対して以下のいずれかを返しうる:

    - 変更前のFW: ``{"text": ..., "emotion": ...}``
    - v1/v2を併存させていない移行期のFW: ``{"utterances": [...]}``

    どちらの形状でも受け取れるよう全フィールドをoptionalにしている。
    正規化は :func:`converters.to_romi_response` が担う。
    """

    text: Annotated[str | None, Field(title="Romiの発話テキスト")] = None
    emotion: Annotated[str | None, Field(title="Romiの発話の感情")] = None
    utterances: Annotated[
        list[CreateRomiResponseUtterance] | None,
        Field(title="Romi発話（text, emotion）のリスト"),
    ] = None


class CreateRomiResponseResponseDataV2(ResponseData):
    """
    ROMIの発話を表すレスポンスデータクラス (v2)

    発話は複数チャンクに分かれて生成されるため、text/emotion の組を
    発話順のリストとして保持します。
    """

    utterances: Annotated[
        list[CreateRomiResponseUtterance],
        Field(title="Romi発話（text, emotion）のリスト"),
    ]
