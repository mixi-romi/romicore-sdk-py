from typing import Annotated
from pydantic import Field

from .base import ResponseData


class CreateRomiResponseResponseData(ResponseData):
    """
    ROMIの発話を表すレスポンスデータクラス
    """

    text: Annotated[str, Field(title="Romiの発話テキスト")]
    emotion: Annotated[str | None, Field(title="Romiの発話の感情")] = None
