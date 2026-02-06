# home_tab.py
from typing import List, Dict
from slack_sdk.web.client import WebClient


def build_home_blocks(status_text: str = "未確認") -> List[Dict]:
    """
    App Home 用の Block Kit を作成する

    :param status_text: Wrike / MCP などの状態表示用テキスト
    :return: blocks
    """
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "🤖 slack-wrike-bot"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "こんにちは！ *slack-wrike-bot* です。\nここでは接続確認を行えます。"
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*接続ステータス*\n{status_text}"
                }
            ]
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "🔄 接続を確認"
                    },
                    "action_id": "refresh_home"
                },
            ]
        },
    ]

    return blocks


def update_home_tab(client: WebClient, user_id: str, status_text: str = "未確認"):
    """
    App Home タブを更新する

    :param client: Slack WebClient (Bolt から渡される client)
    :param user_id: Home を表示するユーザー ID
    :param status_text: 状態表示テキスト
    """
    blocks = build_home_blocks(status_text)

    client.views_publish(
        user_id=user_id,
        view={
            "type": "home",
            "blocks": blocks
        }
    )
