from typing import Annotated
from pydantic import Field

from .base import ResponseData


class GetRegisteredToolsResponseData(ResponseData):
    """
    登録済みツール一覧取得レスポンスのペイロードデータクラス
    """

    tool_names: Annotated[
        list[str],
        Field(
            title="登録済みツール名一覧",
            description="Romi に登録済みのツール名配列を設定します。",
            examples=[["re_tool1", "re_tool2", "re_tool3"]],
        ),
    ]
