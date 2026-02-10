import sys
import re
import time
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient

from lib.config import (
    SLACK_BOT_TOKEN,
    SLACK_APP_TOKEN,
    WRIKE_FOLDERS,
)
from lib.wrike_api import get_all_tasks, create_task_in_wrike
from lib.home_tab import update_home_tab
from services.delete_bot_message import delete_bot_message
from services.token_check import (
    check_slack_token,
    check_wrike_token,
)
from services.facilitator_daily import start_facilitator_scheduler

app = App(token=SLACK_BOT_TOKEN)
BOT_ID = app.client.auth_test()["user_id"]
client = WebClient(token=SLACK_BOT_TOKEN)

# 定時ファシリテーター通知
start_facilitator_scheduler(app)


# Home タブ
@app.event("app_home_opened")
def handle_app_home_opened(event, client, logger):
    user_id = event["user"]
    logger.info(f"app_home_opened by {user_id}")
    update_home_tab(client, user_id)

@app.action("refresh_home")
def refresh_home(ack, body, client):
    ack()
    user_id = body["user"]["id"]

    update_home_tab(client, user_id, status_text="読み込み中…")

    slack_ok = check_slack_token(client)
    wrike_ok = check_wrike_token()

    status_text = (
        f"*Slack*: {'○' if slack_ok else '✖︎'}  "
        f"*Wrike*: {'○' if wrike_ok else '✖︎'}"
    )

    update_home_tab(client, user_id, status_text=status_text)


# アプリ内 Bot 発言削除コマンド
@app.command("/delete_dm")
def delete_dm_command(ack, body, client):
    ack()
    channel_id = body["channel_id"]

    notify = client.chat_postMessage(
        channel=channel_id,
        text="DM内のBot発言を削除しています…"
    )
    notify_ts = notify["ts"]

    has_more = True
    cursor = None
    deleted_count = 0

    while has_more:
        res = client.conversations_history(
            channel=channel_id,
            limit=100,
            cursor=cursor
        )

        for msg in res["messages"]:
            if msg.get("user") == BOT_ID:
                if delete_bot_message(client, channel_id, msg["ts"]):
                    deleted_count += 1

        has_more = res.get("has_more", False)
        cursor = res.get("response_metadata", {}).get("next_cursor")

    result = client.chat_postMessage(
        channel=channel_id,
        text=f"削除完了: {deleted_count-1} 件のメッセージを削除しました"
    )
    time.sleep(2)
    delete_bot_message(client, channel_id, result["ts"])
    delete_bot_message(client, channel_id, notify_ts)


# /add_task
@app.command("/add_task")
def open_task_modal_command(ack, body, client):
    ack()
    trigger_id = body["trigger_id"]
    channel_id = body["channel_id"]

    client.views_open(
        trigger_id=trigger_id,
        view={
            "type": "modal",
            "callback_id": "submit_task_modal",
            "title": {"type": "plain_text", "text": "タスク作成"},
            "submit": {"type": "plain_text", "text": "作成"},
            "close": {"type": "plain_text", "text": "キャンセル"},
            "private_metadata": channel_id,
            "blocks": [
                {
                    "type": "input",
                    "block_id": "folder_block",
                    "element": {
                        "type": "static_select",
                        "action_id": "folder_select",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "作成先フォルダを選択"
                        },
                        "options": [
                            {
                                "text": {"type": "plain_text", "text": name},
                                "value": folder_id
                            }
                            for name, folder_id in WRIKE_FOLDERS.items()
                        ]
                    },
                    "label": {"type": "plain_text", "text": "フォルダ"}
                },
                {
                    "type": "input",
                    "block_id": "task_title_block",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "task_title_input",
                        "placeholder": {"type": "plain_text", "text": "タスク名を入力"}
                    },
                    "label": {"type": "plain_text", "text": "タスク名"}
                },
                {
                    "type": "input",
                    "block_id": "task_desc_block",
                    "optional": True,
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "task_desc_input",
                        "multiline": True,
                        "placeholder": {"type": "plain_text", "text": "タスクの詳細"}
                    },
                    "label": {"type": "plain_text", "text": "タスク詳細"}
                }
            ]
        }
    )



# モーダル送信
@app.view("submit_task_modal")
def handle_task_modal_submission(ack, body, client):
    ack()
    values = body["view"]["state"]["values"]

    title = values["task_title_block"]["task_title_input"]["value"]
    description = values["task_desc_block"]["task_desc_input"]["value"]
    folder_id = values["folder_block"]["folder_select"]["selected_option"]["value"]

    folder_name = next(
        (name for name, fid in WRIKE_FOLDERS.items() if fid == folder_id),
        "不明なフォルダ"
    )

    created = create_task_in_wrike(
        title=title,
        description=description,
        folder_id=folder_id
    )

    channel_id = body["view"]["private_metadata"]
    user = body["user"]["username"]

    if created:
        client.chat_postMessage(
            channel=channel_id,
            text=f"{user} がタスク「{title}」を「{folder_name}」に作成しました。"
        )
    else:
        client.chat_postMessage(
            channel=channel_id,
            text=f"{user} のタスク作成に失敗しました。"
        )


# 起動
if __name__ == "__main__":
    print("Slack Bot 起動中...")
    try:
        handler = SocketModeHandler(app, SLACK_APP_TOKEN)
        handler.start()
    except Exception as e:
        print(f"[ERROR] SocketMode 起動エラー: {e}")
        sys.exit(1)