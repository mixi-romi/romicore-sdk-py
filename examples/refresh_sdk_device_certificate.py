# このサンプルコードは、SDK デバイス証明書の更新を行う例です。
# CSR（証明書署名要求）を生成して Romi 経由で新しい証明書を取得し、
# CA チェーンとクライアント証明書をファイルに保存します。

import logging
import asyncio
from pathlib import Path

from romicoresdk import SDK

logging.basicConfig(level=logging.INFO)

HOST = "romi-l01-0123456789.local"  # mDNS host name を指定してください
BROKER_PORT = 443

TARGET_ROMI_ID = "romi-l01-0123456789"  # 制御する Romi の ID

CERTS_PATH = "/path/to/your/certs"  # TLS証明書のディレクトリパスを指定してください


async def main():
    # TLS 鍵を指定して SDK インスタンスを生成
    sdk = SDK.create(HOST, BROKER_PORT, certs_dir=Path(CERTS_PATH))
    key_path = Path(CERTS_PATH) / "client.key"
    ca_chain_path = Path(CERTS_PATH) / "ca.crt"
    cert_path = Path(CERTS_PATH) / "client.crt"
    # CSR を生成
    csr_string = sdk._generate_csr(str(key_path))
    # MQTT ブローカーに接続する
    try:
        await sdk.connect()
    except Exception as e:
        logging.error(f"Failed to connect to MQTT broker: {e}")
        return

    # ブローカーに接続されている SDK-mode が有効な Romi を検出
    romi_list = await sdk.discover_romis(timeout=5)

    # 対象の Romi を検索
    romi = None
    for r in romi_list:
        if r.id == TARGET_ROMI_ID:
            romi = r
            break

    if romi is None:
        logging.error(f"Target Romi '{TARGET_ROMI_ID}' not found.")
        return

    logging.info(f"Found target Romi: {romi.id}")

    try:
        # RomiにSDKデバイス証明書の更新をリクエスト
        response = await romi.refresh_sdk_device_certificate(csr_string)
    except Exception as e:
        logging.error(f"Failed to refresh SDK device certificate: {e}")
        return
    logging.info(f"SDK device certificate refreshed successfully for Romi {romi.id}.")
    # ca_chainとclient_certをファイルに保存
    with open(ca_chain_path, "w") as f:
        f.write(response.ca_chain)
    with open(cert_path, "w") as f:
        f.write(response.certificate)


if __name__ == "__main__":
    asyncio.run(main())
