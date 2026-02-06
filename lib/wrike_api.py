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

def create_task_in_wrike(title, description="", folder_id=WRIKE_FOLDER_ID):
    payload = {"title": title, "description": description, "status": "Active"}
    url = f"https://www.wrike.com/api/v4/folders/{folder_id}/tasks"
    try:
        resp = requests.post(url, headers=HEADERS, json=payload)
        resp.raise_for_status()
        return resp.json().get("data", [])
    except Exception as e:
        print(f"[ERROR] Failed to create task: {e}")
        return None
