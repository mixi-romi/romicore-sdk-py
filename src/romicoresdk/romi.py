import asyncio
import logging
from typing import Callable, Awaitable, ClassVar

from . import converters
from .capability_negotiation import NegotiatedCapability
from .capability_table import SDK_CAPABILITY_TABLE, SdkCapabilityTable
from .exceptions import CapabilityNotSupportedError
from .payload.unicast.data.base import RequestData, ResponseData
from .payload.unicast.data.capability import RomiCapability
from .payload.unicast.data.create_romi_response_response import (
    CreateRomiResponseResponseData,
    CreateRomiResponseResponseDataV2,
)
from .payload.event.data.requested_tool_call import RequestedToolCall
from .payload.unicast.data.refresh_sdk_device_certificate_response import (
    RefreshSdkDeviceCertificateResponseData,
)
from .payload.unicast.data.get_registered_tools_response import (
    GetRegisteredToolsResponseData,
)
from .payload.unicast.from_romi_request_payload import (
    FromRomiRequestPayload,
    GetResourceUrlRequestPayload,
)
from .payload.request_type import RequestType
from .payload.error_info import ErrorInfo
from .payload.event.event_payload import EventType, EventData
from .payload.event.data.conversation_streaming_event import (
    ConversationStreamingEventData,
)
from .results import (
    ConversationStreamingEvent,
    ResourceUrlRequest,
    RomiResponse,
    SdkDeviceCertificate,
    ToolCall,
)

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# request_type は RequestType（公開種別）に加え、コア enum に存在しない
# 種別（オーバーレイが定義する種別）を str で渡せるよう RequestType | str を許容する。
RequesterMethod = Callable[
    [str, RequestType | str, RequestData],
    Awaitable[ResponseData | None],
]
ResponderMethod = Callable[
    [str, str, RequestType | str, ResponseData | None, bool, ErrorInfo | None],
    Awaitable[None],
]
GetEventFutureMethod = Callable[[EventType], asyncio.Future[EventData]]
# request_type は RequestType（公開種別）に加え、オーバーレイが定義する種別を
# str で渡せるよう RequestType | str を許容する。
GetRequestFutureMethod = Callable[
    [RequestType | str], asyncio.Future[FromRomiRequestPayload]
]


class Romi:
    """Romi クラス

    Romi クラスは、SDK-mode が有効な Romi を表すクラスです。
    Romi へのリクエスト送信や、Romi からのイベントやリクエストの待機を行うためのメソッドを提供します。
    """

    _sdk_capability_table: ClassVar[SdkCapabilityTable] = SDK_CAPABILITY_TABLE

    def __init__(
        self,
        model: str,
        serial_number: str,
        capability: RomiCapability | None,
        requester: RequesterMethod,
        responder: ResponderMethod,
        get_event_future: GetEventFutureMethod,
        get_request_future: GetRequestFutureMethod,
    ):
        """Romi コンストラクタ

        Romi オブジェクトを初期化します。

        Parameters
        ----------
        model : str
            Romi のモデル名
        serial_number : str
            Romi のシリアル番号
        capability : RomiCapability | None
            Romi のケイパビリティ情報。capability に未対応の古い FW では None。
            SDK が対応するバージョンと突き合わせた結果は
            ``negotiated_capability`` として保持される。
        requester : RequesterMethod
            Romi へのリクエストを送信するためのコールバック関数
        responder : ResponderMethod
            Romi へのレスポンスを送信するためのコールバック関数
        get_event_future : GetEventFutureMethod
            Romi からのイベントを待機するためのコールバック関数
        get_request_future : GetRequestFutureMethod
            Romi からのリクエストを待機するためのコールバック関数
        """
        self.model: str = model
        self.serial_number: str = serial_number
        self.id: str = model + "-" + serial_number
        self.capability: RomiCapability | None = capability
        self.negotiated_capability: NegotiatedCapability = (
            NegotiatedCapability.negotiate(capability, self._sdk_capability_table)
        )
        self._requester = requester
        self._responder = responder
        self._get_event_future = get_event_future
        self._get_request_future = get_request_future

    async def add_tool(
        self,
        name: str,
        description: str,
        additional_base_instruction: str,
        additional_response_instruction: str,
        skill: str,
        parameters: str | None = None,
    ) -> None:
        """Romi にツールを追加します。

        Parameters
        ----------
        name : str
            ツールの名前
        description : str
            ツールの説明
        additional_base_instruction : str
            ツール呼び出しのためのインストラクション
        additional_response_instruction : str
            ツール実行時のレスポンス生成で個別に追加するインストラクション
        skill : str
            ツール呼び出し時に Romi 内部で実行する処理の種類
            （``reset_conversation`` / ``download_picture`` / ``no_operation``）
        parameters : str | None
            ツールのパラメータ定義（JSON Schema 形式の文字列）。省略可能。
        """
        request_type = self._resolve_to_romi_request_type(RequestType.ADD_TOOL)
        logger.debug(f"Adding tool to Romi {self.id}: {name}")

        tool = converters.build_add_tool_request_data(
            name=name,
            description=description,
            additional_base_instruction=additional_base_instruction,
            additional_response_instruction=additional_response_instruction,
            skill=skill,
            parameters=parameters,
        )
        await self._requester(
            self.id,
            request_type,
            tool,
        )

        logger.info(f"Tool added to Romi {self.id}: {name}")

    async def remove_tool(self, name: str) -> None:
        """Romi から指定したツールを削除します。

        Parameters
        ----------
        name : str
            削除するツール名
        """
        request_type = self._resolve_to_romi_request_type(RequestType.REMOVE_TOOL)
        logger.debug(f"Removing tool from Romi {self.id}: {name}")

        await self._requester(
            self.id,
            request_type,
            converters.build_remove_tool_request_data(name=name),
        )

        logger.info(f"Tool removed from Romi {self.id}: {name}")

    async def wait_for_tool_call(self) -> ToolCall:
        """Romi からのツール呼び出し要求を待機します。

        Returns
        -------
        ToolCall
            要求されたツール情報
        """
        self._ensure_supported(EventType.TOOL_CALL_INVOKED)
        logger.debug(f"Waiting for tool request on Romi {self.id}...")

        requested_tool_call = await self._get_event_future(EventType.TOOL_CALL_INVOKED)
        if not isinstance(requested_tool_call, RequestedToolCall):
            raise TypeError("Unexpected event payload type for wait_for_tool_call")

        logger.info(
            f"Received tool request on Romi {self.id}: {requested_tool_call.name}"
        )
        return converters.to_tool_call(requested_tool_call)

    async def wait_for_conversation_streaming_event(
        self,
    ) -> ConversationStreamingEvent:
        """Romi からの会話ストリーミングイベントを待機します。

        Returns
        -------
        ConversationStreamingEvent
            会話ストリーミングイベントの情報
        """
        self._ensure_supported(EventType.CONVERSATION_STREAMING)
        logger.debug(f"Waiting for conversation_streaming event on Romi {self.id}...")

        event_data = await self._get_event_future(EventType.CONVERSATION_STREAMING)
        if not isinstance(event_data, ConversationStreamingEventData):
            raise TypeError(
                "Unexpected event payload type for wait_for_conversation_streaming_event"
            )

        logger.info(
            f"Received conversation_streaming event on Romi {self.id}: {event_data.utterance_text}"
        )
        return converters.to_conversation_streaming_event(event_data)

    async def create_and_speak_response(
        self,
        instruction: str | None = None,
        user_utterance: str | None = None,
        should_include_user_utterance_in_conversation_log: bool = False,
    ) -> RomiResponse:
        """Romi に発話させます。

        Romi に発話させるためのリクエストを送信し、Romi が生成したレスポンスを取得します。
        Romi が会話できない状態の場合はエラーになります。

        Parameters
        ----------
        instruction : str | None
            Romi の発話生成のためのインストラクション。省略可能。
        user_utterance : str | None
            ユーザーの発話テキスト。省略可能。
        should_include_user_utterance_in_conversation_log : bool
            ``user_utterance`` を会話ログに含めるかどうか。
            ``user_utterance`` を指定する場合はあわせて設定してください。

        Returns
        -------
        RomiResponse
            Romi が生成したレスポンスのデータ

        Raises
        ------
        ValueError
            ``user_utterance`` を指定せずに
            ``should_include_user_utterance_in_conversation_log=True`` とした場合。
        """
        request_type = self._resolve_to_romi_request_type(
            RequestType.CREATE_ROMI_RESPONSE
        )
        logger.debug(f"Creating Romi response for Romi {self.id}")

        request = converters.build_create_romi_response_request_data(
            instruction=instruction,
            user_utterance=user_utterance,
            should_include_user_utterance_in_conversation_log=(
                should_include_user_utterance_in_conversation_log
            ),
        )
        romi_response = await self._requester(
            self.id,
            request_type,
            request,
        )

        if romi_response is None:
            raise ValueError("Failed to obtain response from Romi.")

        if not isinstance(
            romi_response,
            (CreateRomiResponseResponseData, CreateRomiResponseResponseDataV2),
        ):
            raise TypeError("Unexpected response type for create_and_speak_response")

        logger.info(f"Romi response created for Romi {self.id}")
        return converters.to_romi_response(romi_response)

    async def refresh_sdk_device_certificate(self, csr: str) -> SdkDeviceCertificate:
        """SDK デバイス証明書を更新します。

        Parameters
        ----------
        csr : str
            証明書署名要求（CSR）

        Returns
        -------
        SdkDeviceCertificate
            更新された SDK デバイス証明書の情報
        """
        request_type = self._resolve_to_romi_request_type(
            RequestType.REFRESH_SDK_DEVICE_CERTIFICATE
        )
        logger.debug(f"Refreshing SDK device certificate for Romi {self.id}")

        request = converters.build_refresh_sdk_device_certificate_request_data(csr=csr)
        response = await self._requester(
            self.id,
            request_type,
            request,
        )
        if response is None:
            raise ValueError("Failed to obtain response from Romi.")
        if not isinstance(response, RefreshSdkDeviceCertificateResponseData):
            raise TypeError(
                "Unexpected response type for refresh_sdk_device_certificate"
            )
        logger.info(f"SDK device certificate refreshed for Romi {self.id}.")
        return converters.to_sdk_device_certificate(response)

    async def get_registered_tools(self) -> list[str]:
        """Romi に登録済みのツール一覧を取得します。

        Returns
        -------
        list[str]
            Romi に登録されているツール名の一覧
        """
        request_type = self._resolve_to_romi_request_type(
            RequestType.GET_REGISTERED_TOOLS
        )
        logger.debug(f"Getting registered tools for Romi {self.id}")

        response = await self._requester(
            self.id,
            request_type,
            converters.build_get_registered_tools_request_data(),
        )
        if response is None:
            raise ValueError("Failed to obtain response from Romi.")
        if not isinstance(response, GetRegisteredToolsResponseData):
            raise TypeError("Unexpected response type for get_registered_tools")

        logger.info(f"Registered tools fetched for Romi {self.id}.")
        return response.tool_names

    async def start_conversation_stream(self, speaker: str = "romi") -> None:
        """Romi の会話ストリームを開始します。

        Parameters
        ----------
        speaker : str
            会話ストリームで有効化する話者（現時点では ``"romi"`` のみ）
        """
        request_type = self._resolve_to_romi_request_type(
            RequestType.START_CONVERSATION_STREAM
        )
        logger.debug(f"Starting conversation stream on Romi {self.id}")

        request = converters.build_start_conversation_stream_request_data(
            speaker=speaker
        )
        await self._requester(
            self.id,
            request_type,
            request,
        )

        logger.info(f"Conversation stream started on Romi {self.id}")

    async def stop_conversation_stream(self) -> None:
        """Romi の会話ストリームを停止します。"""
        request_type = self._resolve_to_romi_request_type(
            RequestType.STOP_CONVERSATION_STREAM
        )
        logger.debug(f"Stopping conversation stream on Romi {self.id}")

        await self._requester(
            self.id,
            request_type,
            converters.build_stop_conversation_stream_request_data(),
        )

        logger.info(f"Conversation stream stopped on Romi {self.id}")

    async def wait_for_get_resource_url_request(
        self,
    ) -> ResourceUrlRequest:
        """Romi からリソースURL取得リクエストが来るのを待機します。

        Returns
        -------
        ResourceUrlRequest
            リソースURL取得リクエスト。``request_id`` は
            ``respond_get_resource_url_success`` / ``respond_get_resource_url_error``
            に渡してレスポンスを返すために使う。
        """
        self._ensure_supported(RequestType.GET_RESOURCE_URL)
        logger.debug(f"Waiting for Get Resource URL Request on Romi {self.id}...")

        payload = await self._get_request_future(RequestType.GET_RESOURCE_URL)
        if not isinstance(payload, GetResourceUrlRequestPayload):
            raise TypeError(
                "Unexpected request payload type for wait_for_get_resource_url_request"
            )

        logger.info(f"Received Get Resource URL Request on Romi {self.id}.")
        return converters.to_resource_url_request(payload)

    async def respond_get_resource_url_success(
        self,
        request_id: str,
        resource_id: str,
        url: str,
    ) -> None:
        """Romi にリソースURL取得リクエストへの成功レスポンスを返します。

        Parameters
        ----------
        request_id : str
            ``wait_for_get_resource_url_request`` で受け取った ``request_id``
        resource_id : str
            ``wait_for_get_resource_url_request`` で受け取った ``resource_id``
        url : str
            取得したリソースの URL
        """
        self._ensure_supported(RequestType.GET_RESOURCE_URL)
        logger.debug(f"Responding to Get Resource URL Request on Romi {self.id}")

        # NOTE: from_romi_request（Romi→SDK）方向は Romi が送信者のため、
        # Romi 側が共通版を決定できるようになるまで版符号化は行わない。
        # 応答は受信リクエストと同じ request_type を返すべきで、その配線は別途対応。
        await self._responder(
            self.id,
            request_id,
            RequestType.GET_RESOURCE_URL,
            converters.build_get_resource_url_response_data(
                resource_id=resource_id, url=url
            ),
            True,
            None,
        )

        logger.info(f"Responded to Get Resource URL Request on Romi {self.id}")

    async def respond_get_resource_url_error(
        self,
        request_id: str,
        code: str,
        message: str,
    ) -> None:
        """Romi にリソースURL取得リクエストへのエラーレスポンスを返します。

        Parameters
        ----------
        request_id : str
            ``wait_for_get_resource_url_request`` で受け取った ``request_id``
        code : str
            エラーコード
        message : str
            エラーメッセージ
        """
        self._ensure_supported(RequestType.GET_RESOURCE_URL)
        logger.debug(
            f"Responding to Get Resource URL Request on Romi {self.id} with error"
        )

        await self._responder(
            self.id,
            request_id,
            RequestType.GET_RESOURCE_URL,
            None,
            False,
            ErrorInfo(code=code, message=message),
        )

        logger.info(
            f"Responded to Get Resource URL Request on Romi {self.id} with error"
        )

    async def speak_text(self, text: str, emotion: str, lang: str) -> None:
        """Romiに指定したテキストを発話させます。

        Parameters
        ----------
        text : str
            発話するテキスト（空文字はエラーとなります）
        emotion : str
            発話の感情
        lang : str
            発話の言語
        """
        request_type = self._resolve_to_romi_request_type(RequestType.SPEAK_TEXT)
        logger.debug(f"Sending a request to Romi {self.id} to speak text.")
        request = converters.build_speak_text_request_data(
            text=text, emotion=emotion, lang=lang
        )
        await self._requester(self.id, request_type, request)
        logger.info(f"Request sent to Romi {self.id} to speak text.")

    def _resolve_to_romi_request_type(self, api: RequestType | str) -> str:
        """SDK→Romi 送信に使う request_type（バージョン符号化済み）を返します。

        ネゴシエーションで解決した版を符号化した request_type（例
        ``"speak_text_v2"``、v1 は生名）を返します。capability 未広告の旧 FW
        （baseline）では従来どおり生名を返します。

        Raises
        ------
        CapabilityNotSupportedError
            当該 API に使用可能な共通バージョンが存在しない場合。
        """
        # baseline 互換: capability 未広告の旧 FW では従来どおり生名を送る
        if self.capability is None:
            return str(api)
        wire_request_type = self.negotiated_capability.resolve_to_romi_request(api)
        if wire_request_type is None:
            raise CapabilityNotSupportedError(str(api))
        return wire_request_type

    def _ensure_supported(self, api: RequestType | EventType | str) -> None:
        """指定 API がこの Romi で使用可能でなければ例外を送出します。

        API 名はカテゴリ（to_romi_request / from_romi_request）を跨いで
        重複しないため、いずれかで使用可能なら OK とする。

        Parameters
        ----------
        api : RequestType | EventType | str
            対象の API 名

        Raises
        ------
        CapabilityNotSupportedError
            ネゴシエーションの結果、当該 API に使用可能な共通バージョンが存在しない場合。
        """
        if isinstance(api, EventType):
            return
        # baseline 互換: capability 未広告の旧 FW では従来どおり全許可
        if self.capability is None:
            return
        api_name = str(api)
        if (
            api_name not in self.negotiated_capability.to_romi_request
            and api_name not in self.negotiated_capability.from_romi_request
        ):
            raise CapabilityNotSupportedError(api_name)
