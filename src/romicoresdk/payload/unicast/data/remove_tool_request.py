from typing import Annotated
from pydantic import Field

from .base import RequestData


class RemoveToolRequestData(RequestData):
    """
    ツール削除リクエストのペイロードデータクラス
    """

    name: Annotated[str, Field(title="削除対象ツール名", examples=["target"])]
