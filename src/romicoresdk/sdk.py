from pathlib import Path
import logging
import asyncio
import secrets
import base64
from importlib.metadata import PackageNotFoundError, version as _package_version
from typing import Awaitable, Callable, Generic, Self, TypeVar
from pydantic import ValidationError
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization

from .romi import Romi
from .mqtt.mqtt_protocol import MqttProtocol, MqttEndpoint, TlsConfig
from .mqtt.mqtt_paho_tls import MqttPahoTls
from .payload.request_type import RequestType
from .payload.error_info import ErrorInfo
from .payload.adapters import PayloadAdapters, DEFAULT_ADAPTERS
from .payload.unicast.from_romi_request_payload import FromRomiRequestPayload
from .payload.event.event_payload import EventType
from .payload.event.data.base import EventData
from .payload.broadcast.data.discover_available_romis_request import (
    DiscoverAvailableRomisRequestData,
    SdkCapabilityDeclaration,
)
from .payload.unicast.data.base import RequestData, ResponseData
from .payload.unicast.data.capability import RomiCapability
from .capability_table import SDK_CAPABILITY_TABLE, SdkCapabilityTable
from .topic.topic_name_manager import TopicNameManager

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

SDK_ID_PREFIX = "py-sdk"

# SDK が申告するプロトコルバージョン。
SDK_PROTOCOL_VERSION = 1

Handler = Callable[[str, dict], Awaitable[None]]

DEFAULT_QOS = 1

# discover 時に生成する Romi の型。romi_class 注入に追従し、discover の戻り値型を
# サブクラスに絞り込めるようにする。既定は Romi。
RomiT = TypeVar("RomiT", bound=Romi, default=Romi)


class SDK(Generic[RomiT]):
    """RomiCore SDK クラス

    RomiCore SDK のメインクラスです。MQTT ブローカーへの接続や
    Romi デバイスの発見を行います。
    """

    def __init__(
        self,
        endpoint: MqttEndpoint,
        tls_config: TlsConfig,
        mqtt_client_class: type[MqttProtocol] = MqttPahoTls,
        adapters: PayloadAdapters = DEFAULT_ADAPTERS,
        # 既定 Romi は RomiT の既定（=Romi）に一致するが、型チェッカは
        # type[RomiT] への代入を一般には検証できないため抑制する。
        romi_class: type[RomiT] = Romi,  # ty: ignore[invalid-parameter-default]
        sdk_capability_table: SdkCapabilityTable = SDK_CAPABILITY_TABLE,
    ):
        """SDK コンストラクタ

        SDK オブジェクトを初期化します。

        Parameters
        ----------
        endpoint : MqttEndpoint
            MQTT ブローカーのエンドポイント情報
        tls_config : TlsConfig
            TLS 設定情報
        mqtt_client_class : type[MqttProtocol], optional
            MQTT クライアントのクラス, by default MqttPahoTls
        adapters : PayloadAdapters, optional
            ペイロードのパースアダプタ群, by default DEFAULT_ADAPTERS
            （公開ユニオン）。拡張ユニオンを注入することでパース対象を
            差し替えられる。
        romi_class : type[Romi], optional
            discover 時に生成する Romi クラス, by default Romi。
            サブクラスを注入することで Romi に独自メソッドを生やせる。
        sdk_capability_table : SdkCapabilityTable, optional
            discover リクエストで申告する SDK の対応 API テーブル,
            by default SDK_CAPABILITY_TABLE。非公開 API を含む拡張テーブルを
            注入することで、申告内容を差し替えられる。
        """
        self._mqtt_endpoint = endpoint
        self._tls_config = tls_config
        self._adapters = adapters
        self._romi_class = romi_class
        self._sdk_capability_table = sdk_capability_table

        self._sdk_id = generate_sdk_id()
        self._topic_manager = TopicNameManager(self._sdk_id)
        self._request_id_counter = 0
        self._pending_requests: dict[str, asyncio.Future] = {}
        self._waiting_events: dict[EventType, asyncio.Future[EventData]] = {}
        self._waiting_requests: dict[
            RequestType | str, asyncio.Future[FromRomiRequestPayload]
        ] = {}

        logger.debug(f"Generated SDK ID: {self._sdk_id}")

        # dict of response/request handlers
        self._response_handlers: dict[str, Handler] = {
            RequestType.DISCOVER_AVAILABLE_ROMIS: self._discover_available_romis_handler,
        }

        self._request_handlers: dict[str, Handler] = {}

        # create MQTT client
        logger.debug(f"SDK initialized. SDK ID: {self._sdk_id}")
        self._mqtt_client = mqtt_client_class(
            self._mqtt_endpoint, self._tls_config, self._sdk_id
        )

    @classmethod
    def create(
        cls,
        host: str,
        broker_port: int,
        certs_dir: Path,
        keepalive: int | None = None,
        mqtt_client_class: type[MqttProtocol] = MqttPahoTls,
        adapters: PayloadAdapters = DEFAULT_ADAPTERS,
        romi_class: type[RomiT] = Romi,  # ty: ignore[invalid-parameter-default]
        sdk_capability_table: SdkCapabilityTable = SDK_CAPABILITY_TABLE,
    ) -> Self:
        """
        IPアドレスとポート、証明書ディレクトリパスからSDKを生成するファクトリメソッド

        Parameters
        ----------
        host : str
            ブローカーのホスト名または IP アドレス
        broker_port : int
            ブローカーのポート番号
        certs_dir : Path
            TLS 証明書のディレクトリパス
        keepalive : int, optional
            MQTT の keepalive 秒数, default None
        mqtt_client_class : type[MqttProtocol], optional
            MQTT クライアントのクラス, default MqttPahoTls
        adapters : PayloadAdapters, optional
            ペイロードのパースアダプタ群, default DEFAULT_ADAPTERS
        romi_class : type[Romi], optional
            discover 時に生成する Romi クラス, default Romi
        sdk_capability_table : SdkCapabilityTable, optional
            discover リクエストで申告する SDK の対応 API テーブル,
            default SDK_CAPABILITY_TABLE
        """
        if keepalive is None:
            endpoint = MqttEndpoint(host, broker_port)
        else:
            endpoint = MqttEndpoint(host, broker_port, keepalive)

        tls_config = TlsConfig(
            ca_certs_path=str(certs_dir / "ca.crt"),
            client_certfile_path=str(certs_dir / "client.crt"),
            client_keyfile_path=str(certs_dir / "client.key"),
        )

        return cls(
            endpoint=endpoint,
            tls_config=tls_config,
            mqtt_client_class=mqtt_client_class,
            adapters=adapters,
            romi_class=romi_class,
            sdk_capability_table=sdk_capability_table,
        )

    def register_request_handler(self, request_type: str, handler: Handler) -> None:
        """リクエストメッセージのハンドラを登録します。

        Parameters
        ----------
        request_type : str
            ハンドラを紐づけるリクエストタイプ
        handler : Handler
            (topic, payload_dict) を受け取る非同期ハンドラ
        """
        self._request_handlers[request_type] = handler

    def register_response_handler(self, request_type: str, handler: Handler) -> None:
        """レスポンスメッセージのハンドラを登録します。

        Parameters
        ----------
        request_type : str
            ハンドラを紐づけるリクエストタイプ
        handler : Handler
            (topic, payload_dict) を受け取る非同期ハンドラ
        """
        self._response_handlers[request_type] = handler

    async def connect(self, timeout: float = 10.0) -> None:
        """SDKの接続
        SDK を MQTT ブローカーに接続します。

        Parameters
        ----------
        timeout : float, optional
            接続タイムアウト秒数, by default 10.0
        """
        # Connect to MQTT broker
        logger.debug(
            f"Connecting to MQTT broker at {self._mqtt_endpoint.host}:{self._mqtt_endpoint.port}..."
        )

        await self._mqtt_client.connect(timeout=timeout)

        logger.info(
            f"Connected to MQTT broker. {self._mqtt_endpoint.host}:{self._mqtt_endpoint.port}"
        )

        # Subscribe to response and event topics
        for topic, handler in [
            (
                self._topic_manager.get_subscribe_response_topic(),
                self._on_message_response,
            ),
            (
                self._topic_manager.get_subscribe_request_topic(),
                self._on_message_request,
            ),
            (self._topic_manager.get_subscribe_event_topic(), self._on_message_event),
        ]:
            await self._mqtt_client.subscribe(
                topic=topic, message_handler=handler, qos=DEFAULT_QOS
            )

    async def discover_romis(self, timeout: int = 5) -> list[RomiT]:
        """Romi を見つける
        MQTTブローカーに接続されていて、SDK から制御可能な
        Romi の一覧を取得します。

        Parameters
        ----------
        timeout : int, optional
            タイムアウト時間（秒）, by default 5

        Returns
        -------
        list[Romi]
            SDK から制御可能な Romi のリスト
        """

        logger.debug(
            f"Discovering Romi devices with SDK-mode enabled (timeout: {timeout}s)..."
        )

        self._discovered_romis: list[RomiT] = []

        request_id = f"{self._sdk_id}-{self._request_id_counter}"
        self._request_id_counter += 1

        request_data = DiscoverAvailableRomisRequestData(
            capability=SdkCapabilityDeclaration(
                protocol_version=SDK_PROTOCOL_VERSION,
                sdk_version=_get_sdk_version(),
                from_romi_request=self._sdk_capability_table.from_romi_request,
            )
        )

        await self._mqtt_client.publish(
            topic=self._topic_manager.get_broadcast_request_topic(),
            payload=self._adapters.broadcast_request.validate_python(
                {
                    "request_id": request_id,
                    "request_type": RequestType.DISCOVER_AVAILABLE_ROMIS,
                    "data": request_data,
                }
            ).model_dump_json(exclude_none=True),
            qos=DEFAULT_QOS,
        )

        await asyncio.sleep(timeout)

        logger.info(
            f"Found Romi(s): {[romi.serial_number for romi in self._discovered_romis]}"
        )

        return self._discovered_romis

    async def _on_message_response(self, topic: str, payload: str):
        """
        responseメッセージ受信時のコールバック
        """
        logger.debug(f"Received message on topic '{topic}'")
        # parse topic
        if not self._topic_manager.parse_response_topic(topic):
            logger.warning(f"Received message on invalid topic: {topic}")
            return

        # parse payload
        try:
            response_payload = self._adapters.from_romi_response.validate_json(payload)
        except ValidationError as e:
            logger.warning(f"Received invalid response payload: {e}")
            return

        # check for pending request
        # ※ request_id に紐づく future がある場合は、ここで payload を set_result して
        # type での dispatch を省略します。
        request_id = response_payload.request_id
        if request_id in self._pending_requests:
            if not self._pending_requests[request_id].done():
                self._pending_requests[request_id].set_result(response_payload)
            return

        # dispatch by type
        msg_type = response_payload.request_type
        if msg_type is None:
            logger.warning("Received message does not contain 'request_type' field.")
            return

        handler = self._response_handlers.get(msg_type)
        if handler is not None:
            await handler(topic, response_payload.model_dump())
        else:
            logger.warning(f"No handler found for message type: {msg_type}")

    async def _on_message_request(self, topic: str, payload: str):
        """
        requestメッセージ受信時のコールバック
        """
        logger.debug(f"Received request message on topic '{topic}'")
        # parse topic
        if not self._topic_manager.parse_request_topic(topic):
            logger.warning(f"Received request message on invalid topic: {topic}")
            return

        # parse payload
        try:
            request_payload = self._adapters.from_romi_request.validate_json(payload)
        except ValidationError as e:
            logger.warning(f"Received invalid request payload: {e}")
            return

        # dispatch by type
        msg_type = request_payload.request_type
        if msg_type is None:
            logger.warning(
                "Received request message does not contain 'request_type' field."
            )
            return

        # check for waiting futures
        if msg_type in self._waiting_requests:
            if not self._waiting_requests[msg_type].done():
                self._waiting_requests[msg_type].set_result(request_payload)
                self._waiting_requests.pop(msg_type, None)
            return

        handler = self._request_handlers.get(msg_type)
        if handler is not None:
            await handler(topic, request_payload.model_dump())
        else:
            logger.warning(f"No handler found for request message type: {msg_type}")

    async def _on_message_event(self, topic: str, payload: str):
        """
        eventメッセージ受信時のコールバック
        """
        logger.debug(f"Received event message on topic '{topic}'")

        # parse topic
        if not self._topic_manager.parse_event_topic(topic):
            logger.warning(f"Received event message on invalid topic: {topic}")
            return

        # parse payload
        try:
            event_payload = self._adapters.event.validate_json(payload)
        except ValidationError as e:
            logger.warning(f"Received invalid event payload: {e}")
            return

        event_type = event_payload.type
        if event_type in self._waiting_events:
            if not self._waiting_events[event_type].done():
                self._waiting_events[event_type].set_result(event_payload.data)
                self._waiting_events.pop(event_type, None)
            return

    async def _discover_available_romis_handler(
        self, topic: str, payload_dict: dict
    ) -> None:
        """
        'discover_available_romis' メッセージのハンドラー
        """
        logger.debug("Handling 'discover_available_romis' message")
        data = payload_dict.get("data", {})
        model = data.get("model")
        serial_number = data.get("serial_number")
        capability_dict = data.get("capability")
        if serial_number is not None and model is not None:
            if capability_dict is not None:
                capability = RomiCapability.model_validate(capability_dict)
            else:
                capability = None
            self._discovered_romis.append(
                self._romi_class(
                    model,
                    serial_number,
                    capability,
                    self._send_unicast_request,
                    self._send_unicast_response,
                    self._get_event_future,
                    self._get_request_future,
                )
            )

    async def _send_unicast_request(
        self,
        romi_id: str,
        request_type: RequestType | str,
        data: RequestData,
        timeout: float = 10.0,
    ) -> ResponseData | None:
        """
        Romi に対してユニキャストリクエストを送信します。
        """
        request_id = f"{self._sdk_id}-{self._request_id_counter}"
        self._request_id_counter += 1

        payload = self._adapters.to_romi_request.validate_python(
            {
                "request_id": request_id,
                "request_type": request_type,
                "data": data,
            }
        ).model_dump_json(exclude_none=True)

        topic = self._topic_manager.get_unicast_request_topic(romi_id)

        self._pending_requests[request_id] = asyncio.get_running_loop().create_future()

        logger.debug(f"Sending unicast request to Romi {romi_id} on topic '{topic}'")

        try:
            await self._mqtt_client.publish(
                topic=topic,
                payload=payload,
                qos=DEFAULT_QOS,
            )

            await asyncio.wait_for(self._pending_requests[request_id], timeout=timeout)

            response_payload = self._pending_requests[request_id].result()
            result = response_payload.ok
            if not result:
                error_code = response_payload.error.code
                error_message = response_payload.error.message
                raise RuntimeError(
                    f"Romi {romi_id} returned error: {error_code} - {error_message}"
                )
        finally:
            self._pending_requests.pop(request_id, None)

        return response_payload.data

    async def _send_unicast_response(
        self,
        romi_id: str,
        request_id: str,
        request_type: RequestType | str,
        data: ResponseData | None = None,
        ok: bool = True,
        error: ErrorInfo | None = None,
    ) -> None:
        """
        Romi に対してユニキャストレスポンスを送信します。

        Parameters
        ----------
        romi_id : str
            送信先の Romi ID
        request_id : str
            対応するリクエストの ID
        request_type : RequestType | str
            リクエストタイプ
        data : ResponseData | None
            レスポンスデータ
        ok : bool, optional
            リクエストの処理が成功したかどうか, by default True
        error : ErrorInfo, optional
            エラー情報 (ok が False の場合), by default ErrorInfo(code="", message="")
        """
        if error is None:
            error = ErrorInfo(code="", message="")

        payload = self._adapters.to_romi_response.validate_python(
            {
                "request_id": request_id,
                "request_type": request_type,
                "data": data,
                "ok": ok,
                "error": error,
            }
        ).model_dump_json(exclude_none=True)

        topic = self._topic_manager.get_unicast_response_topic(romi_id)

        logger.debug(f"Sending unicast response to Romi {romi_id} on topic '{topic}'")

        await self._mqtt_client.publish(
            topic=topic,
            payload=payload,
            qos=DEFAULT_QOS,
        )

    def _get_event_future(self, event_type: EventType) -> asyncio.Future[EventData]:
        """
        指定されたイベントが来るのを待機します。
        戻り値の Future を await することでイベントの発生を待つことができます。
        """
        if event_type in self._waiting_events:
            if not self._waiting_events[event_type].done():
                return self._waiting_events[event_type]

        future = asyncio.get_running_loop().create_future()
        self._waiting_events[event_type] = future
        return future

    def _get_request_future(
        self, request_type: RequestType | str
    ) -> asyncio.Future[FromRomiRequestPayload]:
        """
        指定されたリクエストタイプのリクエストが来るのを待機します。
        戻り値の Future を await することでリクエストの到着を待つことができます。
        """
        if request_type in self._waiting_requests:
            if not self._waiting_requests[request_type].done():
                return self._waiting_requests[request_type]

        future: asyncio.Future[FromRomiRequestPayload] = (
            asyncio.get_running_loop().create_future()
        )
        self._waiting_requests[request_type] = future
        return future

    def _generate_csr(self, key_path: str) -> str:
        """
        CSR (Certificate Signing Request) を生成します。
        生成された CSR は PEM 形式の文字列で返されます。
        :param key_path: RSA秘密鍵のファイルパス
        :return: PEM形式のCSR文字列
        """
        # 1. 既存のRSA秘密鍵をPEM形式から読み込む
        with open(key_path, "rb") as f:
            loaded_private_key = serialization.load_pem_private_key(
                f.read(),
                password=None,
            )
        # RSA秘密鍵であることを確認
        if not isinstance(loaded_private_key, rsa.RSAPrivateKey):
            raise TypeError(
                "Unsupported private key type for CSR signing: expected RSA"
            )

        private_key: rsa.RSAPrivateKey = loaded_private_key

        # 2. CSRを作成（CN + SAN）
        # opensslのコマンド例:
        # openssl req -new -key client.key -out client.csr -subj "/CN=<SDK_ID>" -addext "subjectAltName=DNS:<SDK_ID>"
        csr = (
            x509.CertificateSigningRequestBuilder()
            .subject_name(
                x509.Name(
                    [
                        x509.NameAttribute(NameOID.COMMON_NAME, self._sdk_id),
                    ]
                )
            )
            .add_extension(
                x509.SubjectAlternativeName(
                    [
                        x509.DNSName(self._sdk_id),
                    ]
                ),
                critical=False,
            )
            .sign(private_key, hashes.SHA256())
        )
        # 3. CSRをPEM文字列として取得
        csr_pem = csr.public_bytes(serialization.Encoding.PEM).decode("utf-8")
        return csr_pem


def _get_sdk_version() -> str | None:
    """インストール済みパッケージから SDK バージョンを取得する。

    discover 申告の ``sdk_version``（情報/ログ用）に載せる。取得できない場合
    （未インストール等）は ``None`` を返す。
    """
    try:
        return _package_version("romicoresdk")
    except PackageNotFoundError:
        return None


def generate_sdk_id(nbytes: int = 5) -> str:
    """SDK IDの生成

    SDK ID を生成します。
    base32エンコードした乱数を小文字に変換し、
    prefixに付与した形式で生成します。

    Parameters
    ----------
    nbytes : int, optional
        乱数バイト数, by default 5
    """
    # 5 bytes = 40 bits → base32 8文字
    rand = secrets.token_bytes(nbytes)
    b32_low = base64.b32encode(rand).decode("ascii").rstrip("=").lower()
    return f"{SDK_ID_PREFIX}-{b32_low}"
