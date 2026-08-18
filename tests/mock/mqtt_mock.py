from unittest.mock import AsyncMock, Mock
from romicoresdk.mqtt.mqtt_protocol import MqttEndpoint, TlsConfig


class MqttMock:
    def __init__(
        self, mqtt_endpoint: MqttEndpoint, tls_config: TlsConfig, client_id: str
    ) -> None:
        self._mqtt_endpoint = mqtt_endpoint
        self._tls_config = tls_config
        self._client_id = client_id

        # 接続状態を実際のクライアントと同じように遷移させる。SDK.connect() は
        # 接続前にしか意味のない設定（LWT）を is_connected() で判定するため、
        # 常に True を返すモックでは接続前後の違いを検証できない。
        self._connected = False

        async def _connect(timeout: float) -> None:
            self._connected = True

        async def _disconnect() -> None:
            self._connected = False

        self.connect = AsyncMock(side_effect=_connect)
        self.disconnect = AsyncMock(side_effect=_disconnect)
        self.publish = AsyncMock()
        self.subscribe = AsyncMock()
        self.unsubscribe = AsyncMock()
        self.set_will = Mock()
        self.set_on_connected = Mock()

        self.is_connected = Mock(side_effect=lambda: self._connected)
