from pydantic import Discriminator, TypeAdapter
from typing import Annotated, Literal

from ..request_type import RequestType
from ..generic_payload import (
    SuccessResponsePayload,
    ErrorResponsePayload as _ErrorResponsePayloadBase,
)
from .data.get_resource_url_response import GetResourceUrlResponseData


# このモジュール（to_romi のレスポンス）で扱う request_type の集合。
# 現状は get_resource_url のみ。エラー payload もこの集合に絞り、方向違いの
# request_type を持つレスポンスを ValidationError として検知する。
_ToRomiResponseRequestType = Literal[RequestType.GET_RESOURCE_URL]


class ErrorResponsePayload(_ErrorResponsePayloadBase[_ToRomiResponseRequestType]):
    """to_romi レスポンス共通のエラー payload（from_romi_response と同形）。

    ``request_type`` はこのモジュールが扱う種別（成功側と同じ集合）に限定する。
    成功 API が増えたら ``_ToRomiResponseRequestType`` に追加する。
    """


# --- 成功レスポンス（API ごとに data 型が異なるため個別に定義）-------------------


class GetResourceUrlResponseSuccessPayload(
    SuccessResponsePayload[
        Literal[RequestType.GET_RESOURCE_URL], GetResourceUrlResponseData
    ]
): ...


# 成功レスポンスは request_type で識別する。
# API が増えたら Annotated[A | B | ..., Discriminator("request_type")] に拡張する。
ToRomiResponseSuccessPayload = GetResourceUrlResponseSuccessPayload

# まず ok で成功/エラーを分け、成功側はさらに request_type で識別する。
ToRomiResponsePayload = Annotated[
    ToRomiResponseSuccessPayload | ErrorResponsePayload,
    Discriminator("ok"),
]

DEFAULT_TO_ROMI_RESPONSE_ADAPTER = TypeAdapter(ToRomiResponsePayload)
