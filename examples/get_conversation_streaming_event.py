# このサンプルコードは、Romi の conversation_streaming イベントを受信する例です。
# start_conversation_stream でストリームを開始し、イベントを待ち受けます。

import asyncio
import logging
from pathlib import Path

from romicoresdk import SDK
from romicoresdk import ConversationSpeaker

logging.basicConfig(level=logging.INFO)

HOST = "romi-l01-0123456789.local"  # mDNS host name を指定してください
BROKER_PORT = 443

TARGET_ROMI_ID = "romi-l01-0123456789"  # 制御する Romi の ID

CERTS_PATH = "/path/to/your/certs"  # TLS証明書のディレクトリパスを指定してください


async def main() -> None:
    sdk = SDK.create(HOST, BROKER_PORT, certs_dir=Path(CERTS_PATH))

    try:
        await sdk.connect()
    except Exception as e:
        logging.error(f"Failed to connect to MQTT broker: {e}")
        return

    romi_list = await sdk.discover_romis(timeout=5)

    romi = next((r for r in romi_list if r.id == TARGET_ROMI_ID), None)
    if romi is None:
        logging.error(f"Target Romi '{TARGET_ROMI_ID}' not found.")
        return

    logging.info(f"Found target Romi: {romi.id}")

    try:
        # Romiへ発話ストリーミング開始要求
        await romi.start_conversation_stream(speaker=ConversationSpeaker.ROMI.value)
        logging.info("Started conversation stream. Waiting for events...")
        # 発話ストリーミング通知受信ループ
        while True:
            event = await romi.wait_for_conversation_streaming_event()
            logging.info(
                "conversation_streaming received: "
                f"speaker={event.speaker}, text={event.utterance_text}, timestamp={event.timestamp}"
            )
    except (KeyboardInterrupt, asyncio.CancelledError):
        logging.info("Stopped by user")
    finally:
        try:
            await romi.stop_conversation_stream()
            logging.info("Stopped conversation stream")
        except Exception as e:
            logging.warning(f"Failed to stop conversation stream: {e}")


if __name__ == "__main__":
    asyncio.run(main())
