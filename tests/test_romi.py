import pytest
import asyncio
from unittest.mock import AsyncMock, Mock

from romicoresdk.romi import Romi
from romicoresdk.capability_table import SDK_CAPABILITY_TABLE, SdkCapabilityTable
from romicoresdk.exceptions import CapabilityNotSupportedError, RomiCoreSdkError
from romicoresdk.payload.unicast.data.capability import (
    RomiCapability,
    CapabilityEntry,
    VersionDescriptor,
    CapabilityVersionState,
)
from romicoresdk.payload.request_type import RequestType
from romicoresdk.payload.unicast.data.add_tool_request import (
    AddToolRequestData,
    ToolProperty,
    ToolSkill,
)
from romicoresdk.payload.unicast.data.create_romi_response_request import (
    RomiResponseUserUtterance,
    CreateRomiResponseRequestData,
)
from romicoresdk.payload.unicast.data.create_romi_response_response import (
    CreateRomiResponseResponseData,
    CreateRomiResponseResponseDataV2,
    CreateRomiResponseUtterance,
)
from romicoresdk.payload.unicast.data.refresh_sdk_device_certificate_request import (
    RefreshSdkDeviceCertificateRequestData,
)
from romicoresdk.payload.unicast.data.refresh_sdk_device_certificate_response import (
    RefreshSdkDeviceCertificateResponseData,
)
from romicoresdk.payload.unicast.data.get_registered_tools_response import (
    GetRegisteredToolsResponseData,
)
from romicoresdk.payload.unicast.data.get_registered_tools_request import (
    GetRegisteredToolsRequestData,
)
from romicoresdk.payload.unicast.data.remove_tool_request import RemoveToolRequestData
from romicoresdk.payload.unicast.data.start_conversation_stream_request import (
    StartConversationStreamRequestData,
    ConversationSpeaker,
)
from romicoresdk.payload.unicast.data.stop_conversation_stream_request import (
    StopConversationStreamRequestData,
)
from romicoresdk.payload.event.data.requested_tool_call import (
    RequestedToolCall,
)
from romicoresdk.payload.unicast.data.get_resource_url_response import (
    GetResourceUrlResponseData,
)
from romicoresdk.payload.unicast.from_romi_request_payload import (
    GetResourceUrlRequestPayload,
)
from romicoresdk.payload.unicast.data.speak_text_request import (
    SpeakTextRequestData,
    Emotion,
    Language,
)
from romicoresdk.payload.error_info import ErrorInfo
from romicoresdk.payload.event.data.conversation_streaming_event import (
    ConversationStreamingEventData,
)
from romicoresdk.results import (
    ConversationStreamingEvent,
    ResourceUrlRequest,
    RomiResponse,
    RomiUtterance,
    SdkDeviceCertificate,
    ToolCall,
)


# 公開 API 全体をこの Romi が対応している状態を表すフィクスチャ。
# SDK 側のテーブルをそのまま広告することで、ネゴシエーション強制（_ensure_supported）
# を導入しても既存の振る舞いテストが全 API を呼び出せるようにする。
# 個別 API の未対応ケースは PARTIAL_CAPABILITY / capability=None のテストで扱う。
MOCK_CAPABILITY = RomiCapability(
    protocol_version=1,
    firmware_version="L.15.1.61",
    to_romi_request=SDK_CAPABILITY_TABLE.to_romi_request,
    resolved_from_romi_request=SDK_CAPABILITY_TABLE.from_romi_request,
)

# 一部 API のみ対応している Romi を表すフィクスチャ（未対応 API のガード検証用）。
# speak_text（to_romi_request）のみ対応し、他は広告しない。
PARTIAL_CAPABILITY = RomiCapability(
    protocol_version=1,
    firmware_version="L.15.1.61",
    to_romi_request=[
        CapabilityEntry(
            name="speak_text",
            versions=[
                VersionDescriptor(version="1", state=CapabilityVersionState.ACTIVE)
            ],
        )
    ],
    resolved_from_romi_request=[],
)


def test_romi_initialization() -> None:
    """Test that Romi can be initialized with device_id and sdk_id."""
    requester_mock = AsyncMock()
    responder_mock = AsyncMock()
    get_event_future_mock = Mock()
    get_request_future_mock = Mock()
    romi = Romi(
        model="romi-l01",
        serial_number="test_device",
        capability=MOCK_CAPABILITY,
        requester=requester_mock,
        responder=responder_mock,
        get_event_future=get_event_future_mock,
        get_request_future=get_request_future_mock,
    )
    assert romi.model == "romi-l01"
    assert romi.serial_number == "test_device"
    assert romi.id == "romi-l01-test_device"


@pytest.mark.asyncio
async def test_romi_add_tool() -> None:
    """Test that add_tool() can be called without errors."""
    requester_mock = AsyncMock()
    responder_mock = AsyncMock()
    get_event_future_mock = Mock()
    get_request_future_mock = Mock()
    romi = Romi(
        model="romi-l01",
        serial_number="test_device",
        capability=MOCK_CAPABILITY,
        requester=requester_mock,
        responder=responder_mock,
        get_event_future=get_event_future_mock,
        get_request_future=get_request_future_mock,
    )
    await romi.add_tool(
        name="test_func",
        description="This is an example tool.",
        additional_base_instruction="Use this tool to demonstrate the RomiCore SDK.",
        additional_response_instruction="Provide appropriate responses based on the tool.",
        skill=ToolSkill.NO_OPERATION.value,
    )

    expected_tool = AddToolRequestData(
        name="test_func",
        property=ToolProperty(
            description="This is an example tool.",
            parameters=None,
            additional_base_instruction="Use this tool to demonstrate the RomiCore SDK.",
            additional_response_instruction="Provide appropriate responses based on the tool.",
            skill=ToolSkill.NO_OPERATION,
        ),
    )
    requester_mock.assert_awaited_once_with(
        "romi-l01-test_device",
        RequestType.ADD_TOOL,
        expected_tool,
    )


@pytest.mark.asyncio
async def test_romi_wait_for_tool_call() -> None:
    """Test that wait_for_tool_call() returns RequestedToolCall."""
    requester_mock = AsyncMock()
    responder_mock = AsyncMock()
    # Mock get_event_future
    expected_data = RequestedToolCall(
        name="Example Tool",
        call_id="12345",
        arguments_json='{"param1": "value1"}',
    )
    future: asyncio.Future[RequestedToolCall] = asyncio.Future()
    future.set_result(expected_data)
    get_event_future_mock = Mock(return_value=future)
    get_request_future_mock = Mock()

    romi = Romi(
        model="romi-l01",
        serial_number="test_device",
        capability=MOCK_CAPABILITY,
        requester=requester_mock,
        responder=responder_mock,
        get_event_future=get_event_future_mock,
        get_request_future=get_request_future_mock,
    )
    result = await romi.wait_for_tool_call()
    assert isinstance(result, ToolCall)
    assert result.name == "Example Tool"
    assert result.call_id == "12345"
    assert result.arguments_json == '{"param1": "value1"}'


@pytest.mark.asyncio
async def test_romi_wait_for_conversation_streaming_event() -> None:
    """Test that wait_for_conversation_streaming_event() returns typed event data."""
    requester_mock = AsyncMock()
    responder_mock = AsyncMock()

    expected_data = ConversationStreamingEventData(
        speaker=ConversationSpeaker.ROMI,
        utterance_text="こんにちは",
        timestamp=1715060000,
    )
    future: asyncio.Future[ConversationStreamingEventData] = asyncio.Future()
    future.set_result(expected_data)
    get_event_future_mock = Mock(return_value=future)
    get_request_future_mock = Mock()

    romi = Romi(
        model="romi-l01",
        serial_number="test_device",
        capability=MOCK_CAPABILITY,
        requester=requester_mock,
        responder=responder_mock,
        get_event_future=get_event_future_mock,
        get_request_future=get_request_future_mock,
    )

    result = await romi.wait_for_conversation_streaming_event()

    assert isinstance(result, ConversationStreamingEvent)
    assert result.speaker == ConversationSpeaker.ROMI.value
    assert result.utterance_text == "こんにちは"
    assert result.timestamp == 1715060000


@pytest.mark.asyncio
async def test_romi_create_and_speak_response() -> None:
    """create_and_speak_response()はデフォルト(v1/v2双方対応のRomi)ではv2を
    ネゴシエートし、utterancesリストを返すこと。"""
    expected_response = CreateRomiResponseResponseDataV2(
        utterances=[
            CreateRomiResponseUtterance(
                text="Hello from Romi",
                emotion="neutral",
            ),
        ],
    )
    requester_mock = AsyncMock(return_value=expected_response)
    responder_mock = AsyncMock()
    get_event_future_mock = Mock()
    get_request_future_mock = Mock()
    romi = Romi(
        model="romi-l01",
        serial_number="test_device",
        capability=MOCK_CAPABILITY,
        requester=requester_mock,
        responder=responder_mock,
        get_event_future=get_event_future_mock,
        get_request_future=get_request_future_mock,
    )

    result = await romi.create_and_speak_response(
        instruction="This is an instruction for creating response.",
        user_utterance="This is user utterance",
        should_include_user_utterance_in_conversation_log=True,
    )

    expected_request = CreateRomiResponseRequestData(
        instruction="This is an instruction for creating response.",
        user_utterance=RomiResponseUserUtterance(
            utterance="This is user utterance",
            should_include_in_conversation_log=True,
        ),
    )
    # MOCK_CAPABILITYはSDK_CAPABILITY_TABLEを鏡写ししており、双方がv2まで
    # 対応しているためv2の request_type("_v2"サフィックス付き)が送信される。
    requester_mock.assert_awaited_once_with(
        "romi-l01-test_device",
        "create_romi_response_v2",
        expected_request,
    )
    assert result == RomiResponse(
        utterances=[RomiUtterance(text="Hello from Romi", emotion="neutral")]
    )


# 変更前(v1)のみを実装した旧FWを表すRomi capability。
# create_romi_response は v1 のみが active。
_V1_ONLY_CREATE_ROMI_RESPONSE_CAPABILITY = RomiCapability(
    protocol_version=1,
    firmware_version="L.15.1.60",
    to_romi_request=[
        CapabilityEntry(
            name="create_romi_response",
            versions=[
                VersionDescriptor(version="1", state=CapabilityVersionState.ACTIVE)
            ],
        )
    ],
    resolved_from_romi_request=[],
)


@pytest.mark.asyncio
async def test_romi_create_and_speak_response_v1_only_romi_uses_bare_request_type() -> (
    None
):
    """create_romi_response のv1のみ広告する旧FWとは、生名でリクエストし、
    text/emotion単体のレスポンスをそのまま受け取れること（後方互換）。"""
    expected_response = CreateRomiResponseResponseData(
        text="Hello from Romi", emotion="neutral"
    )
    requester_mock = AsyncMock(return_value=expected_response)
    romi = Romi(
        model="romi-l01",
        serial_number="test_device",
        capability=_V1_ONLY_CREATE_ROMI_RESPONSE_CAPABILITY,
        requester=requester_mock,
        responder=AsyncMock(),
        get_event_future=Mock(),
        get_request_future=Mock(),
    )

    result = await romi.create_and_speak_response(instruction="おはよう")

    requester_mock.assert_awaited_once_with(
        "romi-l01-test_device",
        "create_romi_response",
        CreateRomiResponseRequestData(instruction="おはよう"),
    )
    assert result == RomiResponse(
        utterances=[RomiUtterance(text="Hello from Romi", emotion="neutral")]
    )


@pytest.mark.asyncio
async def test_romi_create_and_speak_response_v1_negotiated_but_utterances_shape() -> (
    None
):
    """v1がネゴシエートされ生名で送信したにもかかわらず、移行期のFWから
    utterances形状で返ってきた場合でも、正しく正規化できること。

    (このFWはcreate_romi_responseをv1のみ広告しているが、実際のレスポンス
    形状は変更後(utterances)のままという移行期の組み合わせを想定している。)
    """
    expected_response = CreateRomiResponseResponseData(
        utterances=[
            CreateRomiResponseUtterance(text="おはよう！", emotion="joy"),
            CreateRomiResponseUtterance(text="今日の気分はどう？"),
        ]
    )
    requester_mock = AsyncMock(return_value=expected_response)
    romi = Romi(
        model="romi-l01",
        serial_number="test_device",
        capability=_V1_ONLY_CREATE_ROMI_RESPONSE_CAPABILITY,
        requester=requester_mock,
        responder=AsyncMock(),
        get_event_future=Mock(),
        get_request_future=Mock(),
    )

    result = await romi.create_and_speak_response(instruction="おはよう")

    requester_mock.assert_awaited_once_with(
        "romi-l01-test_device",
        "create_romi_response",
        CreateRomiResponseRequestData(instruction="おはよう"),
    )
    assert result == RomiResponse(
        utterances=[
            RomiUtterance(text="おはよう！", emotion="joy"),
            RomiUtterance(text="今日の気分はどう？", emotion=None),
        ]
    )


@pytest.mark.asyncio
async def test_romi_refresh_sdk_device_certificate() -> None:
    """Test that refresh_sdk_device_certificate() can be called without errors."""
    expected_response = RefreshSdkDeviceCertificateResponseData(
        ca_chain="-----BEGIN CERTIFICATE-----\nCA\n-----END CERTIFICATE-----",
        certificate="-----BEGIN CERTIFICATE-----\nCERT\n-----END CERTIFICATE-----",
    )
    requester_mock = AsyncMock(return_value=expected_response)
    responder_mock = AsyncMock()
    get_event_future_mock = Mock()
    get_request_future_mock = Mock()
    romi = Romi(
        model="romi-l01",
        serial_number="test_device",
        capability=MOCK_CAPABILITY,
        requester=requester_mock,
        responder=responder_mock,
        get_event_future=get_event_future_mock,
        get_request_future=get_request_future_mock,
    )

    csr = "-----BEGIN CERTIFICATE REQUEST-----\nTEST\n-----END CERTIFICATE REQUEST-----"
    result = await romi.refresh_sdk_device_certificate(csr)

    expected_request = RefreshSdkDeviceCertificateRequestData(csr=csr)
    requester_mock.assert_awaited_once_with(
        "romi-l01-test_device",
        RequestType.REFRESH_SDK_DEVICE_CERTIFICATE,
        expected_request,
    )
    assert result == SdkDeviceCertificate(
        ca_chain="-----BEGIN CERTIFICATE-----\nCA\n-----END CERTIFICATE-----",
        certificate="-----BEGIN CERTIFICATE-----\nCERT\n-----END CERTIFICATE-----",
    )


@pytest.mark.asyncio
async def test_romi_get_registered_tools() -> None:
    """Test that get_registered_tools() can be called without errors."""
    expected_response = GetRegisteredToolsResponseData(
        tool_names=["re_tool1", "re_tool2", "re_tool3"]
    )
    requester_mock = AsyncMock(return_value=expected_response)
    responder_mock = AsyncMock()
    get_event_future_mock = Mock()
    get_request_future_mock = Mock()
    romi = Romi(
        model="romi-l01",
        serial_number="test_device",
        capability=MOCK_CAPABILITY,
        requester=requester_mock,
        responder=responder_mock,
        get_event_future=get_event_future_mock,
        get_request_future=get_request_future_mock,
    )

    result = await romi.get_registered_tools()
    requester_mock.assert_awaited_once_with(
        "romi-l01-test_device",
        RequestType.GET_REGISTERED_TOOLS,
        GetRegisteredToolsRequestData(),
    )
    assert result == ["re_tool1", "re_tool2", "re_tool3"]


@pytest.mark.asyncio
async def test_romi_remove_tool() -> None:
    """Test that remove_tool() can be called without errors."""
    requester_mock = AsyncMock()
    responder_mock = AsyncMock()
    get_event_future_mock = Mock()
    get_request_future_mock = Mock()
    romi = Romi(
        model="romi-l01",
        serial_number="test_device",
        capability=MOCK_CAPABILITY,
        requester=requester_mock,
        responder=responder_mock,
        get_event_future=get_event_future_mock,
        get_request_future=get_request_future_mock,
    )

    await romi.remove_tool("target")

    requester_mock.assert_awaited_once_with(
        "romi-l01-test_device",
        RequestType.REMOVE_TOOL,
        RemoveToolRequestData(name="target"),
    )


@pytest.mark.asyncio
async def test_romi_start_conversation_stream() -> None:
    """Test that start_conversation_stream() can be called without errors."""
    requester_mock = AsyncMock(return_value=None)
    responder_mock = AsyncMock()
    get_event_future_mock = Mock()
    get_request_future_mock = Mock()
    romi = Romi(
        model="romi-l01",
        serial_number="test_device",
        capability=MOCK_CAPABILITY,
        requester=requester_mock,
        responder=responder_mock,
        get_event_future=get_event_future_mock,
        get_request_future=get_request_future_mock,
    )

    result = await romi.start_conversation_stream(
        speaker=ConversationSpeaker.ROMI.value
    )

    expected_request = StartConversationStreamRequestData(
        speaker=ConversationSpeaker.ROMI,
    )
    requester_mock.assert_awaited_once_with(
        "romi-l01-test_device",
        RequestType.START_CONVERSATION_STREAM,
        expected_request,
    )
    assert result is None


@pytest.mark.asyncio
async def test_romi_stop_conversation_stream() -> None:
    """Test that stop_conversation_stream() can be called without errors."""
    requester_mock = AsyncMock(return_value=None)
    responder_mock = AsyncMock()
    get_event_future_mock = Mock()
    get_request_future_mock = Mock()
    romi = Romi(
        model="romi-l01",
        serial_number="test_device",
        capability=MOCK_CAPABILITY,
        requester=requester_mock,
        responder=responder_mock,
        get_event_future=get_event_future_mock,
        get_request_future=get_request_future_mock,
    )

    result = await romi.stop_conversation_stream()
    requester_mock.assert_awaited_once_with(
        "romi-l01-test_device",
        RequestType.STOP_CONVERSATION_STREAM,
        StopConversationStreamRequestData(),
    )
    assert result is None


@pytest.mark.asyncio
async def test_romi_wait_for_get_resource_url_request() -> None:
    """Test that wait_for_get_resource_url_request() returns ResourceUrlRequest."""
    requester_mock = AsyncMock()
    responder_mock = AsyncMock()
    get_event_future_mock = Mock()

    # Mock get_request_future
    expected_payload = GetResourceUrlRequestPayload.model_validate(
        {
            "request_id": "req-001",
            "request_type": RequestType.GET_RESOURCE_URL,
            "data": {
                "resource_id": "res-001",
                "resource_type": "streaming_conversation_image_url",
            },
        }
    )
    future: asyncio.Future[GetResourceUrlRequestPayload] = asyncio.Future()
    future.set_result(expected_payload)
    get_request_future_mock = Mock(return_value=future)

    romi = Romi(
        model="romi-l01",
        serial_number="test_device",
        capability=MOCK_CAPABILITY,
        requester=requester_mock,
        responder=responder_mock,
        get_event_future=get_event_future_mock,
        get_request_future=get_request_future_mock,
    )

    result = await romi.wait_for_get_resource_url_request()
    assert isinstance(result, ResourceUrlRequest)
    assert result.request_id == "req-001"
    assert result.resource_id == "res-001"
    assert result.resource_type == "streaming_conversation_image_url"
    get_request_future_mock.assert_called_once_with(RequestType.GET_RESOURCE_URL)


@pytest.mark.asyncio
async def test_romi_respond_get_resource_url_success() -> None:
    """Test that respond_get_resource_url_success() calls responder correctly."""
    requester_mock = AsyncMock()
    responder_mock = AsyncMock()
    get_event_future_mock = Mock()
    get_request_future_mock = Mock()
    romi = Romi(
        model="romi-l01",
        serial_number="test_device",
        capability=MOCK_CAPABILITY,
        requester=requester_mock,
        responder=responder_mock,
        get_event_future=get_event_future_mock,
        get_request_future=get_request_future_mock,
    )

    await romi.respond_get_resource_url_success(
        request_id="req-001",
        resource_id="res-001",
        url="https://example.com/image.jpg",
    )

    responder_mock.assert_awaited_once_with(
        "romi-l01-test_device",
        "req-001",
        RequestType.GET_RESOURCE_URL,
        GetResourceUrlResponseData(
            resource_id="res-001",
            url="https://example.com/image.jpg",
        ),
        True,
        None,
    )


@pytest.mark.asyncio
async def test_romi_respond_get_resource_url_error() -> None:
    """Test that respond_get_resource_url_error() sends error response correctly."""
    requester_mock = AsyncMock()
    responder_mock = AsyncMock()
    get_event_future_mock = Mock()
    get_request_future_mock = Mock()
    romi = Romi(
        model="romi-l01",
        serial_number="test_device",
        capability=MOCK_CAPABILITY,
        requester=requester_mock,
        responder=responder_mock,
        get_event_future=get_event_future_mock,
        get_request_future=get_request_future_mock,
    )

    await romi.respond_get_resource_url_error(
        request_id="req-001", code="NOT_FOUND", message="Resource not found"
    )

    responder_mock.assert_awaited_once_with(
        "romi-l01-test_device",
        "req-001",
        RequestType.GET_RESOURCE_URL,
        None,
        False,
        ErrorInfo(code="NOT_FOUND", message="Resource not found"),
    )


@pytest.mark.asyncio
async def test_romi_speak_text_success() -> None:
    """Test that speak_text() can be called without errors."""
    requester_mock = AsyncMock()
    responder_mock = AsyncMock()
    get_event_future_mock = Mock()
    get_request_future_mock = Mock()
    romi = Romi(
        model="romi-l01",
        serial_number="test_device",
        capability=MOCK_CAPABILITY,
        requester=requester_mock,
        responder=responder_mock,
        get_event_future=get_event_future_mock,
        get_request_future=get_request_future_mock,
    )
    result = await romi.speak_text(
        text="こんにちはロミィだよ！",
        emotion=Emotion.NORMAL.value,
        lang=Language.JPN.value,
    )

    expected_request = SpeakTextRequestData(
        emotion=Emotion.NORMAL, lang=Language.JPN, text="こんにちはロミィだよ！"
    )
    requester_mock.assert_awaited_once_with(
        "romi-l01-test_device",
        RequestType.SPEAK_TEXT,
        expected_request,
    )
    assert result is None


# --- capability ネゴシエーション強制のテスト ---------------------------------


def _make_romi(capability: RomiCapability | None) -> Romi:
    """指定した capability で Romi を組み立てるテスト用ヘルパー。"""
    return Romi(
        model="romi-l01",
        serial_number="test_device",
        capability=capability,
        requester=AsyncMock(),
        responder=AsyncMock(),
        get_event_future=Mock(),
        get_request_future=Mock(),
    )


@pytest.mark.asyncio
async def test_unsupported_to_romi_request_raises() -> None:
    """未対応の SDK→Romi リクエスト API 呼び出しは例外を送出する。"""
    romi = _make_romi(PARTIAL_CAPABILITY)  # speak_text のみ対応
    with pytest.raises(CapabilityNotSupportedError) as exc_info:
        await romi.add_tool(
            name="test_func",
            description="dummy",
            additional_base_instruction="dummy",
            additional_response_instruction="dummy",
            skill=ToolSkill.NO_OPERATION.value,
        )
    assert exc_info.value.api == "add_tool"


@pytest.mark.asyncio
async def test_event_wait_not_gated_by_capability() -> None:
    """capability に広告されていないイベントでも待機できる。

    PARTIAL_CAPABILITY は tool_call_invoked を広告しないが、
    CapabilityNotSupportedError にはならず、イベント待機に進める。
    """
    expected_data = RequestedToolCall(
        name="Example Tool",
        call_id="12345",
        arguments_json='{"param1": "value1"}',
    )
    future: asyncio.Future[RequestedToolCall] = asyncio.Future()
    future.set_result(expected_data)

    romi = Romi(
        model="romi-l01",
        serial_number="test_device",
        capability=PARTIAL_CAPABILITY,  # tool_call_invoked は広告なし
        requester=AsyncMock(),
        responder=AsyncMock(),
        get_event_future=Mock(return_value=future),
        get_request_future=Mock(),
    )

    result = await romi.wait_for_tool_call()
    assert isinstance(result, ToolCall)
    assert result.name == "Example Tool"


@pytest.mark.asyncio
async def test_unsupported_from_romi_request_wait_raises() -> None:
    """未対応の Romi→SDK リクエスト待機は例外を送出する。"""
    romi = _make_romi(PARTIAL_CAPABILITY)  # get_resource_url は未対応
    with pytest.raises(CapabilityNotSupportedError) as exc_info:
        await romi.wait_for_get_resource_url_request()
    assert exc_info.value.api == "get_resource_url"


@pytest.mark.asyncio
async def test_unsupported_respond_raises() -> None:
    """未対応の Romi→SDK リクエストへのレスポンス送信も例外を送出する。"""
    romi = _make_romi(PARTIAL_CAPABILITY)  # get_resource_url は未対応
    with pytest.raises(CapabilityNotSupportedError):
        await romi.respond_get_resource_url_success(
            request_id="req-001",
            resource_id="res-001",
            url="https://example.com/image.jpg",
        )


@pytest.mark.asyncio
async def test_unsupported_respond_error_raises() -> None:
    """未対応の Romi→SDK リクエストへのエラーレスポンス送信も例外を送出する。"""
    romi = _make_romi(PARTIAL_CAPABILITY)  # get_resource_url は未対応
    with pytest.raises(CapabilityNotSupportedError):
        await romi.respond_get_resource_url_error(
            request_id="req-001",
            code="NOT_FOUND",
            message="Resource not found",
        )


@pytest.mark.asyncio
async def test_create_and_speak_response_flag_without_utterance_raises() -> None:
    """user_utterance 未指定で会話ログ包含フラグを立てると ValueError。"""
    romi = _make_romi(MOCK_CAPABILITY)
    with pytest.raises(ValueError):
        await romi.create_and_speak_response(
            instruction="朝のあいさつをしてください。",
            should_include_user_utterance_in_conversation_log=True,
        )


@pytest.mark.asyncio
async def test_supported_api_with_partial_capability_succeeds() -> None:
    """PARTIAL_CAPABILITY でも対応済み API（speak_text）は呼び出せる。"""
    requester_mock = AsyncMock()
    romi = Romi(
        model="romi-l01",
        serial_number="test_device",
        capability=PARTIAL_CAPABILITY,
        requester=requester_mock,
        responder=AsyncMock(),
        get_event_future=Mock(),
        get_request_future=Mock(),
    )
    await romi.speak_text(
        text="やあ", emotion=Emotion.NORMAL.value, lang=Language.JPN.value
    )
    requester_mock.assert_awaited_once_with(
        "romi-l01-test_device",
        RequestType.SPEAK_TEXT,
        SpeakTextRequestData(emotion=Emotion.NORMAL, lang=Language.JPN, text="やあ"),
    )


@pytest.mark.asyncio
async def test_capability_none_allows_all_apis() -> None:
    """capability 未対応の旧 FW（None）では従来どおり全 API を呼び出せる。"""
    requester_mock = AsyncMock()
    romi = Romi(
        model="romi-l01",
        serial_number="test_device",
        capability=None,
        requester=requester_mock,
        responder=AsyncMock(),
        get_event_future=Mock(),
        get_request_future=Mock(),
    )
    # ガードで例外にならず requester まで到達する
    await romi.speak_text(
        text="やあ", emotion=Emotion.NORMAL.value, lang=Language.JPN.value
    )
    requester_mock.assert_awaited_once()


def test_capability_not_supported_error_is_romi_sdk_error() -> None:
    """CapabilityNotSupportedError は RomiCoreSdkError のサブクラス。"""
    err = CapabilityNotSupportedError("add_tool")
    assert isinstance(err, RomiCoreSdkError)


# --- 解決した版がワイヤ request_type に反映されることのテスト ------------------

# SDK 側が speak_text の v1/v2 を実装している状態を表すテスト用テーブル。
# 実インスタンスの ClassVar を差し替えるためサブクラス化する。
_V2_SDK_CAPABILITY_TABLE = SdkCapabilityTable(
    to_romi_request=[
        CapabilityEntry(
            name="speak_text",
            versions=[
                VersionDescriptor(version="1", state=CapabilityVersionState.ACTIVE),
                VersionDescriptor(version="2", state=CapabilityVersionState.ACTIVE),
            ],
        ),
    ],
)


class _V2Romi(Romi):
    """v2 を実装した SDK テーブルを持つ Romi（テスト専用）。"""

    _sdk_capability_table = _V2_SDK_CAPABILITY_TABLE


# SDK/Romi の双方が speak_text の v2 まで対応している状態。
_V2_CAPABILITY = RomiCapability(
    protocol_version=1,
    firmware_version="L.15.1.61",
    to_romi_request=_V2_SDK_CAPABILITY_TABLE.to_romi_request,
    resolved_from_romi_request=[],
)


@pytest.mark.asyncio
async def test_resolved_v2_encodes_wire_request_type() -> None:
    """解決版が v2 のとき、送信 request_type が "speak_text_v2" に符号化される。"""
    requester_mock = AsyncMock()
    romi = _V2Romi(
        model="romi-l01",
        serial_number="test_device",
        capability=_V2_CAPABILITY,
        requester=requester_mock,
        responder=AsyncMock(),
        get_event_future=Mock(),
        get_request_future=Mock(),
    )
    await romi.speak_text(
        text="やあ", emotion=Emotion.NORMAL.value, lang=Language.JPN.value
    )
    requester_mock.assert_awaited_once_with(
        "romi-l01-test_device",
        "speak_text_v2",
        SpeakTextRequestData(emotion=Emotion.NORMAL, lang=Language.JPN, text="やあ"),
    )


@pytest.mark.asyncio
async def test_resolved_v1_uses_bare_wire_request_type() -> None:
    """解決版が v1 のとき、送信 request_type は従来どおり生名（後方互換）。"""
    requester_mock = AsyncMock()
    romi = Romi(
        model="romi-l01",
        serial_number="test_device",
        capability=MOCK_CAPABILITY,
        requester=requester_mock,
        responder=AsyncMock(),
        get_event_future=Mock(),
        get_request_future=Mock(),
    )
    await romi.speak_text(
        text="やあ", emotion=Emotion.NORMAL.value, lang=Language.JPN.value
    )
    requester_mock.assert_awaited_once_with(
        "romi-l01-test_device",
        "speak_text",
        SpeakTextRequestData(emotion=Emotion.NORMAL, lang=Language.JPN, text="やあ"),
    )


@pytest.mark.asyncio
async def test_baseline_uses_bare_wire_request_type() -> None:
    """capability 未広告の旧 FW（None）でも送信 request_type は生名。"""
    requester_mock = AsyncMock()
    romi = _V2Romi(
        model="romi-l01",
        serial_number="test_device",
        capability=None,
        requester=requester_mock,
        responder=AsyncMock(),
        get_event_future=Mock(),
        get_request_future=Mock(),
    )
    await romi.speak_text(
        text="やあ", emotion=Emotion.NORMAL.value, lang=Language.JPN.value
    )
    requester_mock.assert_awaited_once_with(
        "romi-l01-test_device",
        "speak_text",
        SpeakTextRequestData(emotion=Emotion.NORMAL, lang=Language.JPN, text="やあ"),
    )
