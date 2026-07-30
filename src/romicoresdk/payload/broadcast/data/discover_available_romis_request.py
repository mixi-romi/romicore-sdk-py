from typing import Annotated

from pydantic import BaseModel, Field

from ...unicast.data.capability import CapabilityEntry


class SdkCapabilityDeclaration(BaseModel):
    """discover リクエストで SDK が Romi へ申告するケイパビリティ情報。

    SDK は Romi→SDK 方向（``from_romi_request``、例 ``get_resource_url``）で
    自分が対応するバージョン一覧を申告する。Romi 側はこれと自身の対応表を
    突き合わせてネゴシエートし、結果を discover レスポンスの
    ``resolved_from_romi_request`` として返す。

    SDK→Romi 方向（``to_romi_request``）は Romi が全対応版を静的広告し、
    SDK 側でローカルにネゴシエートするため、この申告には含めない。
    """

    protocol_version: Annotated[int, Field(title="プロトコルバージョン")] = 1
    sdk_version: Annotated[
        str | None, Field(default=None, title="SDK バージョン (情報/ログ用)")
    ] = None
    from_romi_request: Annotated[
        list[CapabilityEntry],
        Field(title="SDK が対応する Romi→SDK リクエスト一覧"),
    ] = Field(default_factory=list)


class DiscoverAvailableRomisRequestData(BaseModel):
    """
    利用可能な Romi の発見リクエストのペイロードデータクラス
    """

    capability: Annotated[
        SdkCapabilityDeclaration | None,
        Field(default=None, title="SDK のケイパビリティ申告"),
    ] = None
