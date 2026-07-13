from pydantic import BaseModel


class RequestData(BaseModel):
    """Romi へのリクエスト / Romi からのリクエストのデータ共通基底クラス。

    `RequesterMethod` などの型シグネチャで具体的な Request クラスを
    すべて Union で列挙する代わりに、この基底クラスを参照する。
    """


class ResponseData(BaseModel):
    """Romi からのレスポンス / Romi へのレスポンスのデータ共通基底クラス。"""
