from unittest.mock import AsyncMock, Mock
from romicoresdk.mqtt.mqtt_protocol import MqttEndpoint, TlsConfig


class MqttMock:
    def __init__(
        self, mqtt_endpoint: MqttEndpoint, tls_config: TlsConfig, client_id: str
    ) -> None:
        self._mqtt_endpoint = mqtt_endpoint
        self._tls_config = tls_config
        self._client_id = client_id

        self.connect = AsyncMock()
        self.disconnect = AsyncMock()
        self.publish = AsyncMock()
        self.subscribe = AsyncMock()
        self.unsubscribe = AsyncMock()

        self.is_connected = Mock(return_value=True)
