# このサンプルコードでは、Romiにツールを登録し、その呼び出しを待機する例を示します。
# 具体的には、Romiに「買い物リスト管理」のツールを登録し、
# ユーザーの発話によって買い物アイテムが追加されるのを待機します。
# 例えば「牛乳を買い物リストに追加して」「卵3つ追加」などと話しかけると、
# ツール呼び出しが発火し、引数からアイテム名と個数を取得できます。

import json
import logging
import asyncio
from pathlib import Path

from romicoresdk import SDK
from romicoresdk import (
    AddToolRequestData,
    ToolProperty,
    ToolSkill,
)

logging.basicConfig(level=logging.INFO)

HOST = "romi-l01-0123456789.local"  # mDNS host name を指定してください
BROKER_PORT = 443

TARGET_ROMI_ID = "romi-l01-0123456789"  # 制御する Romi の ID

CERTS_PATH = "/path/to/your/certs"  # TLS証明書のディレクトリパスを指定してください

# 買い物リスト (メモリ上で管理)
shopping_list: list[dict] = []


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

    # Romi に「買い物リスト追加」のツールを登録
    tool_prop = ToolProperty(
        description="買い物リストにアイテムを追加します。",
        parameters=json.dumps(
            {
                "type": "object",
                "properties": {
                    "item": {
                        "type": "string",
                        "description": "追加する商品名",
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "個数",
                        "default": 1,
                    },
                },
                "required": ["item"],
            }
        ),
        additional_base_instruction=(
            "ユーザーが買い物リストへの追加を依頼した場合"
            "（例：「牛乳を買い物リストに追加して」「卵3つ追加」「パンも買わなきゃ」など）に、"
            "add_shopping_item を呼び出す。"
        ),
        additional_response_instruction=(
            "買い物リストにアイテムを追加したことをユーザーに伝えてください。"
        ),
        skill=ToolSkill.NO_OPERATION,
    )
    tool = AddToolRequestData(
        name="add_shopping_item",
        property=tool_prop,
    )
    try:
        await romi.add_tool(tool)
    except Exception as e:
        logging.error(f"Failed to add tool: {e}")
        return
    logging.info("Tool 'add_shopping_item' registered.")

    # ツール呼び出しリクエストを無限ループで待機
    logging.info("Waiting for tool call requests... (Ctrl+C to stop)")
    try:
        while True:
            requested_tool_call = await romi.wait_for_tool_call()

            # 引数を JSON からパース
            args = json.loads(requested_tool_call.arguments_json)
            item = args.get("item", "不明")
            quantity = args.get("quantity", 1)

            # 買い物リストに追加
            shopping_list.append({"item": item, "quantity": quantity})
            logging.info(f"Added: {item} x{quantity}")

            # 現在の買い物リストを表示
            logging.info("--- Shopping List ---")
            for i, entry in enumerate(shopping_list, 1):
                logging.info(f"  {i}. {entry['item']} x{entry['quantity']}")
            logging.info("---------------------")
    except (KeyboardInterrupt, asyncio.CancelledError):
        logging.info("Stopped by user.")


if __name__ == "__main__":
    asyncio.run(main())
