# このサンプルコードは、指定した Romi から登録済みツールを削除する例です。

import asyncio
import logging
from pathlib import Path

from romicoresdk import SDK

logging.basicConfig(level=logging.INFO)

HOST = "romi-l01-0123456789.local"  # mDNS host name を指定してください
BROKER_PORT = 443

TARGET_ROMI_ID = "romi-l01-0123456789"  # 制御する Romi の ID

CERTS_PATH = "/path/to/your/certs"  # TLS証明書のディレクトリパスを指定してください
# 削除するツールの名前 (Romi にツールを登録する際に指定した name)
TOOL_NAME = "target"


async def main() -> None:
    # TLS 鍵を指定して SDK インスタンスを生成
    sdk = SDK.create(HOST, BROKER_PORT, certs_dir=Path(CERTS_PATH))

    # ブロックを抜けるときに Romi へ切断を通知してから接続を閉じる
    async with sdk:
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

        # 指定したツールを削除
        try:
            await romi.remove_tool(TOOL_NAME)
        except Exception as e:
            logging.error(f"Failed to remove tool '{TOOL_NAME}': {e}")
            return

        logging.info(f"Tool '{TOOL_NAME}' removed successfully.")


if __name__ == "__main__":
    asyncio.run(main())
