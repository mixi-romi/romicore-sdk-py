from dataclasses import dataclass
from typing import ClassVar, Generic, Protocol, TypeVar, cast

from ..payload.error_info import ErrorInfo
from ..payload.unicast.data.base import ResponseData

ResponseDataT = TypeVar("ResponseDataT", bound=ResponseData)


@dataclass(frozen=True)
class ToRomiResponse(Generic[ResponseDataT]):
    """Romi から来たリクエストへのレスポンス。

    送信責務は持たず、対応する ``Romi.respond_*`` メソッドに渡すことで送信される。
    """

    _request_id: str
    _data: ResponseDataT | None
    _ok: bool
    _error: ErrorInfo | None


class _HasRequestId(Protocol):
    request_id: str


RequestPayloadT = TypeVar("RequestPayloadT", bound=_HasRequestId)
ResponseT = TypeVar("ResponseT", bound=ToRomiResponse)


class FromRomiRequest(Generic[RequestPayloadT, ResponseT]):
    """Romi から来るリクエストを表すユーザー向けクラス。

    内部に MQTT ペイロード (request_id を含む) を保持する。
    サブクラスは ``_response_cls`` にレスポンス型を設定し、
    型固有の ``create_success_response`` をオーバーライドする。
    """

    _response_cls: ClassVar[type[ToRomiResponse]]

    def __init__(self, payload: RequestPayloadT) -> None:
        self._payload = payload

    def create_error_response(self, error: ErrorInfo) -> ResponseT:
        return cast(
            ResponseT,
            self._response_cls(
                _request_id=self._payload.request_id,
                _data=None,
                _ok=False,
                _error=error,
            ),
        )
