import logging

from dataclasses import dataclass, field
from typing import Self

from .capability_table import SDK_CAPABILITY_TABLE, SdkCapabilityTable
from .payload.request_type import RequestType
from .payload.unicast.data.capability import (
    CapabilityEntry,
    CapabilityVersionState,
    RomiCapability,
)

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# バージョンが使用可能とみなす状態（廃止 (removed) 済みのバージョンは対象外）
_USABLE_STATES = frozenset(
    {CapabilityVersionState.ACTIVE, CapabilityVersionState.DEPRECATED}
)

_BASELINE_VERSION = "1"


@dataclass(frozen=True)
class NegotiatedCapability:
    """discover 時に決定した、Romi ごとの API バージョン対応表。

    キーは API 名（:class:`RequestType` の値）、値はその API で実際に使用する
    バージョン。SDK と Romi の間で使用可能な共通バージョンが存在しない API は
    キーごと含まれない。

    ``to_romi_request``（SDK→Romi）は SDK 側でローカルにネゴシエートした結果、
    ``from_romi_request``（Romi→SDK）は Romi 側がネゴシエートして返した
    ``resolved_from_romi_request`` をそのまま採用した結果である。
    """

    to_romi_request: dict[str, str] = field(default_factory=dict)
    from_romi_request: dict[str, str] = field(default_factory=dict)

    def to_romi_request_version(self, request_type: RequestType | str) -> str | None:
        """SDK→Romi リクエストで実際に使用する API バージョンを返す。"""
        return self.to_romi_request.get(str(request_type))

    def from_romi_request_version(self, request_type: RequestType | str) -> str | None:
        """Romi→SDK リクエストで実際に使用する API バージョンを返す。"""
        return self.from_romi_request.get(str(request_type))

    def resolve_to_romi_request(self, request_type: RequestType | str) -> str | None:
        """SDK→Romi リクエストで実際にワイヤへ載せる request_type を返す。

        解決した版を符号化した request_type（例 ``"speak_text_v2"``、v1 は生名）を
        返す。使用可能な共通バージョンが存在しない場合は ``None``。
        """
        version = self.to_romi_request_version(request_type)
        if version is None:
            return None
        return self._encode_request_type(str(request_type), version)

    @classmethod
    def negotiate(
        cls,
        romi_capability: RomiCapability | None,
        sdk_capability_table: SdkCapabilityTable | None = None,
    ) -> Self:
        """discover で得た Romi の capability から、実際に使用する API バージョンを決定する。

        Parameters
        ----------
        romi_capability : RomiCapability | None
            discover レスポンスで得られた Romi のケイパビリティ情報。
            capability に未対応の古い FW では None。
        sdk_capability_table : SdkCapabilityTable | None, optional
            SDK が対応する API バージョンのテーブル。
            None の場合は :data:`SDK_CAPABILITY_TABLE` を使用する。

        Returns
        -------
        NegotiatedCapability
            API ごとに実際に使用するバージョンを保持するオブジェクト。
            ``romi_capability`` が None の場合はすべて空になる。
        """
        if sdk_capability_table is None:
            sdk_capability_table = SDK_CAPABILITY_TABLE
        if romi_capability is None:
            return cls()

        return cls(
            # SDK→Romi は SDK 側でローカルネゴシエートする。
            to_romi_request=cls._negotiate_category(
                sdk_capability_table.to_romi_request, romi_capability.to_romi_request
            ),
            # Romi→SDK は Romi 側がネゴシエート済みの結果を返すため、SDK は
            # resolved_from_romi_request をそのまま採用する。
            from_romi_request=cls._adopt_resolved(
                romi_capability.resolved_from_romi_request
            ),
        )

    @staticmethod
    def _adopt_resolved(resolved_entries: list[CapabilityEntry]) -> dict[str, str]:
        """Romi がネゴシエート済みの ``resolved_from_romi_request`` を採用する。

        各エントリの ``versions`` は 1 件（使用可能）または 0 件（共通版なし＝
        使用不可）のいずれか。1 件あればそのバージョンを採用し、0 件のエントリは
        使用不可として dict に含めない。
        """
        adopted: dict[str, str] = {}
        for entry in resolved_entries:
            if not entry.versions:
                logger.debug(
                    f"API '{entry.name}' has no negotiated version from this Romi. "
                    "This API cannot be used."
                )
                continue
            adopted[entry.name] = entry.versions[0].version
        return adopted

    @classmethod
    def _negotiate_category(
        cls,
        sdk_entries: list[CapabilityEntry],
        romi_entries: list[CapabilityEntry],
    ) -> dict[str, str]:
        """
        SDK と Romi のエントリを突き合わせ、使用可能な最新バージョンを決定する。
        """
        romi_entries_by_name = {entry.name: entry for entry in romi_entries}
        negotiated: dict[str, str] = {}
        for sdk_entry in sdk_entries:
            romi_entry = romi_entries_by_name.get(sdk_entry.name)
            if romi_entry is None:
                logger.debug(f"API '{sdk_entry.name}' is not exposed by this Romi.")
                continue
            version = cls._negotiate_entry_version(sdk_entry, romi_entry)
            if version is None:
                logger.debug(
                    f"API '{sdk_entry.name}' is exposed by this Romi but no "
                    "compatible version exists. This API cannot be used."
                )
                continue
            negotiated[sdk_entry.name] = version
        return negotiated

    @staticmethod
    def _encode_request_type(api: str, version: str) -> str:
        """API 名と解決済みバージョンから、ワイヤに載せる request_type 文字列を返す。

        符号化スキーム（区切り文字は ``_v``）::

            ("speak_text", "1")  -> "speak_text"
            ("speak_text", "2")  -> "speak_text_v2"
            ("speak_text", "10") -> "speak_text_v10"
        """
        if version == _BASELINE_VERSION:
            return api
        return f"{api}_v{version}"

    @staticmethod
    def _negotiate_entry_version(
        sdk_entry: CapabilityEntry, romi_entry: CapabilityEntry
    ) -> str | None:
        """
        SDK と Romi のエントリから、使用可能な最新バージョンを決定する。
        """
        sdk_versions = {
            v.version for v in sdk_entry.versions if v.state in _USABLE_STATES
        }
        romi_versions = {
            v.version for v in romi_entry.versions if v.state in _USABLE_STATES
        }
        common_versions = sdk_versions & romi_versions
        if not common_versions:
            return None

        return max(common_versions, key=lambda version: int(version))
