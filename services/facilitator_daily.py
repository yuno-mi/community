# services/facilitator_daily.py
import threading
import time
import schedule
import json
from pathlib import Path
from datetime import datetime, time as dtime, timedelta, timezone
from lib.config import (
    FACILITATORS,
    FACILITATOR_CHANNEL_ID,
)

STATE_FILE = Path("data/facilitator_state.json")

JST = timezone(timedelta(hours=9))


def load_index():
    if not STATE_FILE.exists():
        return 0
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("index", 0)
    except Exception:
        return 0


def save_index(index: int):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"index": index}, f)


def jst_to_utc_time(jst_hhmm: str) -> str:
    """'HH:MM' (JST) → 'HH:MM' (UTC)"""
    h, m = map(int, jst_hhmm.split(":"))

    jst_dt = datetime.now(JST).replace(
        hour=h, minute=m, second=0, microsecond=0
    )
    utc_dt = jst_dt.astimezone(timezone.utc)

    return utc_dt.strftime("%H:%M")


def start_facilitator_scheduler(app):
    """メインの Slack App を受け取って定時通知を開始"""

    def post_facilitator_message():
        if not FACILITATORS:
            print("[ERROR] FACILITATORS is empty")
            return

        index = load_index()
        facilitator_user_id = FACILITATORS[index]
        mention = f"<@{facilitator_user_id}>"

        print(f"[INFO] Selected facilitator: {facilitator_user_id} (index={index})")

        try:
            response = app.client.chat_postMessage(
                channel=FACILITATOR_CHANNEL_ID,
                text=f"本日のデイリー司会は {mention} さんお願いします。"
            )
            print(f"[INFO] Message sent. Response: {response}")

            next_index = (index + 1) % len(FACILITATORS)
            save_index(next_index)
            print(f"[INFO] Next index saved: {next_index}")

        except Exception as e:
            print(f"[ERROR] Failed to send message: {e}")

    def run_schedule():
        print("[INFO] Scheduler thread started.")

        JST_TIME = "09:30"

        utc_time = jst_to_utc_time(JST_TIME)
        print(f"[INFO] Facilitator notification time JST {JST_TIME} → UTC {utc_time}")

        schedule.every().day.at(utc_time).do(post_facilitator_message)

        while True:
            schedule.run_pending()
            time.sleep(1)

    threading.Thread(target=run_schedule, daemon=True).start()
    print("[INFO] Scheduler thread launched.")