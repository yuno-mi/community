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
    print(f"[ERROR] 以下の環境変数が設定されていません: {', '.join(missing)}")
    sys.exit(1)

WRIKE_FOLDERS = {
    "個人タスク": "IEACB2Q5I5MZG3E4",
    "pc20.4(EOL対応等改善)": "IEACB2Q5I5SOYQK2",
}
