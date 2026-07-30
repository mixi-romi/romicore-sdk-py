import pytest
import json
import asyncio
import tempfile

from romicoresdk import SDK
from romicoresdk.romi import Romi
from romicoresdk.sdk import SDK_PROTOCOL_VERSION
from .mock.mqtt_mock import MqttMock
from romicoresdk.payload.request_type import RequestType
from romicoresdk.payload.error_info import ErrorInfo
from romicoresdk.payload.unicast.data.get_resource_url_response import (
    GetResourceUrlResponseData,
)
from romicoresdk.payload.unicast.data.start_conversation_stream_request import (
    StartConversationStreamRequestData,
    ConversationSpeaker,
)
from romicoresdk.payload.unicast.data.stop_conversation_stream_request import (
    StopConversationStreamRequestData,
)
from romicoresdk import ToolSkill
from romicoresdk.payload.unicast.data.add_tool_request import (
    AddToolRequestData,
    ToolProperty,
)
from romicoresdk.payload.unicast.data.remove_tool_request import RemoveToolRequestData
from romicoresdk.payload.event.data.requested_tool_call import RequestedToolCall
from unittest.mock import call
from romicoresdk.payload.event.event_payload import EventType
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography import x509

HOST = "127.0.0.1"
BROKER_PORT = 443


def test_sdk_initialization_with_certs_dir(tmp_path) -> None:
    """Test SDK initialization with certificates directory."""
    certs_dir = tmp_path / "certs"
    sdk = SDK.create(HOST, BROKER_PORT, certs_dir=certs_dir, mqtt_client_class=MqttMock)
    assert sdk._tls_config.ca_certs_path == str(certs_dir / "ca.crt")
    assert sdk._tls_config.client_certfile_path == str(certs_dir / "client.crt")
    assert sdk._tls_config.client_keyfile_path == str(certs_dir / "client.key")


@pytest.mark.asyncio
async def test_sdk_connect(monkeypatch, tmp_path) -> None:
    """Test that SDK.connect() calls the MQTT client's connect method."""
    monkeypatch.setattr("romicoresdk.sdk.generate_sdk_id", lambda: "py-sdk-testid")
    sdk = SDK.create(HOST, BROKER_PORT, certs_dir=tmp_path, mqtt_client_class=MqttMock)
    assert isinstance(sdk._mqtt_client, MqttMock)
    await sdk.connect()
    sdk._mqtt_client.connect.assert_awaited_once()
    expected_calls = [
        call(
            topic="romicoresdk/+/py-sdk-testid/from_romi/response",
            message_handler=sdk._on_message_response,
            qos=1,
        ),
        call(
            topic="romicoresdk/+/py-sdk-testid/from_romi/request",
            message_handler=sdk._on_message_request,
            qos=1,
        ),
        call(
            topic="romicoresdk/+/event",
            message_handler=sdk._on_message_event,
            qos=1,
        ),
    ]
    sdk._mqtt_client.subscribe.assert_has_awaits(expected_calls)
    assert sdk._mqtt_client.subscribe.await_count == 3


@pytest.mark.asyncio
async def test_discover_romis_returns_list(monkeypatch, tmp_path) -> None:
    """Test that discover_romis() returns a list of Romi objects."""
    monkeypatch.setattr("romicoresdk.sdk.generate_sdk_id", lambda: "py-sdk-testid")

    sdk = SDK.create(HOST, BROKER_PORT, certs_dir=tmp_path, mqtt_client_class=MqttMock)
    assert isinstance(sdk._mqtt_client, MqttMock)

    async def fake_response(timeout: int) -> None:
        payload = {
            "request_id": "py-sdk-testid-0",
            "request_type": "discover_available_romis",
            "ok": True,
            "error": {"code": "", "message": ""},
            "data": {
                "model": "romi-l01",
                "serial_number": "0000000063",
                "capability": {
                    "protocol_version": 1,
                    "firmware_version": "L.15.1.61",
                    "to_romi_request": [
                        {
                            "name": "speak_text",
                            "versions": [{"version": "1", "state": "active"}],
                        }
                    ],
                    "resolved_from_romi_request": [
                        {
                            "name": "get_resource_url",
                            "versions": [{"version": "1", "state": "active"}],
                            "response_timeout_ms": 5000,
                        }
                    ],
                },
            },
        }
        await sdk._on_message_response(
            topic="romicoresdk/romi-l01-0000000063/py-sdk-testid/from_romi/response",
            payload=json.dumps(payload),
        )

    monkeypatch.setattr("romicoresdk.sdk.asyncio.sleep", fake_response)

    romis = await sdk.discover_romis(10)
    call = sdk._mqtt_client.publish.await_args
    assert call.kwargs["topic"] == "romicoresdk/broadcast/py-sdk-testid/request"
    actual_payload = json.loads(call.kwargs["payload"])

    # discover リクエストには SDK の capability 申告（from_romi_request）が載る。
    assert actual_payload["request_id"] == "py-sdk-testid-0"
    assert actual_payload["request_type"] == "discover_available_romis"
    capability = actual_payload["data"]["capability"]
    assert capability["protocol_version"] == SDK_PROTOCOL_VERSION
    declared_from_romi = {entry["name"] for entry in capability["from_romi_request"]}
    assert "get_resource_url" in declared_from_romi

    assert isinstance(romis, list)
    assert len(romis) > 0
    assert all(isinstance(romi, Romi) for romi in romis)


def test_sdk_capability_declaration_serialization() -> None:
    """SdkCapabilityDeclaration が discover 申告のワイヤ形式へ直列化される。"""
    from romicoresdk.payload.broadcast.data.discover_available_romis_request import (
        SdkCapabilityDeclaration,
    )
    from romicoresdk.payload.unicast.data.capability import (
        CapabilityEntry,
        CapabilityVersionState,
        VersionDescriptor,
    )

    declaration = SdkCapabilityDeclaration(
        protocol_version=1,
        sdk_version="9.9.9",
        from_romi_request=[
            CapabilityEntry(
                name="get_resource_url",
                versions=[
                    VersionDescriptor(version="1", state=CapabilityVersionState.ACTIVE)
                ],
            )
        ],
    )

    dumped = declaration.model_dump(mode="json")
    assert dumped["protocol_version"] == 1
    assert dumped["sdk_version"] == "9.9.9"
    assert dumped["from_romi_request"][0]["name"] == "get_resource_url"
    assert dumped["from_romi_request"][0]["versions"] == [
        {"version": "1", "state": "active", "sunset": None}
    ]


def test_sdk_capability_declaration_defaults() -> None:
    """protocol_version/sdk_version は既定値を持ち、from_romi_request は空可。"""
    from romicoresdk.payload.broadcast.data.discover_available_romis_request import (
        SdkCapabilityDeclaration,
    )

    declaration = SdkCapabilityDeclaration()
    assert declaration.protocol_version == 1
    assert declaration.sdk_version is None
    assert declaration.from_romi_request == []


@pytest.mark.asyncio
async def test__send_unicast_request(monkeypatch, tmp_path) -> None:
    """Test that _send_unicast_request() sends the correct MQTT message."""
    monkeypatch.setattr("romicoresdk.sdk.generate_sdk_id", lambda: "py-sdk-testid")

    sdk = SDK.create(HOST, BROKER_PORT, certs_dir=tmp_path, mqtt_client_class=MqttMock)
    assert isinstance(sdk._mqtt_client, MqttMock)

    # Mock asyncio.wait_for
    async def fake_response(fut: asyncio.Future, timeout: float) -> None:
        payload = {
            "request_id": "py-sdk-testid-0",
            "request_type": "add_tool",
            "ok": True,
            "error": {"code": "", "message": ""},
            "data": {},
        }
        await sdk._on_message_response(
            topic="romicoresdk/romi-l01-0000000063/py-sdk-testid/from_romi/response",
            payload=json.dumps(payload),
        )

    monkeypatch.setattr("romicoresdk.sdk.asyncio.wait_for", fake_response)

    # payload for the request
    romi_id = "romi-l01-0000000063"
    request_type = RequestType.ADD_TOOL
    tool_prop = ToolProperty(
        description="This is an example tool.",
        parameters=None,
        additional_base_instruction="Use this tool to demonstrate the RomiCore SDK.",
        additional_response_instruction="Provide appropriate responses based on the tool.",
        skill=ToolSkill.NO_OPERATION,
    )
    tool = AddToolRequestData(
        name="Example Tool",
        property=tool_prop,
    )

    await sdk._send_unicast_request(romi_id, request_type, tool)

    call = sdk._mqtt_client.publish.await_args
    assert (
        call.kwargs["topic"] == f"romicoresdk/{romi_id}/py-sdk-testid/to_romi/request"
    )
    actual_payload = json.loads(call.kwargs["payload"])
    expected_payload = {
        "request_id": "py-sdk-testid-0",
        "request_type": request_type.value,
        "data": tool.model_dump(mode="json", exclude_none=True),
    }
    assert actual_payload == expected_payload


@pytest.mark.asyncio
async def test__send_unicast_request_start_conversation_stream(
    monkeypatch, tmp_path
) -> None:
    """Test that _send_unicast_request() sends start_conversation_stream."""
    monkeypatch.setattr("romicoresdk.sdk.generate_sdk_id", lambda: "py-sdk-testid")

    sdk = SDK.create(HOST, BROKER_PORT, certs_dir=tmp_path, mqtt_client_class=MqttMock)
    assert isinstance(sdk._mqtt_client, MqttMock)

    async def fake_response(fut: asyncio.Future, timeout: float) -> None:
        payload = {
            "request_id": "py-sdk-testid-0",
            "request_type": "start_conversation_stream",
            "ok": True,
            "error": {"code": "", "message": ""},
            "data": {},
        }
        await sdk._on_message_response(
            topic="romicoresdk/romi-l01-0000000063/py-sdk-testid/from_romi/response",
            payload=json.dumps(payload),
        )

    monkeypatch.setattr("romicoresdk.sdk.asyncio.wait_for", fake_response)

    romi_id = "romi-l01-0000000063"
    request_type = RequestType.START_CONVERSATION_STREAM
    request = StartConversationStreamRequestData(
        speaker=ConversationSpeaker.ROMI,
    )

    await sdk._send_unicast_request(romi_id, request_type, request)

    call = sdk._mqtt_client.publish.await_args
    assert (
        call.kwargs["topic"] == f"romicoresdk/{romi_id}/py-sdk-testid/to_romi/request"
    )
    actual_payload = json.loads(call.kwargs["payload"])
    expected_payload = {
        "request_id": "py-sdk-testid-0",
        "request_type": request_type.value,
        "data": request.model_dump(mode="json", exclude_none=True),
    }
    assert actual_payload == expected_payload


@pytest.mark.asyncio
async def test__send_unicast_request_stop_conversation_stream(
    monkeypatch, tmp_path
) -> None:
    """Test that _send_unicast_request() sends stop_conversation_stream."""
    monkeypatch.setattr("romicoresdk.sdk.generate_sdk_id", lambda: "py-sdk-testid")

    sdk = SDK.create(HOST, BROKER_PORT, certs_dir=tmp_path, mqtt_client_class=MqttMock)
    assert isinstance(sdk._mqtt_client, MqttMock)

    async def fake_response(fut: asyncio.Future, timeout: float) -> None:
        payload = {
            "request_id": "py-sdk-testid-0",
            "request_type": "stop_conversation_stream",
            "ok": True,
            "error": {"code": "", "message": ""},
            "data": {},
        }
        await sdk._on_message_response(
            topic="romicoresdk/romi-l01-0000000063/py-sdk-testid/from_romi/response",
            payload=json.dumps(payload),
        )

    monkeypatch.setattr("romicoresdk.sdk.asyncio.wait_for", fake_response)

    romi_id = "romi-l01-0000000063"
    request_type = RequestType.STOP_CONVERSATION_STREAM
    request = StopConversationStreamRequestData()

    await sdk._send_unicast_request(romi_id, request_type, request)

    call = sdk._mqtt_client.publish.await_args
    assert (
        call.kwargs["topic"] == f"romicoresdk/{romi_id}/py-sdk-testid/to_romi/request"
    )
    actual_payload = json.loads(call.kwargs["payload"])
    expected_payload = {
        "request_id": "py-sdk-testid-0",
        "request_type": request_type.value,
        "data": request.model_dump(mode="json", exclude_none=True),
    }
    assert actual_payload == expected_payload


@pytest.mark.asyncio
async def test__send_unicast_request_error(monkeypatch, tmp_path) -> None:
    """Test that _send_unicast_request() sends the correct MQTT message."""
    monkeypatch.setattr("romicoresdk.sdk.generate_sdk_id", lambda: "py-sdk-testid")

    sdk = SDK.create(HOST, BROKER_PORT, certs_dir=tmp_path, mqtt_client_class=MqttMock)
    assert isinstance(sdk._mqtt_client, MqttMock)

    # Mock asyncio.wait_for
    async def fake_response(fut: asyncio.Future, timeout: float) -> None:
        payload = {
            "request_id": "py-sdk-testid-0",
            "request_type": "add_tool",
            "ok": False,
            "error": {
                "code": "INVALID_ARGUMENT",
                "message": "property.description is required",
            },
            "data": {},
        }
        await sdk._on_message_response(
            topic="romicoresdk/romi-l01-0000000063/py-sdk-testid/from_romi/response",
            payload=json.dumps(payload),
        )

    monkeypatch.setattr("romicoresdk.sdk.asyncio.wait_for", fake_response)

    # payload for the request
    romi_id = "romi-l01-0000000063"
    request_type = RequestType.ADD_TOOL
    tool_prop = ToolProperty(
        description="This is an example tool.",
        parameters=None,
        additional_base_instruction="Use this tool to demonstrate the RomiCore SDK.",
        additional_response_instruction="Provide appropriate responses based on the tool.",
        skill=ToolSkill.NO_OPERATION,
    )
    tool = AddToolRequestData(
        name="Example Tool",
        property=tool_prop,
    )

    with pytest.raises(
        RuntimeError,
        match="Romi romi-l01-0000000063 returned error: INVALID_ARGUMENT - property.description is required",
    ):
        await sdk._send_unicast_request(romi_id, request_type, tool)


@pytest.mark.asyncio
async def test__send_unicast_request_error_unspecified(monkeypatch, tmp_path) -> None:
    """Romi がリクエストの payload パースに失敗し request_type を特定できず
    ``unspecified`` のエラーレスポンスを返した場合でも、pending future が解決され
    呼び出し側にエラーが伝播することを検証する。"""
    monkeypatch.setattr("romicoresdk.sdk.generate_sdk_id", lambda: "py-sdk-testid")

    sdk = SDK.create(HOST, BROKER_PORT, certs_dir=tmp_path, mqtt_client_class=MqttMock)
    assert isinstance(sdk._mqtt_client, MqttMock)

    async def fake_response(fut: asyncio.Future, timeout: float) -> None:
        payload = {
            "request_id": "py-sdk-testid-0",
            "request_type": "unspecified",
            "ok": False,
            "error": {
                "code": "INVALID_ARGUMENT",
                "message": "failed to parse request payload",
            },
        }
        await sdk._on_message_response(
            topic="romicoresdk/romi-l01-0000000063/py-sdk-testid/from_romi/response",
            payload=json.dumps(payload),
        )

    monkeypatch.setattr("romicoresdk.sdk.asyncio.wait_for", fake_response)

    romi_id = "romi-l01-0000000063"
    request_type = RequestType.ADD_TOOL
    tool_prop = ToolProperty(
        description="This is an example tool.",
        parameters=None,
        additional_base_instruction="Use this tool to demonstrate the RomiCore SDK.",
        additional_response_instruction="Provide appropriate responses based on the tool.",
        skill=ToolSkill.NO_OPERATION,
    )
    tool = AddToolRequestData(
        name="Example Tool",
        property=tool_prop,
    )

    with pytest.raises(
        RuntimeError,
        match="Romi romi-l01-0000000063 returned error: INVALID_ARGUMENT - failed to parse request payload",
    ):
        await sdk._send_unicast_request(romi_id, request_type, tool)


@pytest.mark.asyncio
async def test__send_unicast_request_remove_tool(monkeypatch, tmp_path) -> None:
    """Test that remove_tool request is serialized and sent correctly."""
    monkeypatch.setattr("romicoresdk.sdk.generate_sdk_id", lambda: "py-sdk-testid")

    sdk = SDK.create(HOST, BROKER_PORT, certs_dir=tmp_path, mqtt_client_class=MqttMock)
    assert isinstance(sdk._mqtt_client, MqttMock)

    async def fake_response(fut: asyncio.Future, timeout: float) -> None:
        payload = {
            "request_id": "py-sdk-testid-0",
            "request_type": "remove_tool",
            "ok": True,
            "error": {"code": "", "message": ""},
            "data": {},
        }
        await sdk._on_message_response(
            topic="romicoresdk/romi-l01-0000000063/py-sdk-testid/from_romi/response",
            payload=json.dumps(payload),
        )

    monkeypatch.setattr("romicoresdk.sdk.asyncio.wait_for", fake_response)

    romi_id = "romi-l01-0000000063"
    request_type = RequestType.REMOVE_TOOL
    request_data = RemoveToolRequestData(name="target")

    await sdk._send_unicast_request(romi_id, request_type, request_data)

    call = sdk._mqtt_client.publish.await_args
    assert (
        call.kwargs["topic"] == f"romicoresdk/{romi_id}/py-sdk-testid/to_romi/request"
    )
    actual_payload = json.loads(call.kwargs["payload"])
    expected_payload = {
        "request_id": "py-sdk-testid-0",
        "request_type": request_type.value,
        "data": {"name": "target"},
    }
    assert actual_payload == expected_payload


@pytest.mark.asyncio
async def test_get_event_future_and_wait_resolves_future(tmp_path) -> None:
    """Test that receiving an event message resolves the waiting future."""
    sdk = SDK.create(HOST, BROKER_PORT, certs_dir=tmp_path, mqtt_client_class=MqttMock)

    event_type = EventType.TOOL_CALL_INVOKED
    future = sdk._get_event_future(event_type)

    assert isinstance(future, asyncio.Future)
    assert not future.done()
    assert event_type in sdk._waiting_events
    assert sdk._waiting_events[event_type] is future

    # event topicを受信したときに、対応するfutureが解決されることをテスト

    payload = {
        "event_id": "test_event_id",
        "type": event_type,
        "data": {
            "name": "Example Tool",
            "call_id": "12345",
            "arguments_json": '{"param1": "value1"}',
        },
    }

    import json

    await sdk._on_message_event(
        "romicoresdk/romi-l01-0000000063/event", json.dumps(payload)
    )

    assert future.done()
    assert future.result() == RequestedToolCall(
        name="Example Tool",
        call_id="12345",
        arguments_json='{"param1": "value1"}',
    )


@pytest.mark.asyncio
async def test__send_unicast_response(monkeypatch, tmp_path) -> None:
    """Test that _send_unicast_response() sends the correct MQTT message."""
    monkeypatch.setattr("romicoresdk.sdk.generate_sdk_id", lambda: "py-sdk-testid")

    sdk = SDK.create(HOST, BROKER_PORT, certs_dir=tmp_path, mqtt_client_class=MqttMock)
    assert isinstance(sdk._mqtt_client, MqttMock)

    romi_id = "romi-l01-0000000063"
    request_id = "py-sdk-testid-0"
    request_type = RequestType.GET_RESOURCE_URL
    data = GetResourceUrlResponseData(
        resource_id="resource-001",
        url="https://example.com/image.jpg",
    )

    await sdk._send_unicast_response(romi_id, request_id, request_type, data)

    call = sdk._mqtt_client.publish.await_args
    assert (
        call.kwargs["topic"] == f"romicoresdk/{romi_id}/py-sdk-testid/to_romi/response"
    )
    actual_payload = json.loads(call.kwargs["payload"])
    expected_payload = {
        "request_id": request_id,
        "request_type": request_type.value,
        "data": {
            "resource_id": "resource-001",
            "url": "https://example.com/image.jpg",
        },
        "ok": True,
    }
    assert actual_payload == expected_payload


@pytest.mark.asyncio
async def test__send_unicast_response_error(monkeypatch, tmp_path) -> None:
    """Test that _send_unicast_response() sends the correct error response."""
    monkeypatch.setattr("romicoresdk.sdk.generate_sdk_id", lambda: "py-sdk-testid")

    sdk = SDK.create(HOST, BROKER_PORT, certs_dir=tmp_path, mqtt_client_class=MqttMock)
    assert isinstance(sdk._mqtt_client, MqttMock)

    romi_id = "romi-l01-0000000063"
    request_id = "py-sdk-testid-0"
    request_type = RequestType.GET_RESOURCE_URL
    error = ErrorInfo(
        code="INVALID_ARGUMENT", message="property.description is required"
    )

    await sdk._send_unicast_response(
        romi_id, request_id, request_type, ok=False, error=error
    )

    call = sdk._mqtt_client.publish.await_args
    assert (
        call.kwargs["topic"] == f"romicoresdk/{romi_id}/py-sdk-testid/to_romi/response"
    )
    actual_payload = json.loads(call.kwargs["payload"])
    expected_payload = {
        "request_id": request_id,
        "request_type": request_type.value,
        "ok": False,
        "error": {
            "code": "INVALID_ARGUMENT",
            "message": "property.description is required",
        },
    }
    assert actual_payload == expected_payload


@pytest.mark.asyncio
async def test_generate_csr(tmp_path) -> None:
    """Test that _generate_csr() generates a valid CSR."""
    sdk = SDK.create("127.0.0.1", 443, certs_dir=tmp_path, mqtt_client_class=MqttMock)

    # Create a temporary RSA key
    with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".key") as f:
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        f.write(key_pem)
        key_path = f.name

    try:
        # Generate CSR
        csr_string = sdk._generate_csr(key_path)

        # Verify CSR is valid PEM format
        assert csr_string.startswith("-----BEGIN CERTIFICATE REQUEST-----")
        assert csr_string.endswith("-----END CERTIFICATE REQUEST-----\n")

        # Verify CSR contains valid x509 data
        csr_pem = csr_string.encode("utf-8")
        csr = x509.load_pem_x509_csr(csr_pem)

        # Verify CSR has Common Name
        cn = csr.subject.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)
        assert len(cn) == 1
        assert cn[0].value == sdk._sdk_id

        # Verify CSR has Subject Alternative Name
        try:
            san_ext = csr.extensions.get_extension_for_class(
                x509.SubjectAlternativeName
            )
            assert len(san_ext.value) == 1
            assert isinstance(san_ext.value[0], x509.DNSName)
            assert san_ext.value[0].value == sdk._sdk_id
        except x509.ExtensionNotFound:
            pytest.fail("SubjectAlternativeName extension not found in CSR")

    finally:
        # Clean up temporary file
        import os

        os.unlink(key_path)
