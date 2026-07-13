from enum import StrEnum
from typing import Annotated
from pydantic import Field

from .base import RequestData


class ResourceType(StrEnum):
    """
    リソースタイプ
    """

    STREAMING_CONVERSATION_IMAGE_URL = "streaming_conversation_image_url"


class GetResourceUrlRequestData(RequestData):
    """
    リソースURL取得リクエストのペイロードデータクラス
    """

    resource_id: Annotated[str, Field(title="リソースID")]
    resource_type: Annotated[ResourceType, Field(title="リソースタイプ")]
    tool_name: Annotated[str | None, Field(title="ツール名")] = None
