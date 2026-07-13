# このサンプルコードは、指定した Romi に登録済みのツール一覧を取得する例です。

import asyncio
import logging
from pathlib import Path

from romicoresdk import SDK

logging.basicConfig(level=logging.INFO)

HOST = "romi-l01-0123456789.local"  # mDNS host name を指定してください
BROKER_PORT = 443

TARGET_ROMI_ID = "romi-l01-0123456789"  # 制御する Romi の ID

CERTS_PATH = "/path/to/your/certs"  # TLS証明書のディレクトリパスを指定してください


async def main() -> None:
    # TLS 鍵を指定して SDK インスタンスを生成
    sdk = SDK.create(HOST, BROKER_PORT, certs_dir=Path(CERTS_PATH))

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

    # Romi に登録済みのツール一覧を取得
    try:
        response = await romi.get_registered_tools()
    except Exception as e:
        logging.error(f"Failed to get registered tools: {e}")
        return

    logging.info("Registered tools:")
    if not response.tool_names:
        logging.info("  (none)")
        return

    for tool_name in response.tool_names:
        logging.info(f"  - {tool_name}")


if __name__ == "__main__":
    asyncio.run(main())
