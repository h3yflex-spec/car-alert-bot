import os
import requests

TOKEN = os.environ["TELEGRAM_TOKEN"]

url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
response = requests.get(url)
data = response.json()

if not data.get("ok"):
    raise Exception("Telegram API error")

updates = data.get("result", [])

if not updates:
    print("Нет сообщений от пользователя.")
    exit()

chat_id = updates[-1]["message"]["chat"]["id"]

send_url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

requests.post(
    send_url,
    json={
        "chat_id": chat_id,
        "text": "🤖 Бот работает!\n\nТеперь можем подключать Kufar и AV.by 🚗"
    }
)

print("Сообщение отправлено!")
