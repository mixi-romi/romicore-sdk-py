from enum import StrEnum
from typing import Annotated
from pydantic import BaseModel, Field, field_validator


class CapabilityVersionState(StrEnum):
    """API バージョンの状態。"""

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    REMOVED = "removed"


class VersionDescriptor(BaseModel):
    """API の単一バージョンエントリ。"""

    version: Annotated[str, Field(title="バージョン番号")]
    state: Annotated[CapabilityVersionState, Field(title="バージョン状態")]
    sunset: Annotated[
        str | None, Field(default=None, title="廃止予定日 (deprecated 時のみ)")
    ] = None

    @field_validator("version")
    @classmethod
    def version_must_be_numeric(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError(f"version must be a numeric string, got '{v}'")
        return v


class CapabilityEntry(BaseModel):
    """名前とバージョン一覧を持つ API エントリ。"""

    name: Annotated[str, Field(title="API 名")]
    versions: Annotated[list[VersionDescriptor], Field(title="サポートバージョン一覧")]
    response_timeout_ms: Annotated[
        int | None,
        Field(
            default=None,
            title="ファームウェアが応答を待つ上限 (ミリ秒)",
            description="from_romi_request エントリ専用。to_romi_request では None。",
        ),
    ] = None


class RomiCapability(BaseModel):
    """Romi のケイパビリティ情報。

    ``to_romi_request`` は Romi 自身が対応する全バージョンの静的広告であり、
    SDK 側でローカルにネゴシエートする（SDK→Romi 方向）。
    ``resolved_from_romi_request`` は Romi 側が SDK の申告と突き合わせて
    ネゴシエート済みの結果（Romi→SDK 方向）で、エントリごとに ``versions`` が
    1 件（使用可能）または 0 件（共通版なし＝使用不可）になる。
    """

    protocol_version: Annotated[int, Field(title="プロトコルバージョン")]
    firmware_version: Annotated[str, Field(title="ファームウェアバージョン (情報のみ)")]
    to_romi_request: Annotated[
        list[CapabilityEntry], Field(title="SDK→Romi で叩ける API 一覧")
    ]
    resolved_from_romi_request: Annotated[
        list[CapabilityEntry],
        Field(
            title="ネゴシエート済みの Romi→SDK リクエスト一覧",
            description="エントリごとに versions は 1 件（使用可能）または 0 件（使用不可）。",
        ),
    ] = Field(default_factory=list)
