from typing import Annotated
from pydantic import Field

from .base import ResponseData


class GetResourceUrlResponseData(ResponseData):
    """
    リソースURLを応答するためのペイロードデータクラス
    """

    resource_id: Annotated[str, Field(title="リソースID")]
    url: Annotated[
        str,
        Field(
            title="リソースURL",
            examples=["https://example.com/image.jpg"],
        ),
    ]
