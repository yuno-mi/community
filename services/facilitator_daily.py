import threading
import time
import schedule
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from collections import deque
from lib.config import FACILITATORS, FACILITATOR_CHANNEL_ID, FACILITATOR_NOTIFY_TIME, PROGRESS_REPORT_TIME

STATE_FILE = Path("data/facilitator_state.json")
JST = timezone(timedelta(hours=9))

# state管理
def load_state():
    if not STATE_FILE.exists():
        return {"queue": list(FACILITATORS)}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
            if "queue" not in state or not state["queue"]:
                state["queue"] = list(FACILITATORS)
            return state
    except Exception:
        return {"queue": list(FACILITATORS)}


def save_state(queue: list):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"queue": queue}, f, ensure_ascii=False)


# JST → UTC 変換
def jst_to_utc_time(jst_hhmm: str) -> str:
    h, m = map(int, jst_hhmm.split(":"))
    jst_dt = datetime.now(JST).replace(hour=h, minute=m, second=0, microsecond=0)
    utc_dt = jst_dt.astimezone(timezone.utc)
    return utc_dt.strftime("%H:%M")


# スケジューラ起動
def start_facilitator_scheduler(app):
    # 勤務状態（オンライン）かどうか判定
    def is_active(user_id: str) -> bool:
        try:
            res = app.client.users_getPresence(user=user_id)
            return res.get("presence") == "active"
        except Exception:
            return False

    def post_facilitator_message():
        if datetime.now(JST).weekday() >= 5:
            return
        state = load_state()
        queue = deque(state["queue"])

        if not queue:
            return

        user_id = queue[0]
        mention = f"<@{user_id}>"

        app.client.chat_postMessage(
            channel=FACILITATOR_CHANNEL_ID,
            text="本日のデイリー司会の確認",
            blocks=[
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"本日のデイリー司会は {mention} さんです。\n対応可能ですか？"},
                },
                {
                    "type": "actions",
                    "elements": [
                        {"type": "button", "text": {"type": "plain_text", "text": "承認"}, "style": "primary", "action_id": "facilitator_approve", "value": str(user_id)},
                        {"type": "button", "text": {"type": "plain_text", "text": "スキップ"}, "action_id": "facilitator_pass", "value": str(user_id)},
                    ],
                },
            ],
        )

    def post_progress_report():
        # 土(5)・日(6)はスキップ
        if datetime.now(JST).weekday() >= 5:
            return
        if not FACILITATORS:
            return

        # 勤務状態（オンライン）の人のみ抽出
        active_users = [uid for uid in FACILITATORS if is_active(uid)]
        if not active_users:
            return

        mentions = " ".join(f"<@{uid}>" for uid in active_users)
        app.client.chat_postMessage(
            channel=FACILITATOR_CHANNEL_ID,
            text=f"{mentions}\nリマインダー : 進捗を記載してください",
        )

    def run_schedule():
        for jst_time in FACILITATOR_NOTIFY_TIME:
            utc_time = jst_to_utc_time(jst_time)
            schedule.every().day.at(utc_time).do(post_facilitator_message)

        #進捗報告
        schedule.every().day.at(jst_to_utc_time(PROGRESS_REPORT_TIME)).do(post_progress_report)

        while True:
            schedule.run_pending()
            time.sleep(1)

    threading.Thread(target=run_schedule, daemon=True).start()

# Slack アクション
def register_facilitator_actions(app):
    @app.action("facilitator_approve")
    def handle_facilitator_approve(ack, body):
        ack()

        user_id = body["actions"][0]["value"]
        channel_id = body["channel"]["id"]
        message_ts = body["message"]["ts"]

        state = load_state()
        queue = deque(state["queue"])

        # 承認された人を先頭から削除して末尾に回す
        if user_id in queue:
            queue.remove(user_id)
            queue.append(user_id)

        save_state(list(queue))

        mention = f"<@{user_id}>"

        # 元メッセージのボタンを更新
        app.client.chat_update(
            channel=channel_id,
            ts=message_ts,
            text=f"{mention} さんが対応を承認されました。",
        )

        app.client.chat_postMessage(
            channel=FACILITATOR_CHANNEL_ID,
            text=f"本日のデイリー司会は <@{user_id}> さんお願いします。",
        )

    @app.action("facilitator_pass")
    def handle_facilitator_pass(ack, body):
        ack()

        user_id = body["actions"][0]["value"]
        channel_id = body["channel"]["id"]
        message_ts = body["message"]["ts"]

        state = load_state()
        queue = deque(state["queue"])

        if user_id in queue:
            queue.remove(user_id)
            queue.append(user_id)

        save_state(list(queue))

        mention = f"<@{user_id}>"

        # ★ 元メッセージのボタンを消す
        app.client.chat_update(
            channel=channel_id,
            ts=message_ts,
            text=f"{mention} さんが対応をスキップされました。",
        )

        # 次の人に通知
        if queue:
            next_user = queue[0]
            mention = f"<@{next_user}>"
            app.client.chat_postMessage(
                channel=FACILITATOR_CHANNEL_ID,
                text="本日のデイリー司会の確認",
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"本日のデイリー司会は {mention} さんです。\n対応可能ですか？"
                        },
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "承認"},
                                "style": "primary",
                                "action_id": "facilitator_approve",
                                "value": str(next_user),
                            },
                            {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "スキップ"},
                                "action_id": "facilitator_pass",
                                "value": str(next_user),
                            },
                        ],
                    },
                ],
            )