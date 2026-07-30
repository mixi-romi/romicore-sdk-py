class RomiCoreSdkError(Exception):
    """RomiCore SDK が送出する例外の基底クラス。

    SDK 由来の例外はこのクラスを継承する。利用者は ``RomiCoreSdkError`` を捕捉することで
    SDK 起因のエラーをまとめてハンドリングできる。
    """


class CapabilityNotSupportedError(RomiCoreSdkError):
    """対象 Romi が対応していない API を呼び出した場合に送出される例外。

    capability ネゴシエーションの結果、SDK と Romi の間で使用可能な共通バージョンが
    存在しない（もしくは Romi が当該 API を提供していない）API を呼び出そうとしたときに
    送出される。
    """

    def __init__(self, api: str):
        self.api = api
        super().__init__(f"API '{api}' is not supported by this Romi ")
