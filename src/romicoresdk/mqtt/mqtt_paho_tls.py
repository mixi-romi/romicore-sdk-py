import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
from paho.mqtt.client import Client, ConnectFlags, DisconnectFlags
from paho.mqtt.reasoncodes import ReasonCode
from paho.mqtt.properties import Properties
from .mqtt_protocol import (
    ConnectedHandler,
    MessageHandler,
    MqttEndpoint,
    TlsConfig,
    Will,
)
from typing import Any
import asyncio
import logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class MqttPahoTls:
    """Paho MQTTライブラリを使用してTLS接続を行うMQTTクライアントクラス

    非同期IO (asyncio) を利用して、ノンブロッキングなMQTT通信を行います。
    TLSによる暗号化通信を行います。

    Parameters
    ----------
    mqtt_endpoint : MqttEndpoint
        接続先のMQTTエンドポイント情報を持つMqttEndpointオブジェクト。
    tls_config : TlsConfig
        TLS接続に必要な証明書情報を持つTlsConfigオブジェクト。
    client_id : str, optional
        MQTTクライアントのID。デフォルトは空文字列。
    """

    def __init__(
        self,
        mqtt_endpoint: MqttEndpoint,
        tls_config: TlsConfig,
        client_id: str = "",
    ):
        self._tls_config = tls_config
        self._mqtt_endpoint = mqtt_endpoint

        # MQTTクライアントの初期化
        self._client = mqtt.Client(
            callback_api_version=CallbackAPIVersion.VERSION2,
            client_id=client_id,
            protocol=mqtt.MQTTv311,
        )

        # TLSの設定
        self._client.tls_set(
            ca_certs=self._tls_config.ca_certs_path,
            certfile=self._tls_config.client_certfile_path,
            keyfile=self._tls_config.client_keyfile_path,
        )

        # コールバックの設定
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_publish = self._on_publish
        self._client.on_message = self._on_message
        self._client.on_subscribe = self._on_subscribe

        self._pending_publishes: dict[int, asyncio.Future] = {}
        self._pending_subscribes: dict[int, asyncio.Future] = {}
        self._message_handlers: dict[str, MessageHandler] = {}
        self._loop: asyncio.AbstractEventLoop | None = None
        self._connect_future: asyncio.Future[None] | None = None
        self._disconnect_future: asyncio.Future[None] | None = None
        self._on_connected_handler: ConnectedHandler | None = None
        # 初回接続を済ませたかどうか。再接続の判定に使う。
        self._has_connected = False

    async def connect(self, timeout: float):
        """clientの接続

        指定されたエンドポイントにTLSで接続し、メッセージ処理ループをバックグラウンドで開始します。
        接続が完了するか、タイムアウトするまで待機します。

        Parameters
        ----------
        timeout : float
            接続のタイムアウト時間（秒）。デフォルトは 10.0。

        Raises
        ------
        Exception
            接続に失敗した場合、タイムアウトした場合、またはキャンセルされた場合に発生します。
        """
        if self._client.is_connected():
            return
        self._loop = asyncio.get_running_loop()
        self._connect_future = self._loop.create_future()
        # 明示的な connect は「初回接続」として扱う。切断後に再度 connect を
        # 呼び直した場合も、自動再接続ではなくこちらの経路で完了を待つ。
        self._has_connected = False
        self._client.connect_async(
            self._mqtt_endpoint.host,
            self._mqtt_endpoint.port,
            self._mqtt_endpoint.keepalive,
        )
        self._client.loop_start()

        try:
            await asyncio.wait_for(self._connect_future, timeout=timeout)
        except (Exception, asyncio.CancelledError):
            self._client.loop_stop()
            raise

    async def disconnect(self):
        """clientの切断

        バックグラウンドで実行中のメッセージ処理ループを停止し、接続を閉じます。
        切断が完了するまで待機します。

        Raises
        ------
        Exception
            切断処理中にエラーが発生した場合に発生します。
        """
        if not self._client.is_connected():
            return

        if self._loop is None:
            raise RuntimeError("Event loop is not running")
        self._disconnect_future = self._loop.create_future()
        self._client.disconnect()
        await self._disconnect_future
        self._client.loop_stop()

    async def publish(self, topic: str, payload: str, qos: int = 0):
        """メッセージのpublish

        メッセージを指定したトピックにパブリッシュします。
        メッセージがブローカーに送信され、受領確認（ACK）が返るまで待機します。

        Parameters
        ----------
        topic : str
            メッセージを送信するトピック名。
        payload : str
            送信するメッセージ。

        Raises
        ------
        Exception
            パブリッシュ処理中にエラーが発生した場合に発生します。
        """
        message_info = self._client.publish(topic, payload, qos=qos)
        mid = message_info.mid

        if self._loop is None:
            raise RuntimeError("Event loop is not running")
        self._pending_publishes[mid] = self._loop.create_future()
        try:
            await self._pending_publishes[mid]
        finally:
            if mid in self._pending_publishes:
                del self._pending_publishes[mid]

    async def subscribe(
        self, topic: str, message_handler: MessageHandler, qos: int = 0
    ):
        """指定トピックのsubscribe

        指定したトピックをサブスクライブします。
        サブスクリプション要求がブローカーに受け入れられ、完了通知（SUBACK）を受信するまで待機します。
        指定されたトピックに対するメッセージを受信すると、登録されたハンドラが呼び出されます。

        Parameters
        ----------
        topic : str
            サブスクライブするトピック名。ワイルドカード（+ または #）を含めることができます。
        message_handler : MessageHandler
            メッセージ受信時に呼び出されるコールバック関数。
            (topic: str, payload: str) -> Coroutine[Any, Any, None] のシグネチャを持つ必要があります。

        Raises
        ------
        Exception
            サブスクライブ要求が失敗した場合や、ブローカーから拒否された場合に発生します。
        """
        self._message_handlers[topic] = message_handler
        result, mid = self._client.subscribe(topic, qos=qos)

        if result != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError(
                f"Failed to subscribe to topic {topic}, error code: {result}"
            )
        if mid is None:
            raise RuntimeError(f"Subscribe returned None mid for topic {topic}")

        if self._loop is None:
            raise RuntimeError("Event loop is not running")
        self._pending_subscribes[mid] = self._loop.create_future()
        try:
            await self._pending_subscribes[mid]
        finally:
            if mid in self._pending_subscribes:
                del self._pending_subscribes[mid]

    async def unsubscribe(self, topic: str) -> None:
        """指定トピックのunsubscribe

        指定したトピックのサブスクリプション（購読）を解除します。
        購読解除要求が完了するまで待機します。ローカルのメッセージハンドラも削除されます。

        Parameters
        ----------
        topic : str
            サブスクリプションを解除するトピック名。

        Raises
        ------
        Exception
            要求が失敗した場合に発生します。
        """
        if topic in self._message_handlers:
            del self._message_handlers[topic]
        result, _ = self._client.unsubscribe(topic)

        if result != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError(
                f"Failed to unsubscribe from topic {topic}, error code: {result}"
            )

    def is_connected(self) -> bool:
        """接続状態の確認

        現在の接続状態を確認します。

        Returns
        -------
        bool
            接続されている場合は True、そうでない場合は False。
        """
        return self._client.is_connected()

    def set_will(self, will: Will) -> None:
        """LWT (Last Will and Testament) を設定する

        正常な DISCONNECT を経ずに接続が切れた場合に、ブローカーが代理で
        パブリッシュするメッセージを登録します。

        Parameters
        ----------
        will : Will
            LWT の設定

        Raises
        ------
        RuntimeError
            既に接続済み、または接続処理が進行中の場合。LWT は CONNECT
            パケットに載せてブローカーへ渡すため、あとから設定しても現在の
            接続には反映されません。
        """
        if self._client.is_connected() or self._is_connecting():
            raise RuntimeError("Will must be set before connecting")
        self._client.will_set(
            will.topic, will.payload, qos=will.qos, retain=will.retain
        )

    def _is_connecting(self) -> bool:
        """
        接続処理が進行中かどうかを返すメソッドです

        connect() が connect_async を呼んでから CONNACK を受け取るまでの間は
        is_connected() が偽のままですが、CONNECT パケットは既に送出されている
        可能性があるため、この間の LWT 設定は現在の接続に間に合いません。
        """
        return self._connect_future is not None and not self._connect_future.done()

    def set_on_connected(self, handler: ConnectedHandler) -> None:
        """再接続時に呼ばれるハンドラを設定する

        ブローカーとの接続が切れた後、クライアントが自動再接続に成功した
        タイミングで呼ばれます。初回接続では呼ばれません（初回は
        :meth:`connect` の呼び出し側が同期的に処理するため）。

        Parameters
        ----------
        handler : ConnectedHandler
            再接続時に呼び出される非同期ハンドラ
        """
        self._on_connected_handler = handler

    def _on_connect(
        self,
        client: Client,
        userdata: Any,
        connect_flags: ConnectFlags,
        reason_code: ReasonCode,
        properties: Properties | None,
    ) -> None:
        """
        接続完了時のコールバックメソッドです
        """
        if not reason_code.is_failure:
            if not self._has_connected:
                # 初回接続。subscribe や online 通知は connect() の呼び出し側が
                # 同期的に行うため、ここでは future を解決するだけにする。
                logger.info("Connected successfully")
                self._has_connected = True
                if (
                    self._connect_future
                    and not self._connect_future.done()
                    and self._loop
                ):
                    self._loop.call_soon_threadsafe(
                        self._connect_future.set_result, None
                    )
                return

            # 自動再接続。clean session により購読が失われているため、
            # 購読の復旧などをハンドラへ委譲する。
            logger.info("Reconnected successfully")
            if self._on_connected_handler is not None and self._loop:
                self._loop.call_soon_threadsafe(
                    asyncio.create_task, self._run_on_connected()
                )
        else:
            if self._connect_future and not self._connect_future.done() and self._loop:
                error = Exception(f"Failed to connect. Reason: {reason_code}")
                self._loop.call_soon_threadsafe(
                    self._connect_future.set_exception, error
                )

    async def _run_on_connected(self) -> None:
        """
        再接続ハンドラを実行するメソッドです

        paho のコールバック起点のタスクとして実行されるため、例外が
        呼び出し元へ伝播しません。握り潰さずログに残します。
        """
        if self._on_connected_handler is None:
            return
        try:
            await self._on_connected_handler()
        except Exception:
            logger.exception("Failed to handle reconnection")

    def _on_disconnect(
        self,
        client: Client,
        userdata: Any,
        disconnect_flags: DisconnectFlags,
        reason_code: ReasonCode,
        properties: Properties | None,
    ) -> None:
        """
        切断時のコールバックメソッドです
        """
        logger.info(f"Disconnected. Reason: {reason_code}")
        if (
            self._disconnect_future
            and not self._disconnect_future.done()
            and self._loop
        ):
            self._loop.call_soon_threadsafe(self._disconnect_future.set_result, None)

    def _on_publish(
        self,
        client: Client,
        userdata: Any,
        mid: int,
        reason_code: ReasonCode,
        properties: Properties,
    ) -> None:
        """
        メッセージがpublishされたときのコールバックメソッドです
        """
        if mid in self._pending_publishes:
            future = self._pending_publishes[mid]
            if not future.done() and self._loop:
                self._loop.call_soon_threadsafe(future.set_result, None)

    def _on_message(
        self, client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage
    ) -> None:
        """
        メッセージを受信したときのコールバックメソッドです
        """
        topic = msg.topic
        payload = msg.payload.decode("utf-8")

        matched = False
        if self._loop:
            for sub_topic, handler in self._message_handlers.items():
                if mqtt.topic_matches_sub(sub_topic, topic):
                    self._loop.call_soon_threadsafe(
                        asyncio.create_task, handler(topic, payload)
                    )
                    matched = True

        if not matched:
            logger.warning(f"Received message for unhandled topic: {topic}")

    def _on_subscribe(
        self,
        client: Client,
        userdata: Any,
        mid: int,
        reason_code_list: list[ReasonCode],
        properties: Properties,
    ) -> None:
        """
        subscribe完了時のコールバックメソッドです
        """
        if mid in self._pending_subscribes:
            future = self._pending_subscribes[mid]
            if not future.done() and self._loop:
                self._loop.call_soon_threadsafe(future.set_result, None)
