from enum import StrEnum


class RequestType(StrEnum):
    """
    SDK <-> Romi の通信で使用するリクエストのタイプ
    """

    # SDK -> Romi へ送るリクエスト
    DISCOVER_AVAILABLE_ROMIS = "discover_available_romis"
    ADD_TOOL = "add_tool"
    REMOVE_TOOL = "remove_tool"
    CREATE_ROMI_RESPONSE = "create_romi_response"
    # create_romi_responseのレスポンスがtext/emotion単体からutterancesリストへ
    # 変わった版。ネゴシエーションでv2が解決された場合にのみワイヤへ現れる。
    CREATE_ROMI_RESPONSE_V2 = "create_romi_response_v2"
    REFRESH_SDK_DEVICE_CERTIFICATE = "refresh_sdk_device_certificate"
    GET_REGISTERED_TOOLS = "get_registered_tools"
    START_CONVERSATION_STREAM = "start_conversation_stream"
    STOP_CONVERSATION_STREAM = "stop_conversation_stream"
    SPEAK_TEXT = "speak_text"

    # Romi -> SDK へ送られてくるリクエスト
    GET_RESOURCE_URL = "get_resource_url"

    # リクエストの payload パースに失敗し、Romi が request_type を特定できなかった
    # 場合にエラーレスポンスへ設定される種別
    UNSPECIFIED = "unspecified"
