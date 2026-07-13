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
    REFRESH_SDK_DEVICE_CERTIFICATE = "refresh_sdk_device_certificate"
    GET_REGISTERED_TOOLS = "get_registered_tools"
    START_CONVERSATION_STREAM = "start_conversation_stream"
    STOP_CONVERSATION_STREAM = "stop_conversation_stream"
    SPEAK_TEXT = "speak_text"

    # Romi -> SDK へ送られてくるリクエスト
    GET_RESOURCE_URL = "get_resource_url"
