from typing import Annotated
from pydantic import BaseModel, Field


class RequestedToolCall(BaseModel):
    """
    Romiからツールの呼び出し要求を受信するペイロードクラス
    """

    name: Annotated[str, Field(title="ツールの名前", examples=["get_picture"])]

    call_id: Annotated[str, Field(title="ツールの呼び出し ID", examples=["12345"])]

    arguments_json: Annotated[
        str,
        Field(
            title="ツールの引数 JSON",
            examples=['{"param1": "value1"}'],
        ),
    ]
