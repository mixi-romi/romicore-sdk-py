from dataclasses import dataclass, field

from .payload.request_type import RequestType
from .payload.unicast.data.capability import (
    CapabilityEntry,
    CapabilityVersionState,
    VersionDescriptor,
)


def _version(
    version: str,
    state: CapabilityVersionState,
    sunset: str | None = None,
) -> VersionDescriptor:
    """``VersionDescriptor`` を簡潔に書くためのヘルパー。"""
    return VersionDescriptor(version=version, state=state, sunset=sunset)


def _entry(
    name: RequestType,
    versions: list[VersionDescriptor],
) -> CapabilityEntry:
    """API 名とバージョン一覧から ``CapabilityEntry`` を組み立てる。

    ``versions`` は呼び出し側で明示的に列挙する（デフォルト値は持たせない）。
    API ごとに対応バージョンが分かれていく前提のため、エントリ単位で個別に
    編集できるようにするための設計。
    """
    return CapabilityEntry(name=str(name), versions=versions)


@dataclass(frozen=True)
class SdkCapabilityTable:
    """SDK が実装している API と、その対応バージョンの一覧。"""

    to_romi_request: list[CapabilityEntry] = field(default_factory=list)
    from_romi_request: list[CapabilityEntry] = field(default_factory=list)


# SDK→Romi リクエスト能力テーブル
_TO_ROMI_REQUEST_ENTRIES = [
    _entry(RequestType.ADD_TOOL, [_version("1", CapabilityVersionState.ACTIVE)]),
    _entry(RequestType.REMOVE_TOOL, [_version("1", CapabilityVersionState.ACTIVE)]),
    _entry(
        RequestType.CREATE_ROMI_RESPONSE,
        [
            _version("1", CapabilityVersionState.DEPRECATED),
            _version("2", CapabilityVersionState.ACTIVE),
        ],
    ),
    _entry(
        RequestType.REFRESH_SDK_DEVICE_CERTIFICATE,
        [_version("1", CapabilityVersionState.ACTIVE)],
    ),
    _entry(
        RequestType.GET_REGISTERED_TOOLS, [_version("1", CapabilityVersionState.ACTIVE)]
    ),
    _entry(
        RequestType.START_CONVERSATION_STREAM,
        [_version("1", CapabilityVersionState.ACTIVE)],
    ),
    _entry(
        RequestType.STOP_CONVERSATION_STREAM,
        [_version("1", CapabilityVersionState.ACTIVE)],
    ),
    _entry(RequestType.SPEAK_TEXT, [_version("1", CapabilityVersionState.ACTIVE)]),
]

# Romi→SDK リクエスト能力テーブル
_FROM_ROMI_REQUEST_ENTRIES = [
    _entry(
        RequestType.GET_RESOURCE_URL, [_version("1", CapabilityVersionState.ACTIVE)]
    ),
]

SDK_CAPABILITY_TABLE = SdkCapabilityTable(
    to_romi_request=_TO_ROMI_REQUEST_ENTRIES,
    from_romi_request=_FROM_ROMI_REQUEST_ENTRIES,
)
