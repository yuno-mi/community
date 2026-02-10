import os
import sys
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WRIKE_API_TOKEN = os.getenv("WRIKE_API_TOKEN")
WRIKE_FOLDER_ID = os.getenv("WRIKE_FOLDER_ID")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")

required_tokens = {
    "OPENAI_API_KEY": OPENAI_API_KEY,
    "WRIKE_API_TOKEN": WRIKE_API_TOKEN,
    "SLACK_BOT_TOKEN": SLACK_BOT_TOKEN,
    "SLACK_APP_TOKEN": SLACK_APP_TOKEN
}
missing = [name for name, val in required_tokens.items() if not val]
if missing:
    print(f"[ERROR] The following environment variables are not set: {', '.join(missing)}")
    sys.exit(1)

WRIKE_FOLDERS = {}
folders_str = os.getenv("WRIKE_FOLDERS", "")
if folders_str:
    for pair in folders_str.split(","):
        name, folder_id = pair.split(":")
        WRIKE_FOLDERS[name] = folder_id

FACILITATORS = [
    name.strip()
    for name in os.getenv("FACILITATORS", "").split(",")
    if name.strip()
]

FACILITATOR_CHANNEL_ID = os.getenv("FACILITATOR_CHANNEL_ID")
