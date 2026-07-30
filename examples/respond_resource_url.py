# このサンプルコードは、ツールと連携して、
# RomiからのリソースURL取得リクエストに応答する例です。
# 具体的には、画像ダウンロード用のツールを登録し、Romiがツールを呼び出した際に
# 画像のURLを返すことで、Romiが外部の画像を取得して会話に活用できるようにします。

import logging
import asyncio
from pathlib import Path

from romicoresdk import SDK
from romicoresdk import ToolSkill

logging.basicConfig(level=logging.INFO)

HOST = "romi-l01-0123456789.local"  # mDNS host name を指定してください
BROKER_PORT = 443

TARGET_ROMI_ID = "romi-l01-0123456789"  # 制御する Romi の ID

CERTS_PATH = "/path/to/your/certs"  # TLS証明書のディレクトリパスを指定してください

# 黒い犬の画像URL from https://picsum.photos/
RESOURCE_URL = "https://picsum.photos/id/237/400/300"


async def main():
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

    # 画像をダウンロードして発話するツールを追加
    try:
        # Romi にツールを追加
        await romi.add_tool(
            name="download_picture",
            description="画像をダウンロードして取得した画像を元にユーザーへのアドバイスや感想、共感を行うための判断材料にします。",
            parameters=None,
            additional_base_instruction="ユーザーが「ダウンロードして」と発話したら必ずdownload_pictureを必ず1回呼び出して新しい画像のみを解釈する。直前の画像が残っていても再利用しない。",
            additional_response_instruction="直前のユーザーの画像情報を元に、画像に映っている内容について反応してください。",
            skill=ToolSkill.DOWNLOAD_PICTURE.value,
        )
    except Exception as e:
        logging.error(f"Failed to add tool: {e}")
        return
    logging.info("Tool added successfully.")

    # ツール呼び出しの結果として、RomiからリソースURL取得リクエストが来るのを待機
    try:
        request = await romi.wait_for_get_resource_url_request()
    except (KeyboardInterrupt, asyncio.CancelledError):
        logging.info("Stopped by user.")
        return
    logging.info(
        f"Received Get Resource URL Request: "
        f"resource_id={request.resource_id}, type={request.resource_type}"
    )

    # リクエストに対して画像URLを含むレスポンスを返す
    await romi.respond_get_resource_url_success(
        request_id=request.request_id,
        resource_id=request.resource_id,
        url=RESOURCE_URL,
    )
    logging.info("Responded to Get Resource URL Request.")


if __name__ == "__main__":
    asyncio.run(main())
