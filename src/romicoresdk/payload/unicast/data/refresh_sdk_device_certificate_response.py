from typing import Annotated
from pydantic import Field

from .base import ResponseData


class RefreshSdkDeviceCertificateResponseData(ResponseData):
    """
    SDK デバイス証明書の更新に対するレスポンスのペイロードデータクラス
    """

    ca_chain: Annotated[
        str,
        Field(
            title="CAチェーン文字列",
            description="更新された SDK デバイス証明書の CA チェーンを設定します。",
            examples=[
                "-----BEGIN CERTIFICATE-----\n*******\n-----END CERTIFICATE-----"
            ],
        ),
    ]
    certificate: Annotated[
        str,
        Field(
            title="証明書文字列",
            description="更新された SDK デバイス証明書を設定します。",
            examples=[
                "-----BEGIN CERTIFICATE-----\n*******\n-----END CERTIFICATE-----"
            ],
        ),
    ]
