"""payload の共通エンベロープを定義する Generic ベースモデル群。

各 API の payload は ``request_id`` / ``request_type`` / ``data`` / ``ok`` / ``error``
という共通フィールドを繰り返し持つ。API ごとに変わるのは ``request_type`` の Literal 値と
``data`` の型だけであるため、共通フィールドを Generic 基底に集約し、各 API は薄い
名前付きサブクラスとして定義する。

名前付きサブクラスにすることで、生成される JSON Schema の ``$defs`` 名は
``AddToolResponseSuccessPayload`` のように具象クラス名のまま保たれ、AsyncAPI/OpenAPI
コントラクトが維持される。
"""

from typing import Annotated, Generic, Literal, TypeVar

from pydantic import BaseModel, Field

from .error_info import ErrorInfo

RequestTypeT = TypeVar("RequestTypeT")
DataT = TypeVar("DataT")


class RequestPayload(BaseModel, Generic[RequestTypeT, DataT]):
    """リクエスト payload の共通エンベロープ。"""

    request_id: Annotated[str, Field(title="リクエストID")]
    request_type: Annotated[RequestTypeT, Field(title="リクエストタイプ")]
    data: Annotated[DataT, Field(title="リクエストデータ")]


class SuccessResponsePayload(BaseModel, Generic[RequestTypeT, DataT]):
    """成功レスポンス payload の共通エンベロープ（``ok: True``）。"""

    request_id: Annotated[str, Field(title="リクエストID")]
    request_type: Annotated[RequestTypeT, Field(title="リクエストタイプ")]
    data: Annotated[DataT, Field(title="レスポンスデータ")]
    ok: Annotated[Literal[True], Field(title="リクエストの処理が成功したかどうか")]


class ErrorResponsePayload(BaseModel, Generic[RequestTypeT]):
    """エラーレスポンス payload の共通エンベロープ（``ok: False``）。"""

    request_id: Annotated[str, Field(title="リクエストID")]
    request_type: Annotated[RequestTypeT, Field(title="リクエストタイプ")]
    ok: Annotated[Literal[False], Field(title="リクエストの処理が成功したかどうか")]
    error: Annotated[
        ErrorInfo, Field(title="エラーメッセージ (okがFalseの場合にエラー内容を記述)")
    ]
