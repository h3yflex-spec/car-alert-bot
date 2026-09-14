import os
import requests
from bs4 import BeautifulSoup

TOKEN = os.environ["TELEGRAM_TOKEN"]

KUFAR_URL = "https://auto.kufar.by/l/r~minsk/cars?cre=v.or%3A1%2C3%2C6%2C4%2C2%2C7%2C5&crt=v.or%3A1%2C2%2C3%2C4%2C5%2C12%2C11%2C10%2C8%2C9%2C7%2C6&cur=USD&mlg=r%3A0%2C9999999&prc=r%3A0%2C15000&rgd=r%3A1990%2C2026"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140 Safari/537.36"
}

def send_message(chat_id, text):
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": False
        }
    )

# Получаем последнее сообщение пользователя
updates_response = requests.get(
    f"https://api.telegram.org/bot{TOKEN}/getUpdates"
)

updates_data = updates_response.json()

if not updates_data.get("ok"):
    raise Exception("Ошибка Telegram")

updates = updates_data.get("result", [])

if not updates:
    print("Сначала напиши боту /start")
    exit()

chat_id = updates[-1]["message"]["chat"]["id"]

# Открываем Kufar
response = requests.get(
    KUFAR_URL,
    headers=headers,
    timeout=30
)

print("Kufar status:", response.status_code)
print(response.text[:5000])

if response.status_code != 200:
    send_message(
        chat_id,
        f"⚠️ Kufar не дал доступ к странице.\nКод: {response.status_code}"
    )
    exit()

soup = BeautifulSoup(response.text, "html.parser")

# Ищем ссылки на объявления
links = []

for a in soup.find_all("a", href=True):
    href = a["href"]

    if "/item/" in href or "/l/" in href:
        if href.startswith("/"):
            href = "https://auto.kufar.by" + href

        if href not in links:
            links.append(href)

# Оставляем первые 5
links = links[:5]

if not links:
    send_message(
        chat_id,
        "⚠️ Kufar открылся, но объявления не удалось найти.\n\n"
        "Значит, нужно будет подключить другой способ получения данных."
    )
else:
    text = "🚗 <b>Тест Kufar</b>\n\n"

    for i, link in enumerate(links, 1):
        text += f"{i}. {link}\n\n"

    send_message(chat_id, text)

print("Готово!")
