from slack_sdk.errors import SlackApiError
from openai import OpenAI, AuthenticationError, APIError
from tests.config import WRIKE_API_TOKEN, OPENAI_API_KEY
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

def check_openai_token() -> bool:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        client.models.list()
        return True
    except AuthenticationError:
        return False
    except APIError:
        return False
    except Exception:
        return False
