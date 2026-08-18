"""SDK の接続状態通知（payload / トピック）のテスト。"""

import json

import pytest
from paho.mqtt.client import topic_matches_sub
from pydantic import TypeAdapter, ValidationError

from romicoresdk.payload.event.data.connection_status import (
    ConnectionStatus,
    OfflineReason,
    OfflineStatusData,
    OnlineStatusData,
)
from romicoresdk.payload.event.event_payload import (
    ConnectionStatusChangedEventPayload,
    EventPayload,
    EventType,
)
from romicoresdk.topic.topic_name_manager import TopicNameManager


def test_online_payload_wire_format() -> None:
    """online 通知は reason を持たない形にシリアライズされる。"""
    payload = ConnectionStatusChangedEventPayload(
        type=EventType.CONNECTION_STATUS_CHANGED,
        event_id="py-sdk-testid-0",
        data=OnlineStatusData(),
    )

    assert json.loads(payload.model_dump_json()) == {
        "event_id": "py-sdk-testid-0",
        "type": "connection_status_changed",
        "data": {"status": "online"},
    }


@pytest.mark.parametrize(
    "reason,expected",
    [
        (OfflineReason.SHUTDOWN, "shutdown"),
        (OfflineReason.LAST_WILL, "last_will"),
    ],
)
def test_offline_payload_wire_format(reason: OfflineReason, expected: str) -> None:
    """offline 通知は reason を含む形にシリアライズされる。"""
    payload = ConnectionStatusChangedEventPayload(
        type=EventType.CONNECTION_STATUS_CHANGED,
        event_id="py-sdk-testid-1",
        data=OfflineStatusData(reason=reason),
    )

    assert json.loads(payload.model_dump_json()) == {
        "event_id": "py-sdk-testid-1",
        "type": "connection_status_changed",
        "data": {"status": "offline", "reason": expected},
    }


def test_offline_requires_reason() -> None:
    """offline では reason が必須。"""
    with pytest.raises(ValidationError):
        OfflineStatusData()  # ty: ignore[missing-argument]


def test_online_never_carries_reason() -> None:
    """online に reason を紛れ込ませてもワイヤには載らない。

    ``status`` を discriminator とするユニオンなので ``online`` は
    ``OnlineStatusData`` として解釈され、``reason`` は同モデルに存在しない
    余剰フィールドとして落ちる。
    """
    adapter = TypeAdapter(EventPayload)
    payload = adapter.validate_python(
        {
            "event_id": "py-sdk-testid-0",
            "type": "connection_status_changed",
            "data": {"status": "online", "reason": "shutdown"},
        }
    )

    assert isinstance(payload.data, OnlineStatusData)
    assert "reason" not in OnlineStatusData.model_fields
    assert json.loads(payload.model_dump_json())["data"] == {"status": "online"}


def test_payload_discriminated_by_status() -> None:
    """status の値に応じて data のモデルが判別される。"""
    adapter = TypeAdapter(EventPayload)

    online = adapter.validate_python(
        {
            "event_id": "e0",
            "type": "connection_status_changed",
            "data": {"status": "online"},
        }
    )
    assert isinstance(online.data, OnlineStatusData)
    assert online.data.status == ConnectionStatus.ONLINE
    assert online.type == EventType.CONNECTION_STATUS_CHANGED

    offline = adapter.validate_python(
        {
            "event_id": "e1",
            "type": "connection_status_changed",
            "data": {"status": "offline", "reason": "last_will"},
        }
    )
    assert isinstance(offline.data, OfflineStatusData)
    assert offline.data.reason == OfflineReason.LAST_WILL


def test_get_publish_event_topic() -> None:
    """SDK の publish 先イベントトピックは {sdk_id}/event。"""
    topic_manager = TopicNameManager("py-sdk-testid")

    assert topic_manager.get_publish_event_topic() == "romicoresdk/py-sdk-testid/event"


def test_publish_event_topic_is_not_processed_as_romi_event() -> None:
    """SDK 自身の publish 先は購読フィルタにマッチするが、処理対象にはならない。

    購読フィルタ ``romicoresdk/+/event`` は romi_id と sdk_id を区別できない
    ため自分のイベントも届くが、``parse_event_topic`` が False を返すことで
    読み捨てられる。
    """
    topic_manager = TopicNameManager("py-sdk-testid")
    own_topic = topic_manager.get_publish_event_topic()

    # 購読フィルタにはマッチしてしまう
    assert topic_matches_sub(topic_manager.get_subscribe_event_topic(), own_topic)
    # が、処理対象としては弾かれる
    assert topic_manager.parse_event_topic(own_topic) is False
    # Romi 発のイベントは従来どおり処理対象になる
    assert topic_manager.parse_event_topic("romicoresdk/romi-l01-0001/event") is True
