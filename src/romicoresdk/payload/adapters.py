"""ペイロードのパースアダプタを束ねる注入シーム。

`SDK` は受信/送信ペイロードのパースに `TypeAdapter` を用いる。
ここで6つの `TypeAdapter` を1つの dataclass にまとめておき、`SDK` へ
注入できるようにすることで、公開ユニオン（既定）と拡張ユニオン（差し替え可能）を
切り替えられるようにする。

公開コアは常に既定（公開ユニオン）を使うため、挙動は従来どおり。
"""

from dataclasses import dataclass
from pydantic import TypeAdapter

from .unicast.to_romi_request_payload import DEFAULT_TO_ROMI_REQUEST_ADAPTER
from .unicast.to_romi_response_payload import DEFAULT_TO_ROMI_RESPONSE_ADAPTER
from .unicast.from_romi_request_payload import DEFAULT_FROM_ROMI_REQUEST_ADAPTER
from .unicast.from_romi_response_payload import DEFAULT_FROM_ROMI_RESPONSE_ADAPTER
from .broadcast.broadcast_request_payload import DEFAULT_BROADCAST_REQUEST_ADAPTER
from .event.event_payload import DEFAULT_EVENT_ADAPTER


@dataclass(frozen=True)
class PayloadAdapters:
    """SDK が用いる6つのペイロード TypeAdapter を束ねる軽量コンテナ。

    Parameters
    ----------
    broadcast_request : TypeAdapter
        ブロードキャストリクエスト（discover）のパースアダプタ
    to_romi_request : TypeAdapter
        Romi へ送るリクエストのパースアダプタ
    to_romi_response : TypeAdapter
        Romi へ送るレスポンスのパースアダプタ
    from_romi_request : TypeAdapter
        Romi から来るリクエストのパースアダプタ
    from_romi_response : TypeAdapter
        Romi から来るレスポンスのパースアダプタ
    event : TypeAdapter, optional
        event のパースアダプタ, by default DEFAULT_EVENT_ADAPTER
    """

    broadcast_request: TypeAdapter
    to_romi_request: TypeAdapter
    to_romi_response: TypeAdapter
    from_romi_request: TypeAdapter
    from_romi_response: TypeAdapter
    # event は非公開拡張を持たず差し替える動機がないため既定値を持たせる。
    # 5フィールドで構築していた既存の注入コードをそのまま動かすためでもある。
    event: TypeAdapter = DEFAULT_EVENT_ADAPTER


DEFAULT_ADAPTERS = PayloadAdapters(
    broadcast_request=DEFAULT_BROADCAST_REQUEST_ADAPTER,
    to_romi_request=DEFAULT_TO_ROMI_REQUEST_ADAPTER,
    to_romi_response=DEFAULT_TO_ROMI_RESPONSE_ADAPTER,
    from_romi_request=DEFAULT_FROM_ROMI_REQUEST_ADAPTER,
    from_romi_response=DEFAULT_FROM_ROMI_RESPONSE_ADAPTER,
    event=DEFAULT_EVENT_ADAPTER,
)
