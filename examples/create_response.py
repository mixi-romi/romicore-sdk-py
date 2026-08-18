# このサンプルコードは、指定したRomiに、会話AIが生成した内容を発話させる例です。
# Romiユーザーの発話内容と応答の指示を組み合わせて、Romiの返答を生成します。

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

        try:
            # Romiに発話をリクエスト（Romiユーザーの発話内容と応答生成の指示を渡す）
            response = await romi.create_and_speak_response(
                instruction="朝のあいさつをしてください。明るい内容で最後にユーザーへ軽い質問を1つしてください。",
                user_utterance="おはよう",
                should_include_user_utterance_in_conversation_log=True,
            )
        except Exception as e:
            logging.error(f"Failed to create response: {e}")
            return
        for utterance in response.utterances:
            logging.info(
                f"Romi response created and spoken: {utterance.text} (emotion: {utterance.emotion})"
            )


if __name__ == "__main__":
    asyncio.run(main())
