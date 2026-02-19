import threading
import time
import schedule
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from lib.config import (
    FACILITATORS,
    FACILITATOR_CHANNEL_ID,
)

STATE_FILE = Path("data/facilitator_state.json")
JST = timezone(timedelta(hours=9))


# state管理
def load_state():
    if not STATE_FILE.exists():
        return {"index": 0, "carry_index": []}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
            state.setdefault("carry_index", [])
            return state
    except Exception:
        return {"index": 0, "carry_index": []}


def save_state(index: int, carry_index: list):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {"index": index, "carry_index": carry_index},
            f,
            ensure_ascii=False,
        )


# JST → UTC 変換
def jst_to_utc_time(jst_hhmm: str) -> str:
    h, m = map(int, jst_hhmm.split(":"))
    jst_dt = datetime.now(JST).replace(hour=h, minute=m, second=0, microsecond=0)
    utc_dt = jst_dt.astimezone(timezone.utc)
    return utc_dt.strftime("%H:%M")


# スケジューラ起動
def start_facilitator_scheduler(app):
    def post_facilitator_message():
        if not FACILITATORS:
            return

        state = load_state()
        index = state["index"]
        carry_index = state["carry_index"]

        if carry_index:
            display_index = carry_index[0]
        else:
            display_index = index

        user_id = FACILITATORS[display_index]
        mention = f"<@{user_id}>"

        app.client.chat_postMessage(
            channel=FACILITATOR_CHANNEL_ID,
            text="本日のデイリー司会の確認",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"本日のデイリー司会は {mention} さんです。\n対応可能ですか？",
                    },
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "✅ 承認"},
                            "style": "primary",
                            "action_id": "facilitator_approve",
                            "value": str(display_index),
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "⏭ スキップ"},
                            "action_id": "facilitator_pass",
                            "value": str(display_index),
                        },
                    ],
                },
            ],
        )

    def run_schedule():
        JST_TIME = "18:04"
        utc_time = jst_to_utc_time(JST_TIME)
        schedule.every().day.at(utc_time).do(post_facilitator_message)

        while True:
            schedule.run_pending()
            time.sleep(1)

    threading.Thread(target=run_schedule, daemon=True).start()


# Slack アクション
def register_facilitator_actions(app):
    @app.action("facilitator_approve")
    def handle_facilitator_approve(ack, body):
        ack()
        state = load_state()
        display_index = int(body["actions"][0]["value"])
        carry_index = state["carry_index"]

        user_id = FACILITATORS[display_index]
        app.client.chat_postMessage(
            channel=FACILITATOR_CHANNEL_ID,
            text=f"本日のデイリー司会は <@{user_id}> さんお願いします。",
        )

        if display_index in carry_index:
            carry_index.remove(display_index)

        if not carry_index:
            next_index = (display_index + 1) % len(FACILITATORS)
        else:
            next_index = state["index"]

        save_state(next_index, carry_index)

    @app.action("facilitator_pass")
    def handle_facilitator_pass(ack, body):
        ack()
        state = load_state()
        display_index = int(body["actions"][0]["value"])
        carry_index = state["carry_index"]

        if display_index not in carry_index:
            carry_index.append(display_index)

        next_index = (display_index + 1) % len(FACILITATORS)
        save_state(next_index, carry_index)

        next_display_index = next_index
        next_user = FACILITATORS[next_display_index]
        mention = f"<@{next_user}>"

        app.client.chat_postMessage(
            channel=FACILITATOR_CHANNEL_ID,
            text="本日のデイリー司会の確認",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"本日のデイリー司会は {mention} さんです。\n対応可能ですか？",
                    },
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "✅ 承認"},
                            "style": "primary",
                            "action_id": "facilitator_approve",
                            "value": str(next_display_index),
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "⏭ スキップ"},
                            "action_id": "facilitator_pass",
                            "value": str(next_display_index),
                        },
                    ],
                },
            ],
        )