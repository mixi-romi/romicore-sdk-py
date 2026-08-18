"""MqttPahoTls の LWT 登録と再接続検知のテスト。"""

import asyncio
from typing import NamedTuple
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from paho.mqtt.client import ConnectFlags
from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.reasoncodes import ReasonCode

from romicoresdk.mqtt.mqtt_paho_tls import MqttPahoTls
from romicoresdk.mqtt.mqtt_protocol import MqttEndpoint, TlsConfig, Will

ENDPOINT = MqttEndpoint("127.0.0.1", 443)
TLS_CONFIG = TlsConfig(
    ca_certs_path="ca.crt",
    client_certfile_path="client.crt",
    client_keyfile_path="client.key",
)
CONNECT_FLAGS = ConnectFlags(session_present=False)


class MockedClient(NamedTuple):
    """テスト対象と、その内部の paho クライアントのモック。"""

    mqtt: MqttPahoTls
    paho: MagicMock


@pytest.fixture
def client(monkeypatch) -> MockedClient:
    """paho の Client をモックに差し替えた MqttPahoTls を返す。

    実際の ``tls_set`` は証明書ファイルの存在を要求するため、
    Client ごとモックにする。
    """
    paho_client = MagicMock()
    paho_client.is_connected.return_value = False
    monkeypatch.setattr(
        "romicoresdk.mqtt.mqtt_paho_tls.mqtt.Client",
        Mock(return_value=paho_client),
    )
    return MockedClient(
        mqtt=MqttPahoTls(ENDPOINT, TLS_CONFIG, client_id="py-sdk-testid"),
        paho=paho_client,
    )


def _success_reason_code() -> ReasonCode:
    """接続成功 (CONNACK / Success) を表す ReasonCode。"""
    return ReasonCode(PacketTypes.CONNACK, "Success")


def test_set_will_passes_settings_to_paho(client: MockedClient) -> None:
    """set_will は paho の will_set へそのまま渡される。"""
    client.mqtt.set_will(
        Will(topic="topic/status", payload='{"a":1}', qos=1, retain=False)
    )

    client.paho.will_set.assert_called_once_with(
        "topic/status", '{"a":1}', qos=1, retain=False
    )


def test_set_will_after_connect_raises(client: MockedClient) -> None:
    """接続後の set_will は現在の接続に反映できないためエラーにする。"""
    client.paho.is_connected.return_value = True

    with pytest.raises(RuntimeError, match="Will must be set before connecting"):
        client.mqtt.set_will(Will(topic="topic/status", payload="{}"))


@pytest.mark.asyncio
async def test_on_connect_first_time_resolves_future(client: MockedClient) -> None:
    """初回接続では future を解決し、再接続ハンドラは呼ばない。"""
    handler = AsyncMock()
    client.mqtt.set_on_connected(handler)
    loop = asyncio.get_running_loop()
    client.mqtt._loop = loop
    connect_future = loop.create_future()
    client.mqtt._connect_future = connect_future

    client.mqtt._on_connect(
        client.paho, None, CONNECT_FLAGS, _success_reason_code(), None
    )
    await asyncio.sleep(0)

    assert connect_future.done()
    handler.assert_not_awaited()
    assert client.mqtt._has_connected is True


@pytest.mark.asyncio
async def test_on_connect_reconnect_invokes_handler(client: MockedClient) -> None:
    """2 回目以降の接続（自動再接続）では再接続ハンドラを起動する。"""
    handler = AsyncMock()
    client.mqtt.set_on_connected(handler)
    loop = asyncio.get_running_loop()
    client.mqtt._loop = loop
    client.mqtt._connect_future = loop.create_future()

    # 初回接続
    client.mqtt._on_connect(
        client.paho, None, CONNECT_FLAGS, _success_reason_code(), None
    )
    await asyncio.sleep(0)
    handler.assert_not_awaited()

    # 自動再接続
    client.mqtt._on_connect(
        client.paho, None, CONNECT_FLAGS, _success_reason_code(), None
    )
    # call_soon_threadsafe -> create_task -> ハンドラ実行 まで進める
    for _ in range(3):
        await asyncio.sleep(0)

    handler.assert_awaited_once()


@pytest.mark.asyncio
async def test_reconnect_handler_exception_is_swallowed(client: MockedClient) -> None:
    """再接続ハンドラの例外は paho のコールバック起点のため伝播させない。"""
    handler = AsyncMock(side_effect=RuntimeError("boom"))
    client.mqtt.set_on_connected(handler)

    await client.mqtt._run_on_connected()

    handler.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_on_connected_without_handler(client: MockedClient) -> None:
    """ハンドラ未登録なら何もしない。"""
    await client.mqtt._run_on_connected()


@pytest.mark.asyncio
async def test_set_will_while_connecting_raises(client: MockedClient) -> None:
    """接続処理中の set_will も弾く。

    connect_async の後 CONNACK までは is_connected() が偽のままだが、
    CONNECT パケットは既に送出されている可能性があるため、この間の設定は
    現在の接続に間に合わない。
    """
    loop = asyncio.get_running_loop()
    client.mqtt._loop = loop
    # connect() が connect_async を呼んだ直後の状態を再現する
    client.mqtt._connect_future = loop.create_future()

    with pytest.raises(RuntimeError, match="Will must be set before connecting"):
        client.mqtt.set_will(Will(topic="topic/event", payload="{}"))

    # CONNACK 相当で future が解決し、切断済みになれば再度設定できる
    client.mqtt._connect_future.set_result(None)
    client.mqtt.set_will(Will(topic="topic/event", payload="{}"))
    client.paho.will_set.assert_called_once()
