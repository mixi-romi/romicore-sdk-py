class TopicNameManager:
    """topic 名を管理するクラス

    サブスクライブするトピックやパブリッシュするトピック名を生成、
    レスポンストピックの解析を行います。

    Parameters
    ----------
    sdk_id : str
        SDK ID
    """

    PREFIX = "romicoresdk"
    REQUEST_SUFFIX = "request"
    RESPONSE_SUFFIX = "response"
    EVENT_SUFFIX = "event"
    ROMI_ID_PREFIX = "romi-"
    TO_ROMI = "to_romi"
    FROM_ROMI = "from_romi"

    def __init__(self, sdk_id: str):
        self._sdk_id = sdk_id

    def get_broadcast_request_topic(self) -> str:
        """ブロードキャストリクエストトピックを取得する。

        フォーマット:
            romicoresdk/broadcast/{sdk_id}/request

        Returns
        -------
        str
            ブロードキャストリクエストトピック
        """
        return self._build_topic("broadcast", self._sdk_id, self.REQUEST_SUFFIX)

    def get_unicast_request_topic(self, romi_id: str) -> str:
        """指定された romi_id 向けのユニキャストリクエストトピックを取得する。

        フォーマット:
            romicoresdk/{romi_id}/{sdk_id}/to_romi/request

        Parameters
        ----------
        romi_id : str
            Romi デバイスの ID

        Returns
        -------
        str
            ユニキャストリクエストトピック
        """
        return self._build_topic(
            romi_id, self._sdk_id, self.TO_ROMI, self.REQUEST_SUFFIX
        )

    def get_unicast_response_topic(self, romi_id: str) -> str:
        """指定された romi_id 向けのユニキャストレスポンストピックを取得する。

        フォーマット:
            romicoresdk/{romi_id}/{sdk_id}/to_romi/response

        Parameters
        ----------
        romi_id : str
            Romi デバイスの ID

        Returns
        -------
        str
            ユニキャストレスポンストピック
        """
        return self._build_topic(
            romi_id, self._sdk_id, self.TO_ROMI, self.RESPONSE_SUFFIX
        )

    def get_subscribe_response_topic(self) -> str:
        """レスポンストピックのサブスクライブ用トピックを取得する。

        フォーマット:
            romicoresdk/+/{sdk_id}/from_romi/response

        Returns
        -------
        str
            レスポンストピックのサブスクライブ用トピック
        """
        return self._build_topic(
            "+", self._sdk_id, self.FROM_ROMI, self.RESPONSE_SUFFIX
        )

    def get_subscribe_request_topic(self) -> str:
        """リクエストトピックのサブスクライブ用トピックを取得する。

        フォーマット:
            romicoresdk/+/{sdk_id}/from_romi/request

        Returns
        -------
        str
            リクエストトピックのサブスクライブ用トピック
        """
        return self._build_topic("+", self._sdk_id, self.FROM_ROMI, self.REQUEST_SUFFIX)

    def get_subscribe_event_topic(self) -> str:
        """イベントトピックのサブスクライブ用トピックを取得する。

        フォーマット:
            romicoresdk/+/event

        Returns
        -------
        str
            イベントトピックのサブスクライブ用トピック
        """
        return self._build_topic("+", self.EVENT_SUFFIX)

    def parse_response_topic(self, topic: str) -> bool:
        """レスポンストピックを解析し、romi_id を取得する。

        フォーマット:
            romicoresdk/{romi_id}/{sdk_id}/from_romi/response

        Returns
        -------
        bool
            True または False (解析に失敗した場合)
        """
        return self._parse_topic(topic, self.RESPONSE_SUFFIX)

    def parse_request_topic(self, topic: str) -> bool:
        """リクエストトピックを解析し、romi_id を取得する。

        フォーマット:
            romicoresdk/{romi_id}/{sdk_id}/from_romi/request

        Returns
        -------
        bool
            True または False (解析に失敗した場合)
        """
        return self._parse_topic(topic, self.REQUEST_SUFFIX)

    def parse_event_topic(self, topic: str) -> bool:
        """イベントトピックを解析し、romi_id を取得する。

        フォーマット:
            romicoresdk/{romi_id}/event

        Returns
        -------
        bool
            True または False (解析に失敗した場合)
        """
        return self._parse_topic(topic, self.EVENT_SUFFIX)

    def _build_topic(self, *segments: str) -> str:
        """
        トピック文字列を構築する。
        """
        return "/".join((self.PREFIX, *segments))

    def _parse_topic(self, topic: str, expected_suffix: str) -> bool:
        """
        トピックを解析する。
        """
        tokens = topic.split("/")
        if len(tokens) == 5:
            # {prefix}/{romi_id}/{sdk_id}/from_romi/{suffix}
            prefix, romi_id, sdk_id, direction, suffix = tokens
            if sdk_id != self._sdk_id:
                return False
            if direction != self.FROM_ROMI:
                return False
        elif len(tokens) == 3:
            # {prefix}/{romi_id}/{suffix} (e.g. event)
            prefix, romi_id, suffix = tokens
        else:
            return False

        if (
            (prefix != self.PREFIX)
            or (suffix != expected_suffix)
            or (not romi_id)
            or (romi_id.startswith(self.ROMI_ID_PREFIX) is False)
        ):
            return False

        return True
