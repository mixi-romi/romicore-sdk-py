from pathlib import Path
import yaml
from romicoresdk.payload.unicast.to_romi_request_payload import ToRomiRequestPayload
from romicoresdk.payload.unicast.to_romi_response_payload import ToRomiResponsePayload
from romicoresdk.payload.unicast.from_romi_request_payload import FromRomiRequestPayload
from romicoresdk.payload.unicast.from_romi_response_payload import (
    FromRomiResponsePayload,
)
from romicoresdk.payload.broadcast.broadcast_request_payload import (
    BroadcastRequestPayload,
)
from romicoresdk.payload.event.event_payload import EventPayload
from pydantic import TypeAdapter


# OpenAPIはdiscriminatorのmapping表記をサポートしているが、AsyncAPIはサポートしていないための対応。
# AsyncAPIもサポートしたらこの処理は不要になる。
# 関連issues: https://github.com/asyncapi/spec/issues/1073
def simplify_discriminator(schema: dict) -> dict:
    """discriminator オブジェクトを propertyName の値だけに変換する"""
    if isinstance(schema, dict):
        for key, value in schema.items():
            if (
                key == "discriminator"
                and isinstance(value, dict)
                and "propertyName" in value
            ):
                schema[key] = value["propertyName"]
            elif isinstance(value, (dict, list)):
                simplify_discriminator(value)
    elif isinstance(schema, list):
        for item in schema:
            if isinstance(item, dict):
                simplify_discriminator(item)
    return schema


def generate_and_save_schema(payload_class, output_filename: str) -> None:
    """ペイロードクラスのスキーマを生成し、YAMLファイルに保存"""
    schema = simplify_discriminator(TypeAdapter(payload_class).json_schema())
    output_path = Path(f"schemas/{output_filename}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(schema, f, allow_unicode=True, sort_keys=False)


generate_and_save_schema(BroadcastRequestPayload, "broadcast_request_payload.yaml")
generate_and_save_schema(ToRomiRequestPayload, "to_romi_request_payload.yaml")
generate_and_save_schema(FromRomiRequestPayload, "from_romi_request_payload.yaml")
generate_and_save_schema(ToRomiResponsePayload, "to_romi_response_payload.yaml")
generate_and_save_schema(FromRomiResponsePayload, "from_romi_response_payload.yaml")
generate_and_save_schema(EventPayload, "event_payload.yaml")
