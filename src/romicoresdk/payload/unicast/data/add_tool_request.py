from enum import StrEnum
from typing import Annotated
from pydantic import BaseModel, Field

from .base import RequestData


class ToolSkill(StrEnum):
    """
    ツールが呼び出された際に、Romi が内部で実行する処理の種類。

    各処理の挙動は以下のとおりです。

    - ``RESET_CONVERSATION``: 会話セッションをリセットします。

    - ``DOWNLOAD_PICTURE``: ``get_resource_url`` リクエストを発行し、
    得られた URL から画像をダウンロードして、会話モデルに渡します。
    利用方法は ``examples/respond_resource_url.py`` を参照してください。

    - ``NO_OPERATION``: Romi 側では特別な処理をしません。
    """

    RESET_CONVERSATION = "reset_conversation"
    DOWNLOAD_PICTURE = "download_picture"
    NO_OPERATION = "no_operation"


class ToolProperty(BaseModel):
    """
    ツールのプロパティ
    """

    description: Annotated[
        str,
        Field(
            title="ツールの説明",
            examples=["買い物リストにアイテムを追加します。"],
        ),
    ]
    parameters: Annotated[
        str | None,
        Field(
            title="ツールのパラメータ定義 (JSON Schema 形式)",
            description=(
                "ツールが受け取る引数の定義を JSON Schema 形式の文字列で指定します。"
                "省略（None）可能で、引数が不要なツールでは未指定にします。\n\n"
                "指定する場合の制約:\n"
                "- 構文的に正しい JSON 文字列であること。\n"
                "- トップレベルが JSON オブジェクト ``{ ... }`` であること（配列やスカラーは不可）。\n"
                "- 形式は OpenAI Realtime API の function tool ``parameters`` に準拠した"
                " JSON Schema（``type: object`` + ``properties`` + 任意で ``required``）を推奨します。\n"
            ),
            examples=[
                '{"type": "object", "properties": {"item": {"type": "string", "description": "追加する商品名"}}, "required": ["item"]}'
            ],
        ),
    ] = None
    additional_base_instruction: Annotated[
        str,
        Field(
            title="ツール呼び出しのためのインストラクション",
            description="どのような場合にこのツールが呼び出されるべきかを具体的に指示してください。ツールの名称を必ず含めてください。",
            examples=[
                "ユーザーが買い物リストへの追加を依頼した場合（例：「牛乳を追加して」「卵も買わなきゃ」など）に、add_shopping_item を呼び出す。"
            ],
        ),
    ]
    additional_response_instruction: Annotated[
        str,
        Field(
            title="ツール実行時のレスポンス生成で個別に追加するインストラクション",
            description="通常時はこのインストラクションは使用されません。ツール実行時のみ追加されてレスポンスが生成されます。",
            examples=[
                "買い物リストにアイテムを追加したことをユーザーに伝えてください。"
            ],
        ),
    ]
    skill: Annotated[
        ToolSkill, Field(title="ツール呼び出し時に Romi 内部で実行する処理の種類")
    ]


class AddToolRequestData(RequestData):
    """
    ツールを追加するためのペイロードデータクラス
    """

    name: Annotated[str, Field(title="ツールの名前", examples=["add_shopping_item"])]
    property: Annotated[ToolProperty, Field(title="ツールのプロパティ")]
