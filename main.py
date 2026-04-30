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
    WRIKE_MEMBERS,
    WRIKE_DYNAMIC_PARENTS,
)
from lib.wrike_api import get_all_tasks, create_task_in_wrike,get_child_folders
from services.delete_bot_message import delete_bot_message
from services.token_check import (
    check_slack_token,
    check_wrike_token,
)
from services.facilitator_daily import start_facilitator_scheduler,register_facilitator_actions

app = App(token=SLACK_BOT_TOKEN)
BOT_ID = app.client.auth_test()["user_id"]
client = WebClient(token=SLACK_BOT_TOKEN)

for name, parent_id in WRIKE_DYNAMIC_PARENTS.items():
    children = get_child_folders(parent_id)
    for child in children:
        if child["title"] not in WRIKE_FOLDERS:
            WRIKE_FOLDERS[child["title"]] = child["id"]

# 定時ファシリテーター通知
start_facilitator_scheduler(app)

# ファシリテーター承認 / パスのアクション登録
register_facilitator_actions(app)

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


# /create_task
@app.command("/create_task")
def open_task_modal_command(ack, body, client):
    ack()
    trigger_id = body["trigger_id"]
    channel_id = body["channel_id"]

    # config.py の固定メンバーリストから選択肢を生成
    user_options = [
        {
            "text": {"type": "plain_text", "text": name},
            "value": wrike_id
        }
        for name, wrike_id in WRIKE_MEMBERS.items()
    ]

    blocks = [
        {
            "type": "input",
            "block_id": "folder_block",
            "element": {
                "type": "static_select",
                "action_id": "folder_select",
                "placeholder": {"type": "plain_text", "text": "作成先フォルダを選択"},
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
                "placeholder": {"type": "plain_text", "text": "タスクの説明"}
            },
            "label": {"type": "plain_text", "text": "タスクの説明"}
        },
        {
            "type": "input",
            "block_id": "start_date_block",
            "optional": True,
            "element": {
                "type": "datepicker",
                "action_id": "start_date_select",
                "placeholder": {"type": "plain_text", "text": "開始日を選択"}
            },
            "label": {"type": "plain_text", "text": "開始日"}
        },
        {
            "type": "input",
            "block_id": "due_date_block",
            "optional": True,
            "element": {
                "type": "datepicker",
                "action_id": "due_date_select",
                "placeholder": {"type": "plain_text", "text": "期日を選択"}
            },
            "label": {"type": "plain_text", "text": "期日"}
        },
    ]

    # Wrikeユーザーが取得できた場合のみ担当者セレクトを追加
    if user_options:
        blocks.insert(3, {
            "type": "input",
            "block_id": "assignee_block",
            "optional": True,
            "element": {
                "type": "static_select",
                "action_id": "assignee_select",
                "placeholder": {"type": "plain_text", "text": "担当者を選択"},
                "options": user_options
            },
            "label": {"type": "plain_text", "text": "担当者"}
        })

    client.views_open(
        trigger_id=trigger_id,
        view={
            "type": "modal",
            "callback_id": "submit_task_modal",
            "title": {"type": "plain_text", "text": "タスク作成"},
            "submit": {"type": "plain_text", "text": "作成"},
            "close": {"type": "plain_text", "text": "キャンセル"},
            "private_metadata": channel_id,
            "blocks": blocks
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

    # 担当者（Wrike ID）
    assignee_block = values.get("assignee_block", {}).get("assignee_select", {})
    assignee_option = assignee_block.get("selected_option")
    assignee_id = assignee_option["value"] if assignee_option else None
    assignee_name = assignee_option["text"]["text"] if assignee_option else None

    # 日付
    start_date = values["start_date_block"]["start_date_select"].get("selected_date")
    due_date = values["due_date_block"]["due_date_select"].get("selected_date")

    folder_name = next(
        (name for name, fid in WRIKE_FOLDERS.items() if fid == folder_id),
        "不明なフォルダ"
    )

    responsibles = [assignee_id] if assignee_id else None

    created = create_task_in_wrike(
        title=title,
        description=description,
        folder_id=folder_id,
        responsibles=responsibles,
        start_date=start_date,
        due_date=due_date,
    )

    channel_id = body["view"]["private_metadata"]
    user_id = body["user"]["id"]

    user_info = client.users_info(user=user_id)
    profile = user_info["user"]["profile"]
    user_name = (
        profile.get("display_name")
        or profile.get("real_name")
        or body["user"]["username"]
    )

    if created:
        assignee_text = assignee_name if assignee_name else "未設定"
        date_text = ""
        if start_date and due_date:
            date_text = f"{start_date} 〜 {due_date}"
        elif start_date:
            date_text = f"{start_date} 〜"
        elif due_date:
            date_text = f"〜 {due_date}"
        else:
            date_text = "未設定"

        client.chat_postMessage(
            channel=channel_id,
            text=f"{user_name} さんが「{folder_name}」に「{title}」を作成しました",
        )
    else:
        client.chat_postMessage(
            channel=channel_id,
            text="タスク作成に失敗しました。"
        )


# 起動
if __name__ == "__main__":
    print("Starting Bot...")
    try:
        handler = SocketModeHandler(app, SLACK_APP_TOKEN)
        handler.start()
    except Exception as e:
        print(f"[ERROR] SocketMode startup error: {e}")
        sys.exit(1)