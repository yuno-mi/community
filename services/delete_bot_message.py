from slack_sdk.errors import SlackApiError

def delete_bot_message(client, channel_id: str, ts: str) -> bool:
    try:
        client.chat_delete(channel=channel_id, ts=ts)
        return True
    except SlackApiError as e:
        # message_not_found の場合は無視
        if e.response["error"] != "message_not_found":
            print(f"メッセージ削除エラー: {e.response['error']}")
        return False