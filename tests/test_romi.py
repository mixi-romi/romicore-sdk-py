import pytest
import asyncio
from unittest.mock import AsyncMock, Mock

from romicoresdk.romi import Romi
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
from romicoresdk.payload.unicast.data.get_resource_url_request import (
    ResourceType,
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
from romicoresdk.requests.get_resource_url import (
    GetResourceUrlRequest,
)
from romicoresdk.payload.error_info import ErrorInfo
from romicoresdk.payload.event.data.conversation_streaming_event import (
    ConversationStreamingEventData,
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
        requester=requester_mock,
        responder=responder_mock,
        get_event_future=get_event_future_mock,
        get_request_future=get_request_future_mock,
    )
    tool_prop = ToolProperty(
        description="This is an example tool.",
        parameters=None,
        additional_base_instruction="Use this tool to demonstrate the RomiCore SDK.",
        additional_response_instruction="Provide appropriate responses based on the tool.",
        skill=ToolSkill.NO_OPERATION,
    )
    tool = AddToolRequestData(name="test_func", property=tool_prop)
    await romi.add_tool(tool)
    requester_mock.assert_awaited_once_with(
        "romi-l01-test_device",
        RequestType.ADD_TOOL,
        tool,
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
        requester=requester_mock,
        responder=responder_mock,
        get_event_future=get_event_future_mock,
        get_request_future=get_request_future_mock,
    )
    result = await romi.wait_for_tool_call()
    assert isinstance(result, RequestedToolCall)
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
        requester=requester_mock,
        responder=responder_mock,
        get_event_future=get_event_future_mock,
        get_request_future=get_request_future_mock,
    )

    result = await romi.wait_for_conversation_streaming_event()

    assert isinstance(result, ConversationStreamingEventData)
    assert result.speaker == ConversationSpeaker.ROMI
    assert result.utterance_text == "こんにちは"
    assert result.timestamp == 1715060000


@pytest.mark.asyncio
async def test_romi_create_and_speak_response() -> None:
    """Test that create_and_speak_response() can be called without errors."""
    expected_response = CreateRomiResponseResponseData(
        text="Hello from Romi",
        emotion="neutral",
    )
    requester_mock = AsyncMock(return_value=expected_response)
    responder_mock = AsyncMock()
    get_event_future_mock = Mock()
    get_request_future_mock = Mock()
    romi = Romi(
        model="romi-l01",
        serial_number="test_device",
        requester=requester_mock,
        responder=responder_mock,
        get_event_future=get_event_future_mock,
        get_request_future=get_request_future_mock,
    )

    user_utterance = RomiResponseUserUtterance(
        utterance="This is user utterance",
        should_include_in_conversation_log=True,
    )

    response_data = CreateRomiResponseRequestData(
        instruction="This is an instruction for creating response.",
        user_utterance=user_utterance,
    )

    result = await romi.create_and_speak_response(response_data)
    requester_mock.assert_awaited_once_with(
        "romi-l01-test_device",
        RequestType.CREATE_ROMI_RESPONSE,
        response_data,
    )
    assert result == expected_response


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
        requester=requester_mock,
        responder=responder_mock,
        get_event_future=get_event_future_mock,
        get_request_future=get_request_future_mock,
    )

    certificate_request = RefreshSdkDeviceCertificateRequestData(
        csr="-----BEGIN CERTIFICATE REQUEST-----\nTEST\n-----END CERTIFICATE REQUEST-----"
    )

    result = await romi.refresh_sdk_device_certificate(certificate_request)
    requester_mock.assert_awaited_once_with(
        "romi-l01-test_device",
        RequestType.REFRESH_SDK_DEVICE_CERTIFICATE,
        certificate_request,
    )
    assert result == expected_response


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
    assert result == expected_response


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
        requester=requester_mock,
        responder=responder_mock,
        get_event_future=get_event_future_mock,
        get_request_future=get_request_future_mock,
    )

    request = StartConversationStreamRequestData(
        speaker=ConversationSpeaker.ROMI,
    )

    result = await romi.start_conversation_stream(request)
    requester_mock.assert_awaited_once_with(
        "romi-l01-test_device",
        RequestType.START_CONVERSATION_STREAM,
        request,
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
    """Test that wait_for_get_resource_url_request() returns GetResourceUrlRequest."""
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
        requester=requester_mock,
        responder=responder_mock,
        get_event_future=get_event_future_mock,
        get_request_future=get_request_future_mock,
    )

    result = await romi.wait_for_get_resource_url_request()
    assert isinstance(result, GetResourceUrlRequest)
    assert result.resource_id == "res-001"
    assert result.resource_type == ResourceType.STREAMING_CONVERSATION_IMAGE_URL
    get_request_future_mock.assert_called_once_with(RequestType.GET_RESOURCE_URL)


@pytest.mark.asyncio
async def test_romi_respond_get_resource_url() -> None:
    """Test that respond_get_resource_url() calls responder with correct arguments."""
    requester_mock = AsyncMock()
    responder_mock = AsyncMock()
    get_event_future_mock = Mock()
    get_request_future_mock = Mock()
    romi = Romi(
        model="romi-l01",
        serial_number="test_device",
        requester=requester_mock,
        responder=responder_mock,
        get_event_future=get_event_future_mock,
        get_request_future=get_request_future_mock,
    )

    request = GetResourceUrlRequest(
        GetResourceUrlRequestPayload.model_validate(
            {
                "request_id": "req-001",
                "request_type": RequestType.GET_RESOURCE_URL,
                "data": {
                    "resource_id": "res-001",
                    "resource_type": "streaming_conversation_image_url",
                },
            }
        )
    )
    response = request.create_success_response(url="https://example.com/image.jpg")

    await romi.respond_get_resource_url(response)

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
    """Test that respond_get_resource_url() sends error response correctly."""
    requester_mock = AsyncMock()
    responder_mock = AsyncMock()
    get_event_future_mock = Mock()
    get_request_future_mock = Mock()
    romi = Romi(
        model="romi-l01",
        serial_number="test_device",
        requester=requester_mock,
        responder=responder_mock,
        get_event_future=get_event_future_mock,
        get_request_future=get_request_future_mock,
    )

    request = GetResourceUrlRequest(
        GetResourceUrlRequestPayload.model_validate(
            {
                "request_id": "req-001",
                "request_type": RequestType.GET_RESOURCE_URL,
                "data": {
                    "resource_id": "res-001",
                    "resource_type": "streaming_conversation_image_url",
                },
            }
        )
    )
    error = ErrorInfo(code="NOT_FOUND", message="Resource not found")
    response = request.create_error_response(error=error)

    await romi.respond_get_resource_url(response)

    responder_mock.assert_awaited_once_with(
        "romi-l01-test_device",
        "req-001",
        RequestType.GET_RESOURCE_URL,
        None,
        False,
        error,
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
        requester=requester_mock,
        responder=responder_mock,
        get_event_future=get_event_future_mock,
        get_request_future=get_request_future_mock,
    )
    request = SpeakTextRequestData(
        emotion=Emotion.NORMAL, lang=Language.JPN, text="こんにちはロミィだよ！"
    )
    result = await romi.speak_text(request)
    requester_mock.assert_awaited_once_with(
        "romi-l01-test_device",
        RequestType.SPEAK_TEXT,
        request,
    )
    assert result is None
