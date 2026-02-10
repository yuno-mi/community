from slack_sdk.errors import SlackApiError
from lib.config import WRIKE_API_TOKEN
import requests

def check_slack_token(client) -> bool:
    try:
        client.auth_test()
        return True
    except SlackApiError:
        return False

def check_wrike_token() -> bool:
    try:
        res = requests.get(
            "https://www.wrike.com/api/v4/contacts",
            headers={"Authorization": f"Bearer {WRIKE_API_TOKEN}"},
            timeout=5
        )
        return res.status_code == 200
    except Exception:
        return False
