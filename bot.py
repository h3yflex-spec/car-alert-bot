import json
import requests

cfg = json.load(open("config.json", encoding="utf-8"))

TOKEN = cfg["telegram_token"]
CHAT = cfg["chat_id"]

def send(text):
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={
            "chat_id": CHAT,
            "text": text
        }
    )

send("✅ Бот успешно запустился!")
