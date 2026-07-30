from pydantic import Discriminator, Field, TypeAdapter
from typing import Annotated, Literal

from ..request_type import RequestType
from ..generic_payload import (
    SuccessResponsePayload,
    ErrorResponsePayload as _ErrorResponsePayloadBase,
)
from .data.discover_available_romis_response import DiscoverAvailableRomisResponseData
from .data.add_tool_response import AddToolResponseData
from .data.remove_tool_response import RemoveToolResponseData
from .data.create_romi_response_response import (
    CreateRomiResponseResponseData,
    CreateRomiResponseResponseDataV2,
)
from .data.refresh_sdk_device_certificate_response import (
    RefreshSdkDeviceCertificateResponseData,
)
from .data.get_registered_tools_response import GetRegisteredToolsResponseData
from .data.start_conversation_stream_response import StartConversationStreamResponseData
from .data.stop_conversation_stream_response import StopConversationStreamResponseData
from .data.speak_text_response import SpeakTextResponseData


# このモジュール（from_romi のレスポンス）のエラー payload で扱う request_type の集合。
# 成功側の各種別に加え、Romi がリクエストの payload パースに失敗して request_type を
# 特定できなかった場合の ``unspecified`` を許容する。方向違いの request_type を持つ
# レスポンスは引き続き ValidationError として検知できる。
_FromRomiResponseRequestType = Literal[
    RequestType.DISCOVER_AVAILABLE_ROMIS,
    RequestType.ADD_TOOL,
    RequestType.REMOVE_TOOL,
    RequestType.CREATE_ROMI_RESPONSE,
    RequestType.CREATE_ROMI_RESPONSE_V2,
    RequestType.REFRESH_SDK_DEVICE_CERTIFICATE,
    RequestType.GET_REGISTERED_TOOLS,
    RequestType.START_CONVERSATION_STREAM,
    RequestType.STOP_CONVERSATION_STREAM,
    RequestType.SPEAK_TEXT,
    RequestType.UNSPECIFIED,
]


class ErrorResponsePayload(_ErrorResponsePayloadBase[_FromRomiResponseRequestType]):
    """from_romi レスポンス共通のエラー payload。

    エラー時の構造は ``request_type`` 以外すべての API で同一のため単一の payload に
    集約する。許容する ``request_type`` は ``_FromRomiResponseRequestType`` を参照。
    トップレベルの ``ok`` discriminator により成功ユニオンと排他に振り分けられる。
    """


# --- 成功レスポンス（API ごとに data 型が異なるため個別に定義）-------------------


class DiscoverAvailableRomisResponsePayload(
    SuccessResponsePayload[
        Literal[RequestType.DISCOVER_AVAILABLE_ROMIS],
        DiscoverAvailableRomisResponseData,
    ]
): ...


class AddToolResponseSuccessPayload(
    SuccessResponsePayload[Literal[RequestType.ADD_TOOL], AddToolResponseData]
): ...


class RemoveToolResponseSuccessPayload(
    SuccessResponsePayload[Literal[RequestType.REMOVE_TOOL], RemoveToolResponseData]
): ...


class CreateRomiResponseSuccessPayload(
    SuccessResponsePayload[
        Literal[RequestType.CREATE_ROMI_RESPONSE], CreateRomiResponseResponseData
    ]
): ...


class CreateRomiResponseV2SuccessPayload(
    SuccessResponsePayload[
        Literal[RequestType.CREATE_ROMI_RESPONSE_V2], CreateRomiResponseResponseDataV2
    ]
): ...


class RefreshSdkDeviceCertificateResponseSuccessPayload(
    SuccessResponsePayload[
        Literal[RequestType.REFRESH_SDK_DEVICE_CERTIFICATE],
        RefreshSdkDeviceCertificateResponseData,
    ]
): ...


class GetRegisteredToolsResponseSuccessPayload(
    SuccessResponsePayload[
        Literal[RequestType.GET_REGISTERED_TOOLS], GetRegisteredToolsResponseData
    ]
): ...


class StartConversationStreamResponseSuccessPayload(
    SuccessResponsePayload[
        Literal[RequestType.START_CONVERSATION_STREAM],
        StartConversationStreamResponseData,
    ]
):
    data: Annotated[
        StartConversationStreamResponseData,
        Field(
            default_factory=StartConversationStreamResponseData,
            title="レスポンスデータ",
        ),
    ]


class StopConversationStreamResponseSuccessPayload(
    SuccessResponsePayload[
        Literal[RequestType.STOP_CONVERSATION_STREAM],
        StopConversationStreamResponseData,
    ]
):
    data: Annotated[
        StopConversationStreamResponseData,
        Field(
            default_factory=StopConversationStreamResponseData,
            title="レスポンスデータ",
        ),
    ]


class SpeakTextResponseSuccessPayload(
    SuccessResponsePayload[Literal[RequestType.SPEAK_TEXT], SpeakTextResponseData]
):
    data: Annotated[
        SpeakTextResponseData,
        Field(
            default_factory=SpeakTextResponseData,
            title="レスポンスデータ",
        ),
    ]


# 成功レスポンスは request_type で識別する。
FromRomiResponseSuccessPayload = Annotated[
    DiscoverAvailableRomisResponsePayload
    | AddToolResponseSuccessPayload
    | RemoveToolResponseSuccessPayload
    | CreateRomiResponseSuccessPayload
    | CreateRomiResponseV2SuccessPayload
    | RefreshSdkDeviceCertificateResponseSuccessPayload
    | GetRegisteredToolsResponseSuccessPayload
    | StartConversationStreamResponseSuccessPayload
    | StopConversationStreamResponseSuccessPayload
    | SpeakTextResponseSuccessPayload,
    Discriminator("request_type"),
]

# まず ok で成功/エラーを分け、成功側はさらに request_type で識別する。
FromRomiResponsePayload = Annotated[
    FromRomiResponseSuccessPayload | ErrorResponsePayload,
    Discriminator("ok"),
]

DEFAULT_FROM_ROMI_RESPONSE_ADAPTER = TypeAdapter(FromRomiResponsePayload)
