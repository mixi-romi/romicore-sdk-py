"""Romi クラスの公開メソッドが返す、標準ライブラリの dataclass 群。

内部では pydantic の ResponseData/EventData を受信するが、利用者には
pydantic への依存を意識させないよう、ここに定義した dataclass に変換して返す。
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ToolCall:
    """Romi から要求されたツール呼び出し。"""

    name: str
    call_id: str
    arguments_json: str


@dataclass(frozen=True)
class ConversationStreamingEvent:
    """Romi からの会話ストリーミングイベント。"""

    speaker: str
    utterance_text: str
    timestamp: int


@dataclass(frozen=True)
class RomiUtterance:
    """Romi の発話単位（text, emotion）。"""

    text: str
    emotion: str | None


@dataclass(frozen=True)
class RomiResponse:
    """Romi が生成した発話のレスポンス。"""

    utterances: list[RomiUtterance]


@dataclass(frozen=True)
class SdkDeviceCertificate:
    """更新された SDK デバイス証明書。"""

    ca_chain: str
    certificate: str


@dataclass(frozen=True)
class ResourceUrlRequest:
    """Romi からのリソースURL取得リクエスト。

    ``request_id`` は ``Romi.respond_get_resource_url_success`` /
    ``respond_get_resource_url_error`` に渡してレスポンスを返すために使う。
    """

    request_id: str
    resource_id: str
    resource_type: str
    tool_name: str | None = None
