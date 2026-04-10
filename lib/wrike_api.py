import requests
from lib.config import WRIKE_API_TOKEN, WRIKE_FOLDER_ID

HEADERS = {"Authorization": f"bearer {WRIKE_API_TOKEN}"}

def get_all_tasks(folder_id=WRIKE_FOLDER_ID, limit=10):
    tasks = []

    try:
        url = f"https://www.wrike.com/api/v4/folders/{folder_id}/tasks"
        resp = requests.get(url, headers=HEADERS)
        resp.raise_for_status()
        data = resp.json().get("data", [])
        for t in data[:limit]:
            tasks.append({"title": t.get("title"), "status": t.get("status", "undefined")})
    except Exception as e:
        tasks.append({"title": f"[Error] folder: {folder_id}", "status": str(e)})

    try:
        url = f"https://www.wrike.com/api/v4/folders/{folder_id}/subfolders"
        resp = requests.get(url, headers=HEADERS)
        resp.raise_for_status()
        subfolders = resp.json().get("data", [])
        for f in subfolders:
            tasks.extend(get_all_tasks(f["id"], limit=limit))
    except Exception as e:
        pass

    return tasks

def get_wrike_users():
    """Wrikeのコンタクト一覧を取得し、{表示名: wrike_id} の辞書を返す（アクティブメンバーのみ）"""
    url = "https://www.wrike.com/api/v4/contacts"
    try:
        resp = requests.get(url, headers=HEADERS)
        resp.raise_for_status()
        contacts = resp.json().get("data", [])
        return {
            (c["firstName"] + " " + c["lastName"]).strip(): c["id"]
            for c in contacts
            if c.get("type") == "Person"
            and not c.get("deleted", False)
            and c.get("me") or c.get("memberIds")  # アカウントメンバーのみ
        }
    except Exception as e:
        print(f"[ERROR] Failed to get Wrike users: {e}")
        return {}

def create_task_in_wrike(title, description="", folder_id=WRIKE_FOLDER_ID, responsibles=None, start_date=None, due_date=None):
    payload = {"title": title, "description": description, "status": "Active"}
    if responsibles:
        payload["responsibles"] = responsibles
    dates = {}
    if start_date:
        dates["start"] = start_date
    if due_date:
        dates["due"] = due_date
    if dates:
        payload["dates"] = dates
    url = f"https://www.wrike.com/api/v4/folders/{folder_id}/tasks"
    try:
        resp = requests.post(url, headers=HEADERS, json=payload)
        resp.raise_for_status()
        return resp.json().get("data", [])
    except Exception as e:
        print(f"[ERROR] Failed to create task: {e}")
        return None
    
def get_child_folders(parent_id):
    url = f"https://www.wrike.com/api/v4/folders/{parent_id}/folders"
    try:
        resp = requests.get(url, headers=HEADERS)
        resp.raise_for_status()
        return [
            {"id": f["id"], "title": f["title"]}
            for f in resp.json().get("data", [])
        ]
    except Exception as e:
        print(f"[ERROR] Failed to get child folders: {e}")
        return []