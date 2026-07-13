import asyncio
import logging
from typing import Callable, Awaitable

from .payload.unicast.data.base import RequestData, ResponseData
from .payload.unicast.data.add_tool_request import AddToolRequestData
from .payload.unicast.data.remove_tool_request import RemoveToolRequestData
from .payload.unicast.data.create_romi_response_request import (
    CreateRomiResponseRequestData,
)
from .payload.unicast.data.create_romi_response_response import (
    CreateRomiResponseResponseData,
)
from .payload.event.data.requested_tool_call import RequestedToolCall
from .requests.get_resource_url import (
    GetResourceUrlRequest,
    GetResourceUrlResponse,
)
from .payload.unicast.data.refresh_sdk_device_certificate_request import (
    RefreshSdkDeviceCertificateRequestData,
)
from .payload.unicast.data.refresh_sdk_device_certificate_response import (
    RefreshSdkDeviceCertificateResponseData,
)
from .payload.unicast.data.get_registered_tools_request import (
    GetRegisteredToolsRequestData,
)
from .payload.unicast.data.get_registered_tools_response import (
    GetRegisteredToolsResponseData,
)
from .payload.unicast.data.start_conversation_stream_request import (
    StartConversationStreamRequestData,
)
from .payload.unicast.data.stop_conversation_stream_request import (
    StopConversationStreamRequestData,
)
from .payload.unicast.data.speak_text_request import SpeakTextRequestData
from .payload.unicast.from_romi_request_payload import FromRomiRequestPayload
from .payload.request_type import RequestType
from .payload.error_info import ErrorInfo
from .payload.event.event_payload import EventType, EventData
from .payload.event.data.conversation_streaming_event import (
    ConversationStreamingEventData,
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

    def __init__(
        self,
        model: str,
        serial_number: str,
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
        self._requester = requester
        self._responder = responder
        self._get_event_future = get_event_future
        self._get_request_future = get_request_future

    async def add_tool(self, tool: AddToolRequestData) -> None:
        """Romi にツールを追加します。

        Parameters
        ----------
        tool : AddToolRequestData
            追加するツールのデータ
        """
        logger.debug(f"Adding tool to Romi {self.id}: {tool.name}")

        await self._requester(
            self.id,
            RequestType.ADD_TOOL,
            tool,
        )

        logger.info(f"Tool added to Romi {self.id}: {tool.name}")

    async def remove_tool(self, name: str) -> None:
        """Romi から指定したツールを削除します。

        Parameters
        ----------
        name : str
            削除するツール名
        """
        logger.debug(f"Removing tool from Romi {self.id}: {name}")

        await self._requester(
            self.id,
            RequestType.REMOVE_TOOL,
            RemoveToolRequestData(name=name),
        )

        logger.info(f"Tool removed from Romi {self.id}: {name}")

    async def wait_for_tool_call(self) -> RequestedToolCall:
        """Romi からのツール呼び出し要求を待機します。

        Returns
        -------
        RequestedToolCall
            要求されたツール情報
        """
        logger.debug(f"Waiting for tool request on Romi {self.id}...")

        requested_tool_call = await self._get_event_future(EventType.TOOL_CALL_INVOKED)
        if not isinstance(requested_tool_call, RequestedToolCall):
            raise TypeError("Unexpected event payload type for wait_for_tool_call")

        logger.info(
            f"Received tool request on Romi {self.id}: {requested_tool_call.name}"
        )
        return requested_tool_call

    async def wait_for_conversation_streaming_event(
        self,
    ) -> ConversationStreamingEventData:
        """Romi からの会話ストリーミングイベントを待機します。

        Returns
        -------
        ConversationStreamingEventData
            会話ストリーミングイベントの情報
        """
        logger.debug(f"Waiting for conversation_streaming event on Romi {self.id}...")

        event_data = await self._get_event_future(EventType.CONVERSATION_STREAMING)
        if not isinstance(event_data, ConversationStreamingEventData):
            raise TypeError(
                "Unexpected event payload type for wait_for_conversation_streaming_event"
            )

        logger.info(
            f"Received conversation_streaming event on Romi {self.id}: {event_data.utterance_text}"
        )
        return event_data

    async def create_and_speak_response(
        self, request: CreateRomiResponseRequestData
    ) -> CreateRomiResponseResponseData:
        """Romi に発話させます。

        Romi に発話させるためのリクエストを送信し、Romi が生成したレスポンスを取得します。
        Romi が会話できない状態の場合はエラーになります。

        Parameters
        ----------
        request : CreateRomiResponseRequestData
            生成するレスポンスのメタデータ

        Returns
        -------
        CreateRomiResponseResponseData
            Romi が生成したレスポンスのデータ
        """
        logger.debug(f"Creating Romi response for Romi {self.id}")

        romi_response = await self._requester(
            self.id,
            RequestType.CREATE_ROMI_RESPONSE,
            request,
        )

        if romi_response is None:
            raise ValueError("Failed to obtain response from Romi.")

        if not isinstance(romi_response, CreateRomiResponseResponseData):
            raise TypeError("Unexpected response type for create_and_speak_response")

        logger.info(f"Romi response created for Romi {self.id}")
        return romi_response

    async def refresh_sdk_device_certificate(
        self, request: RefreshSdkDeviceCertificateRequestData
    ) -> RefreshSdkDeviceCertificateResponseData:
        """SDK デバイス証明書を更新します。

        Parameters
        ----------
        request : RefreshSdkDeviceCertificateRequestData
            SDK デバイス証明書の更新に必要なデータ

        Returns
        -------
        RefreshSdkDeviceCertificateResponseData
            更新された SDK デバイス証明書の情報
        """
        logger.debug(f"Refreshing SDK device certificate for Romi {self.id}")

        response = await self._requester(
            self.id,
            RequestType.REFRESH_SDK_DEVICE_CERTIFICATE,
            request,
        )
        if response is None:
            raise ValueError("Failed to obtain response from Romi.")
        if not isinstance(response, RefreshSdkDeviceCertificateResponseData):
            raise TypeError(
                "Unexpected response type for refresh_sdk_device_certificate"
            )
        logger.info(f"SDK device certificate refreshed for Romi {self.id}.")
        return response

    async def get_registered_tools(self) -> GetRegisteredToolsResponseData:
        """Romi に登録済みのツール一覧を取得します。

        Returns
        -------
        GetRegisteredToolsResponseData
            Romi に登録されているツールの一覧
        """
        logger.debug(f"Getting registered tools for Romi {self.id}")

        response = await self._requester(
            self.id,
            RequestType.GET_REGISTERED_TOOLS,
            GetRegisteredToolsRequestData(),
        )
        if response is None:
            raise ValueError("Failed to obtain response from Romi.")
        if not isinstance(response, GetRegisteredToolsResponseData):
            raise TypeError("Unexpected response type for get_registered_tools")

        logger.info(f"Registered tools fetched for Romi {self.id}.")
        return response

    async def start_conversation_stream(
        self, request: StartConversationStreamRequestData
    ) -> None:
        """Romi の会話ストリームを開始します。"""
        logger.debug(f"Starting conversation stream on Romi {self.id}")

        await self._requester(
            self.id,
            RequestType.START_CONVERSATION_STREAM,
            request,
        )

        logger.info(f"Conversation stream started on Romi {self.id}")

    async def stop_conversation_stream(self) -> None:
        """Romi の会話ストリームを停止します。"""
        logger.debug(f"Stopping conversation stream on Romi {self.id}")

        await self._requester(
            self.id,
            RequestType.STOP_CONVERSATION_STREAM,
            StopConversationStreamRequestData(),
        )

        logger.info(f"Conversation stream stopped on Romi {self.id}")

    async def wait_for_get_resource_url_request(
        self,
    ) -> GetResourceUrlRequest:
        """Romi からリソースURL取得リクエストが来るのを待機します。

        Returns
        -------
        GetResourceUrlRequest
            リソースURL取得リクエスト
        """
        logger.debug(f"Waiting for Get Resource URL Request on Romi {self.id}...")

        payload = await self._get_request_future(RequestType.GET_RESOURCE_URL)
        logger.info(f"Received Get Resource URL Request on Romi {self.id}.")
        return GetResourceUrlRequest(payload)

    async def respond_get_resource_url(
        self,
        response: GetResourceUrlResponse,
    ) -> None:
        """Romi にリソースURL取得リクエストへのレスポンスを返します。

        Parameters
        ----------
        response : GetResourceUrlResponse
            ``GetResourceUrlRequest.create_success_response`` または
            ``create_error_response`` で生成したレスポンスオブジェクト。
        """
        logger.debug(f"Responding to Get Resource URL Request on Romi {self.id}")

        await self._responder(
            self.id,
            response._request_id,
            RequestType.GET_RESOURCE_URL,
            response._data,
            response._ok,
            response._error,
        )

        logger.info(f"Responded to Get Resource URL Request on Romi {self.id}")

    async def speak_text(self, request: SpeakTextRequestData) -> None:
        """Romiに指定したテキストを発話させます。

        Parameters
        ----------
        request : SpeakTextRequestData
            発話するテキストおよび感情などのデータ
        """
        logger.debug(f"Sending a request to Romi {self.id} to speak text.")
        await self._requester(self.id, RequestType.SPEAK_TEXT, request)
        logger.info(f"Request sent to Romi {self.id} to speak text.")
