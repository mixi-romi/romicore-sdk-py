from pydantic import TypeAdapter
from typing import Literal

from .data.discover_available_romis_request import DiscoverAvailableRomisRequestData
from ..generic_payload import RequestPayload
from ..request_type import RequestType


class DiscoverAvailableRomisRequestPayload(
    RequestPayload[
        Literal[RequestType.DISCOVER_AVAILABLE_ROMIS],
        DiscoverAvailableRomisRequestData,
    ]
): ...


BroadcastRequestPayload = DiscoverAvailableRomisRequestPayload

DEFAULT_BROADCAST_REQUEST_ADAPTER = TypeAdapter(BroadcastRequestPayload)
