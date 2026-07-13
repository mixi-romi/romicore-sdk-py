from typing import Annotated

from pydantic import BaseModel, Field


class ErrorInfo(BaseModel):
    """
    エラー情報のデータクラス
    """

    code: Annotated[str, Field(title="エラーコード")]
    message: Annotated[str, Field(title="エラーメッセージ")]
