import os
import json
import re
import html
import requests
from bs4 import BeautifulSoup

# ============================================================
# НАСТРОЙКИ
# ============================================================

TOKEN = os.environ["TELEGRAM_TOKEN"]

KUFAR_URL = (
    "https://auto.kufar.by/l/r~minsk/cars"
    "?cur=USD"
    "&mlg=r%3A0%2C9999999"
    "&prc=r%3A0%2C1600"
    "&rgd=r%3A1990%2C2026"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8"
}

SENT_FILE = "sent_ads.json"

MAX_PRICE_USD = 1600
MAX_NEW_PER_RUN = 5


# ============================================================
# TELEGRAM
# ============================================================

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
        raise Exception(
            "Сначала открой Telegram и напиши своему боту /start"
        )

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


def send_photo(chat_id, photo, caption):
    response = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
        json={
            "chat_id": chat_id,
            "photo": photo,
            "caption": caption,
            "parse_mode": "HTML"
        },
        timeout=30
    )

    print("Telegram photo:", response.text)

    try:
        return response.json().get("ok", False)
    except Exception:
        return False


# ============================================================
# КУРС USD
# ============================================================

def get_usd_rate():
    response = requests.get(
        "https://api.nbrb.by/exrates/rates/USD?parammode=2",
        timeout=30
    )

    if response.status_code != 200:
        raise Exception("Не удалось получить курс USD")

    data = response.json()

    rate = float(data["Cur_OfficialRate"])

    print("Курс USD:", rate)

    return rate


# ============================================================
# СОХРАНЕНИЕ ОБЪЯВЛЕНИЙ
# ============================================================

def load_sent_ads():
    if not os.path.exists(SENT_FILE):
        return set()

    try:
        with open(
            SENT_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        return set(data)

    except Exception:
        return set()


def save_sent_ads(sent_ads):
    with open(
        SENT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            list(sent_ads),
            file,
            ensure_ascii=False,
            indent=2
        )


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def clean_text(value):
    if not value:
        return ""

    value = str(value)

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


def extract_year(text):
    if not text:
        return None

    match = re.search(
        r"\b(19[8-9]\d|20[0-2]\d)\b",
        text
    )

    if match:
        return int(match.group(1))

    return None


def extract_mileage(text):
    if not text:
        return None

    match = re.search(
        r"(\d[\d\s]*)\s*(?:км|km)",
        text.lower()
    )

    if not match:
        return None

    value = re.sub(
        r"\s+",
        "",
        match.group(1)
    )

    try:
        return int(value)
    except Exception:
        return None


def detect_transmission(text):
    text = (text or "").lower()

    if "вариатор" in text or "cvt" in text:
        return "Вариатор"

    if "робот" in text or "dsg" in text:
        return "Робот"

    if "автомат" in text or "акпп" in text:
        return "Автомат"

    return ""


# ============================================================
# ОЦЕНКА МАРОК
# ============================================================

MODEL_RULES = {

    "bmw": {
        "liquidity": 7,
        "parts": 7,
        "reliability": 6
    },

    "mercedes": {
        "liquidity": 7,
        "parts": 7,
        "reliability": 6
    },

    "audi": {
        "liquidity": 7,
        "parts": 7,
        "reliability": 6
    },

    "volkswagen": {
        "liquidity": 8,
        "parts": 8,
        "reliability": 7
    },

    "toyota": {
        "liquidity": 9,
        "parts": 8,
        "reliability": 9
    },

    "honda": {
        "liquidity": 8,
        "parts": 7,
        "reliability": 9
    },

    "mazda": {
        "liquidity": 8,
        "parts": 7,
        "reliability": 8
    },

    "ford": {
        "liquidity": 8,
        "parts": 8,
        "reliability": 7
    },

    "opel": {
        "liquidity": 8,
        "parts": 9,
        "reliability": 7
    },

    "renault": {
        "liquidity": 7,
        "parts": 8,
        "reliability": 7
    },

    "skoda": {
        "liquidity": 8,
        "parts": 8,
        "reliability": 7
    },

    "nissan": {
        "liquidity": 8,
        "parts": 8,
        "reliability": 7
    },

    "mitsubishi": {
        "liquidity": 7,
        "parts": 7,
        "reliability": 8
    },

    "hyundai": {
        "liquidity": 8,
        "parts": 8,
        "reliability": 8
    },

    "kia": {
        "liquidity": 8,
        "parts": 8,
        "reliability": 8
    },

    "chevrolet": {
        "liquidity": 7,
        "parts": 8,
        "reliability": 7
    },

    "peugeot": {
        "liquidity": 7,
        "parts": 7,
        "reliability": 6
    },

    "citroen": {
        "liquidity": 6,
        "parts": 6,
        "reliability": 6
    },

    "volvo": {
        "liquidity": 6,
        "parts": 6,
        "reliability": 7
    },

    "fiat": {
        "liquidity": 6,
        "parts": 7,
        "reliability": 6
    },

    "suzuki": {
        "liquidity": 7,
        "parts": 7,
        "reliability": 8
    },

    "daewoo": {
        "liquidity": 8,
        "parts": 9,
        "reliability": 7
    },

    "lada": {
        "liquidity": 8,
        "parts": 10,
        "reliability": 6
    },

    "ваз": {
        "liquidity": 8,
        "parts": 10,
        "reliability": 6
    }
}


def rate_car(
    name,
    year=None,
    mileage=None,
    transmission=""
):

    text = clean_text(name).lower()

    base = None

    for brand, values in MODEL_RULES.items():

        if brand in text:

            base = values.copy()

            break

    if base is None:

        base = {
            "liquidity": 6,
            "parts": 7,
            "reliability": 6
        }

    liquidity = base["liquidity"]

    parts = base["parts"]

    reliability = base["reliability"]

    # Возраст

    if year:

        if year < 1998:

            reliability -= 1
            liquidity -= 1

        elif year >= 2010:

            reliability += 1

    # Пробег

    if mileage:

        if mileage > 400000:

            reliability -= 2

        elif mileage > 300000:

            reliability -= 1

        elif mileage < 200000:

            reliability += 1

    # Старые автоматы

    if transmission:

        if year and year < 2005:

            reliability -= 1

    # Ограничение

    liquidity = max(
        1,
        min(10, liquidity)
    )

    parts = max(
        1,
        min(10, parts)
    )

    reliability = max(
        1,
        min(10, reliability)
    )

    resale = round(
        (
            liquidity +
            parts
        ) / 2
    )

    total = round(
        (
            liquidity +
            parts +
            reliability +
            resale
        ) / 4,
        1
    )

    return {
        "liquidity": liquidity,
        "parts": parts,
        "reliability": reliability,
        "resale": resale,
        "total": total
    }


# ============================================================
# KUFAR
# ============================================================

def get_kufar_ads(usd_rate):

    response = requests.get(
        KUFAR_URL,
        headers=HEADERS,
        timeout=30
    )

    print(
        "Kufar status:",
        response.status_code
    )

    if response.status_code != 200:

        raise Exception(
            f"Kufar вернул код {response.status_code}"
        )

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    schema = soup.find(
        "script",
        id="catalog-schema",
        type="application/ld+json"
    )

    if not schema:

        raise Exception(
            "Kufar не передал catalog-schema"
        )

    try:

        data = json.loads(
            schema.string
        )

    except Exception as error:

        raise Exception(
            f"Ошибка JSON Kufar: {error}"
        )

    ads = []

    for item in data.get(
        "itemListElement",
        []
    ):

        product = item.get(
            "item",
            {}
        )

        name = clean_text(
            product.get(
                "name",
                "Автомобиль"
            )
        )

        offers = product.get(
            "offers",
            {}
        )

        raw_price = offers.get(
            "price",
            0
        )

        try:

            price_byn = (
                float(raw_price) / 100
            )

        except Exception:

            continue

        if price_byn <= 0:

            continue

        price_usd = (
            price_byn / usd_rate
        )

        if price_usd > MAX_PRICE_USD:

            continue

        url = offers.get(
            "url",
            ""
        )

        if not url:

            continue

        ad_id = (
            url
            .rstrip("/")
            .split("/")
            [-1]
        )

        description = clean_text(
            product.get(
                "description",
                ""
            )
        )

        combined_text = (
            name +
            " " +
            description
        )

        year = extract_year(
            combined_text
        )

        mileage = extract_mileage(
            combined_text
        )

        transmission = detect_transmission(
            combined_text
        )

        rating = rate_car(
            name=name,
            year=year,
            mileage=mileage,
            transmission=transmission
        )

        # Ищем фотографию

        image = product.get(
            "image",
            ""
        )

        if isinstance(
            image,
            list
        ):

            if image:

                image = image[0]

            else:

                image = ""

        ads.append({

            "id":
                f"kufar_{ad_id}",

            "source":
                "Kufar",

            "name":
                name,

            "price_byn":
                price_byn,

            "price_usd":
                price_usd,

            "url":
                url,

            "image":
                image or "",

            "year":
                year,

            "mileage":
                mileage,

            "transmission":
                transmission,

            "rating":
                rating
        })

    return ads


# ============================================================
# TELEGRAM — ФОРМАТ ОБЪЯВЛЕНИЯ
# ============================================================

def format_ad(ad):

    rating = ad["rating"]

    year_text = (
        str(ad["year"])
        if ad["year"]
        else "не указан"
    )

    mileage_text = (

        f"{ad['mileage']:,} км"
        .replace(",", " ")

        if ad["mileage"]

        else "не указан"
    )

    transmission_text = (

        ad["transmission"]

        if ad["transmission"]

        else "не указана"
    )

    name = html.escape(
        ad["name"]
    )

    url = html.escape(
        ad["url"],
        quote=True
    )

    return (

        "🆕 <b>НОВОЕ ОБЪЯВЛЕНИЕ</b>\n\n"

        f"🚗 <b>{name}</b>\n\n"

        f"💵 <b>${ad['price_usd']:,.0f}</b>\n"

        f"💰 {ad['price_byn']:,.0f} BYN\n\n"

        f"📅 Год: {year_text}\n"

        f"🛣 Пробег: "
        f"{mileage_text}\n"

        f"⚙️ КПП: "
        f"{transmission_text}\n"

        f"📍 {ad['source']}\n\n"

        "📊 <b>ОЦЕНКА</b>\n"

        f"💧 Ликвидность: "
        f"<b>{rating['liquidity']}/10</b>\n"

        f"🔧 Запчасти: "
        f"<b>{rating['parts']}/10</b>\n"

        f"🛠 Надёжность: "
        f"<b>{rating['reliability']}/10</b>\n"

        f"💸 Перепродажа: "
        f"<b>{rating['resale']}/10</b>\n\n"

        f"⭐ <b>ИТОГ: "
        f"{rating['total']}/10</b>\n\n"

        f"🔗 <a href=\"{url}\">"
        "Открыть объявление"
        "</a>"
    )


# ============================================================
# ОТПРАВКА ОБЪЯВЛЕНИЯ
# ============================================================

def send_ad(
    chat_id,
    ad
):

    caption = format_ad(ad)

    image = ad.get(
        "image",
        ""
    )

    # Если есть фотография,
    # пробуем отправить её

    if image and image.startswith(
        (
            "http://",
            "https://"
        )
    ):

        # Telegram ограничивает caption 1024 символами

        if len(caption) <= 1024:

            success = send_photo(
                chat_id,
                image,
                caption
            )

            if success:

                return

    # Если фото не удалось отправить —
    # отправляем обычное сообщение

    send_message(
        chat_id,
        caption
    )


# ============================================================
# ЗАПУСК
# ============================================================

print("=" * 50)

print(
    "🚗 CAR ALERT BOT"
)

print("=" * 50)


chat_id = get_chat_id()

usd_rate = get_usd_rate()


print(
    "Получаем объявления Kufar..."
)


kufar_ads = get_kufar_ads(
    usd_rate
)


print(
    "Kufar найдено:",
    len(kufar_ads)
)


sent_ads = load_sent_ads()


# ============================================================
# ПЕРВЫЙ ЗАПУСК
# ============================================================

if not sent_ads:

    for ad in kufar_ads:

        sent_ads.add(
            ad["id"]
        )

    save_sent_ads(
        sent_ads
    )

    send_message(

        chat_id,

        "✅ <b>Мониторинг запущен!</b>\n\n"

        f"🚗 Найдено объявлений: "
        f"<b>{len(kufar_ads)}</b>\n\n"

        "📍 Минск\n"

        "💵 До $1600\n"

        "⚙️ Автомат / робот / вариатор\n\n"

        "🚨 Старые объявления "
        "запомнил.\n\n"

        "Теперь буду присылать "
        "<b>только новые</b>."
    )


# ============================================================
# ПОСЛЕДУЮЩИЕ ЗАПУСКИ
# ============================================================

else:

    new_ads = []

    for ad in kufar_ads:

        if ad["id"] not in sent_ads:

            new_ads.append(
                ad
            )

            sent_ads.add(
                ad["id"]
            )

    save_sent_ads(
        sent_ads
    )

    print(
        "Новых объявлений:",
        len(new_ads)
    )

    if new_ads:

        for ad in new_ads[:MAX_NEW_PER_RUN]:

            send_ad(
                chat_id,
                ad
            )

    else:

        print(
            "Новых объявлений нет."
        )


print("=" * 50)

print(
    "Готово."
)

print("=" * 50)
