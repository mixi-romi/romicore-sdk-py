"""Python 標準型と Romi 向け Payload データクラスとを相互変換するコンバータ群。

``Romi`` クラスの公開メソッドは、利用者に pydantic ベースの Payload クラス
（``AddToolRequestData`` など）を直接構築・参照させるのではなく、str や int
といった標準型の引数を受け取り、標準ライブラリの dataclass（``results.py``）
を返す。ここに定義した関数群が、その標準型と実際に送受信する Payload
データクラスのインスタンスとの間の変換を担う。
"""

from .payload.event.data.requested_tool_call import RequestedToolCall
from .payload.event.data.conversation_streaming_event import (
    ConversationStreamingEventData,
)
from .payload.unicast.data.add_tool_request import (
    AddToolRequestData,
    ToolProperty,
    ToolSkill,
)
from .payload.unicast.data.remove_tool_request import RemoveToolRequestData
from .payload.unicast.data.create_romi_response_request import (
    CreateRomiResponseRequestData,
    RomiResponseUserUtterance,
)
from .payload.unicast.data.create_romi_response_response import (
    CreateRomiResponseResponseData,
    CreateRomiResponseResponseDataV2,
    CreateRomiResponseUtterance,
)
from .payload.unicast.data.refresh_sdk_device_certificate_request import (
    RefreshSdkDeviceCertificateRequestData,
)
from .payload.unicast.data.refresh_sdk_device_certificate_response import (
    RefreshSdkDeviceCertificateResponseData,
)
from .payload.unicast.data.get_registered_tools_request import (
    GetRegisteredToolsRequestData,
)
from .payload.unicast.data.get_resource_url_response import (
    GetResourceUrlResponseData,
)
from .payload.unicast.data.start_conversation_stream_request import (
    StartConversationStreamRequestData,
    ConversationSpeaker,
)
from .payload.unicast.data.stop_conversation_stream_request import (
    StopConversationStreamRequestData,
)
from .payload.unicast.data.speak_text_request import SpeakTextRequestData
from .payload.unicast.from_romi_request_payload import GetResourceUrlRequestPayload
from .payload.types import Emotion, Language
from .results import (
    ConversationStreamingEvent,
    ResourceUrlRequest,
    RomiResponse,
    RomiUtterance,
    SdkDeviceCertificate,
    ToolCall,
)


def build_add_tool_request_data(
    name: str,
    description: str,
    additional_base_instruction: str,
    additional_response_instruction: str,
    skill: str,
    parameters: str | None = None,
) -> AddToolRequestData:
    return AddToolRequestData(
        name=name,
        property=ToolProperty(
            description=description,
            parameters=parameters,
            additional_base_instruction=additional_base_instruction,
            additional_response_instruction=additional_response_instruction,
            skill=ToolSkill(skill),
        ),
    )


def build_remove_tool_request_data(name: str) -> RemoveToolRequestData:
    return RemoveToolRequestData(name=name)


def build_create_romi_response_request_data(
    instruction: str | None = None,
    user_utterance: str | None = None,
    should_include_user_utterance_in_conversation_log: bool = False,
) -> CreateRomiResponseRequestData:
    if user_utterance is None and should_include_user_utterance_in_conversation_log:
        raise ValueError(
            "should_include_user_utterance_in_conversation_log requires "
            "user_utterance to be set"
        )
    utterance_data = None
    if user_utterance is not None:
        utterance_data = RomiResponseUserUtterance(
            utterance=user_utterance,
            should_include_in_conversation_log=(
                should_include_user_utterance_in_conversation_log
            ),
        )
    return CreateRomiResponseRequestData(
        instruction=instruction,
        user_utterance=utterance_data,
    )


def build_refresh_sdk_device_certificate_request_data(
    csr: str,
) -> RefreshSdkDeviceCertificateRequestData:
    return RefreshSdkDeviceCertificateRequestData(csr=csr)


def build_get_registered_tools_request_data() -> GetRegisteredToolsRequestData:
    return GetRegisteredToolsRequestData()


def build_start_conversation_stream_request_data(
    speaker: str,
) -> StartConversationStreamRequestData:
    return StartConversationStreamRequestData(speaker=ConversationSpeaker(speaker))


def build_stop_conversation_stream_request_data() -> StopConversationStreamRequestData:
    return StopConversationStreamRequestData()


def build_speak_text_request_data(
    text: str,
    emotion: str,
    lang: str,
) -> SpeakTextRequestData:
    return SpeakTextRequestData(
        emotion=Emotion(emotion),
        lang=Language(lang),
        text=text,
    )


def to_tool_call(data: RequestedToolCall) -> ToolCall:
    return ToolCall(
        name=data.name,
        call_id=data.call_id,
        arguments_json=data.arguments_json,
    )


def to_conversation_streaming_event(
    data: ConversationStreamingEventData,
) -> ConversationStreamingEvent:
    return ConversationStreamingEvent(
        speaker=data.speaker.value,
        utterance_text=data.utterance_text,
        timestamp=data.timestamp,
    )


def to_romi_response(
    data: CreateRomiResponseResponseData | CreateRomiResponseResponseDataV2,
) -> RomiResponse:
    """create_romi_response のレスポンスを標準dataclassへ正規化する。

    v2 (CreateRomiResponseResponseDataV2) は常に utterances リストを持つ。
    v1 (CreateRomiResponseResponseData) は、通信相手のFWの世代によって
    utterances リストまたは text/emotion 単体のいずれかで届くため、
    両方の形状を吸収してリストへ揃える。
    """
    if isinstance(data, CreateRomiResponseResponseDataV2):
        utterances = data.utterances
    elif data.utterances is not None:
        utterances = data.utterances
    else:
        utterances = [
            CreateRomiResponseUtterance(text=data.text or "", emotion=data.emotion)
        ]
    return RomiResponse(
        utterances=[
            RomiUtterance(text=utterance.text, emotion=utterance.emotion)
            for utterance in utterances
        ]
    )


def to_sdk_device_certificate(
    data: RefreshSdkDeviceCertificateResponseData,
) -> SdkDeviceCertificate:
    return SdkDeviceCertificate(
        ca_chain=data.ca_chain,
        certificate=data.certificate,
    )


def to_resource_url_request(
    payload: GetResourceUrlRequestPayload,
) -> ResourceUrlRequest:
    return ResourceUrlRequest(
        request_id=payload.request_id,
        resource_id=payload.data.resource_id,
        resource_type=payload.data.resource_type.value,
        tool_name=payload.data.tool_name,
    )


def build_get_resource_url_response_data(
    resource_id: str,
    url: str,
) -> GetResourceUrlResponseData:
    return GetResourceUrlResponseData(resource_id=resource_id, url=url)
