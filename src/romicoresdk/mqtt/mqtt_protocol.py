from typing import Protocol, Callable, Coroutine, Any
from dataclasses import dataclass

MessageHandler = Callable[[str, str], Coroutine[Any, Any, None]]


@dataclass
class MqttEndpoint:
    """
    MQTTエンドポイントの設定を保持するデータクラスです
    """

    host: str
    port: int
    keepalive: int = 60


@dataclass
class TlsConfig:
    """
    TLS接続の設定を保持するデータクラスです
    """

    ca_certs_path: str
    client_certfile_path: str
    client_keyfile_path: str


class MqttProtocol(Protocol):
    """
    MQTT通信するためのプロトコルクラスです
    """

    async def connect(self, timeout: float) -> None: ...
    async def disconnect(self) -> None: ...
    async def publish(self, topic: str, payload: str, qos: int) -> None: ...
    async def subscribe(
        self, topic: str, message_handler: MessageHandler, qos: int
    ) -> None: ...
    async def unsubscribe(self, topic: str) -> None: ...
    def is_connected(self) -> bool: ...
