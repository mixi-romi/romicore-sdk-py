from pydantic import BaseModel


class EventData(BaseModel):
    """event で受け渡すデータの共通基底クラス。

    `GetEventFutureMethod` などの型シグネチャで具体的な Event データクラスを
    すべて Union で列挙する代わりに、この基底クラスを参照する。
    """
