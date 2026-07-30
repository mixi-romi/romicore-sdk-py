from pydantic import Discriminator, TypeAdapter
from typing import Annotated, Literal

from ..request_type import RequestType
from ..generic_payload import RequestPayload
from .data.add_tool_request import AddToolRequestData
from .data.remove_tool_request import RemoveToolRequestData
from .data.create_romi_response_request import CreateRomiResponseRequestData
from .data.refresh_sdk_device_certificate_request import (
    RefreshSdkDeviceCertificateRequestData,
)
from .data.get_registered_tools_request import GetRegisteredToolsRequestData
from .data.start_conversation_stream_request import StartConversationStreamRequestData
from .data.stop_conversation_stream_request import StopConversationStreamRequestData
from .data.speak_text_request import SpeakTextRequestData


class AddToolRequestPayload(
    RequestPayload[Literal[RequestType.ADD_TOOL], AddToolRequestData]
): ...


class CreateRomiResponseRequestPayload(
    RequestPayload[
        Literal[RequestType.CREATE_ROMI_RESPONSE], CreateRomiResponseRequestData
    ]
): ...


class CreateRomiResponseV2RequestPayload(
    RequestPayload[
        Literal[RequestType.CREATE_ROMI_RESPONSE_V2], CreateRomiResponseRequestData
    ]
):
    """create_romi_response v2。リクエストの形状はv1と同一で、
    レスポンス側のみutterancesリストへ変わる。"""


class RemoveToolRequestPayload(
    RequestPayload[Literal[RequestType.REMOVE_TOOL], RemoveToolRequestData]
): ...


class RefreshSdkDeviceCertificateRequestPayload(
    RequestPayload[
        Literal[RequestType.REFRESH_SDK_DEVICE_CERTIFICATE],
        RefreshSdkDeviceCertificateRequestData,
    ]
): ...


class GetRegisteredToolsRequestPayload(
    RequestPayload[
        Literal[RequestType.GET_REGISTERED_TOOLS], GetRegisteredToolsRequestData
    ]
): ...


class StartConversationStreamRequestPayload(
    RequestPayload[
        Literal[RequestType.START_CONVERSATION_STREAM],
        StartConversationStreamRequestData,
    ]
): ...


class StopConversationStreamRequestPayload(
    RequestPayload[
        Literal[RequestType.STOP_CONVERSATION_STREAM],
        StopConversationStreamRequestData,
    ]
): ...


class SpeakTextRequestPayload(
    RequestPayload[Literal[RequestType.SPEAK_TEXT], SpeakTextRequestData]
): ...


ToRomiRequestPayload = Annotated[
    AddToolRequestPayload
    | RemoveToolRequestPayload
    | CreateRomiResponseRequestPayload
    | CreateRomiResponseV2RequestPayload
    | RefreshSdkDeviceCertificateRequestPayload
    | GetRegisteredToolsRequestPayload
    | StartConversationStreamRequestPayload
    | StopConversationStreamRequestPayload
    | SpeakTextRequestPayload,
    Discriminator("request_type"),
]

DEFAULT_TO_ROMI_REQUEST_ADAPTER = TypeAdapter(ToRomiRequestPayload)
