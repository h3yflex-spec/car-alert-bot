import os
import json
import requests
from bs4 import BeautifulSoup

TOKEN = os.environ["TELEGRAM_TOKEN"]

KUFAR_URL = "https://auto.kufar.by/l/r~minsk/cars?cre=v.or%3A1%2C3%2C6%2C4%2C2%2C7%2C5&crt=v.or%3A1%2C2%2C3%2C4%2C5%2C12%2C11%2C10%2C8%2C9%2C7%2C6&cur=USD&mlg=r%3A0%2C9999999&prc=r%3A0%2C15000&rgd=r%3A1990%2C2026"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140 Safari/537.36"
}

# -------------------------
# Telegram
# -------------------------

def get_chat_id():
    response = requests.get(
        f"https://api.telegram.org/bot{TOKEN}/getUpdates",
        timeout=30
    )

    data = response.json()

    if not data.get("ok"):
        raise Exception(f"Telegram error: {data}")

    updates = data.get("result", [])

    if not updates:
        raise Exception("Сначала напиши боту /start")

    return updates[-1]["message"]["chat"]["id"]


def send_message(chat_id, text):
    response = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        },
        timeout=30
    )

    print("Telegram:", response.text)


# -------------------------
# Kufar
# -------------------------

def get_kufar_ads():

    response = requests.get(
        KUFAR_URL,
        headers=HEADERS,
        timeout=30
    )

    print("Kufar status:", response.status_code)

    if response.status_code != 200:
        raise Exception(
            f"Kufar вернул код {response.status_code}"
        )

    soup = BeautifulSoup(response.text, "html.parser")

    schema = soup.find(
        "script",
        id="catalog-schema",
        type="application/ld+json"
    )

    if not schema:
        raise Exception(
            "Kufar не передал catalog-schema"
        )

    data = json.loads(schema.string)

    ads = []

    for item in data.get("itemListElement", []):

        product = item.get("item", {})

        name = product.get("name", "Автомобиль")

        image = product.get("image", "")

        offers = product.get("offers", {})

        price_byn = float(
            offers.get("price", 0)
        )

        url = offers.get("url", "")

        if not url:
            continue

        # Курс BYN → USD
        # Пока используем приблизительный курс.
        # Потом сделаем автоматический курс НБ РБ.
        usd_rate = 3.2

        price_usd = price_byn / usd_rate

        ads.append({
            "name": name,
            "price_byn": price_byn,
            "price_usd": price_usd,
            "url": url,
            "image": image
        })

    return ads


# -------------------------
# Main
# -------------------------

chat_id = get_chat_id()

ads = get_kufar_ads()

print("Найдено объявлений:", len(ads))

if not ads:

    send_message(
        chat_id,
        "😕 Kufar не вернул объявления."
    )

else:

    text = "🚗 <b>Новые объявления Kufar</b>\n\n"

    for ad in ads[:5]:

        text += (
            f"🚘 <b>{ad['name']}</b>\n"
            f"💵 ${ad['price_usd']:,.0f}\n"
            f"💰 {ad['price_byn']:,.0f} BYN\n"
            f"🔗 <a href=\"{ad['url']}\">Открыть объявление</a>\n\n"
        )

    send_message(chat_id, text)
