from typing import Literal
from pydantic import TypeAdapter

from romicoresdk.payload.unicast.data.get_resource_url_request import (
    GetResourceUrlRequestData,
)
from ..generic_payload import RequestPayload
from ..request_type import RequestType


class GetResourceUrlRequestPayload(
    RequestPayload[Literal[RequestType.GET_RESOURCE_URL], GetResourceUrlRequestData]
): ...


FromRomiRequestPayload = GetResourceUrlRequestPayload

DEFAULT_FROM_ROMI_REQUEST_ADAPTER = TypeAdapter(FromRomiRequestPayload)
