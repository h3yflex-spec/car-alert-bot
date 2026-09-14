import os
import requests

TOKEN = os.environ["TELEGRAM_TOKEN"]

# Получаем последние сообщения из Telegram
response = requests.get(
    f"https://api.telegram.org/bot{TOKEN}/getUpdates"
)

print("Telegram response:", response.text)

data = response.json()

if not data.get("ok"):
    raise Exception(f"Telegram API error: {data}")

updates = data.get("result", [])

if not updates:
    print("Сообщений пока нет.")
    exit()

# Берём последнее сообщение
last_message = updates[-1].get("message")

if not last_message:
    print("Последнее обновление не содержит сообщения.")
    exit()

chat_id = last_message["chat"]["id"]

# Отправляем ответ
send = requests.post(
    f"https://api.telegram.org/bot{TOKEN}/sendMessage",
    json={
        "chat_id": chat_id,
        "text": "🤖 Я тебя вижу!\n\nБот работает ✅\n\nСледующий этап — Kufar + AV.by 🚗"
    }
)

print("Send response:", send.text)
