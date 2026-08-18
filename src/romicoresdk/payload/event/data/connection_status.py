from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Discriminator, Field

from .base import EventData


class ConnectionStatus(StrEnum):
    """SDK の接続状態。"""

    ONLINE = "online"
    OFFLINE = "offline"


class OfflineReason(StrEnum):
    """``offline`` になった理由。"""

    # SDK.disconnect() による正常終了
    SHUTDOWN = "shutdown"
    # 異常切断を検知したブローカーによる LWT (Last Will and Testament) 発火
    LAST_WILL = "last_will"


class OnlineStatusData(EventData):
    """connection_status_changed イベント（``online``）のデータ。

    ``reason`` は持たない。
    """

    status: Annotated[Literal[ConnectionStatus.ONLINE], Field(title="接続状態")] = (
        ConnectionStatus.ONLINE
    )


class OfflineStatusData(EventData):
    """connection_status_changed イベント（``offline``）のデータ。

    ``reason`` は必須。
    """

    status: Annotated[Literal[ConnectionStatus.OFFLINE], Field(title="接続状態")] = (
        ConnectionStatus.OFFLINE
    )
    reason: Annotated[OfflineReason, Field(title="切断理由")]


ConnectionStatusData = Annotated[
    OnlineStatusData | OfflineStatusData, Discriminator("status")
]
