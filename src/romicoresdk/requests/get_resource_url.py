from dataclasses import dataclass

from ..payload.unicast.data.get_resource_url_request import ResourceType
from ..payload.unicast.data.get_resource_url_response import GetResourceUrlResponseData
from ..payload.unicast.from_romi_request_payload import GetResourceUrlRequestPayload
from .from_romi_request_base import FromRomiRequest, ToRomiResponse


@dataclass(frozen=True)
class GetResourceUrlResponse(ToRomiResponse[GetResourceUrlResponseData]):
    """リソースURL取得リクエストへのレスポンス。"""


class GetResourceUrlRequest(
    FromRomiRequest[GetResourceUrlRequestPayload, GetResourceUrlResponse]
):
    """Romi からのリソースURL取得リクエストを表すユーザー向けクラス。"""

    _response_cls = GetResourceUrlResponse

    @property
    def resource_id(self) -> str:
        return self._payload.data.resource_id

    @property
    def resource_type(self) -> ResourceType:
        return self._payload.data.resource_type

    def create_success_response(self, url: str) -> GetResourceUrlResponse:
        return GetResourceUrlResponse(
            _request_id=self._payload.request_id,
            _data=GetResourceUrlResponseData(
                resource_id=self.resource_id,
                url=url,
            ),
            _ok=True,
            _error=None,
        )
