from typing import Annotated
from pydantic import Field

from .base import ResponseData


class DiscoverAvailableRomisResponseData(ResponseData):
    """
    利用可能な Romi の発見に対するレスポンスのペイロードデータクラス
    """

    model: Annotated[str, Field(title="Romiのモデル名")]
    serial_number: Annotated[str, Field(title="Romiのシリアルナンバー")]
