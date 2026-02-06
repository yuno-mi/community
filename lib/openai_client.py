from openai import OpenAI
from lib.config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

def generate_response(tasks, user_text):
    try:
        prompt_system = "あなたはタスク管理アシスタントです。以下はタスク一覧です：\n" + \
                        "\n".join([f"- {t['title']} ({t['status']})" for t in tasks])
    except Exception:
        prompt_system = "タスク取得に失敗しました。"

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt_system},
                {"role": "user", "content": user_text},
            ],
            max_tokens=300
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"[ERROR] ChatGPT API エラー: {e}")
        return "AI応答の取得に失敗しました。"
