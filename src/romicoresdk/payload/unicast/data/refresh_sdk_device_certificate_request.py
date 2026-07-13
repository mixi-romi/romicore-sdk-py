from typing import Annotated
from pydantic import Field

from .base import RequestData


class RefreshSdkDeviceCertificateRequestData(RequestData):
    """
    SDK デバイス証明書の更新するためのリクエストのペイロードデータクラス
    """

    csr: Annotated[
        str,
        Field(
            title="CSR文字列",
            description="証明書署名要求（CSR）を設定します。",
            examples=[
                "-----BEGIN CERTIFICATE REQUEST-----\n*******\n-----END CERTIFICATE REQUEST-----"
            ],
        ),
    ]
