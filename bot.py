import os
import json
import re
import requests
from bs4 import BeautifulSoup

# ============================================================
# НАСТРОЙКИ
# ============================================================

TOKEN = os.environ["TELEGRAM_TOKEN"]

# Kufar:
# Минск + Минская область
# Цена до $1600
# Годы 1990-2026
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
# СОХРАНЕНИЕ УЖЕ ОТПРАВЛЕННЫХ ОБЪЯВЛЕНИЙ
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

    value = match.group(1)

    value = re.sub(
        r"\s+",
        "",
        value
    )

    try:
        return int(value)
    except Exception:
        return None


def detect_transmission(text):
    text = text.lower()

    if "вариатор" in text:
        return "Вариатор"

    if "робот" in text:
        return "Робот"

    if "автомат" in text:
        return "Автомат"

    if "акпп" in text:
        return "Автомат"

    return ""


# ============================================================
# ОЦЕНКА АВТОМОБИЛЯ
# ============================================================

def rate_car(
    name,
    year=None,
    mileage=None,
    transmission=""
):
    """
    Ориентировочная оценка автомобиля.

    Это НЕ диагностика автомобиля.
    Оценка строится по общим рыночным признакам.
    """

    text = clean_text(name).lower()

    # Базовые значения
    liquidity = 6
    parts = 7
    reliability = 6

    # --------------------------------------------------------
    # Популярность бренда
    # --------------------------------------------------------

    popular_brands = [
        "volkswagen",
        "toyota",
        "renault",
        "ford",
        "opel",
        "skoda",
        "audi",
        "bmw",
        "mercedes",
        "hyundai",
        "kia",
        "nissan",
        "mazda",
        "mitsubishi",
        "honda",
        "chevrolet",
        "peugeot",
        "citroen",
        "volvo",
        "fiat",
        "suzuki",
        "daewoo",
        "lada",
        "ваз"
    ]

    if any(
        brand in text
        for brand in popular_brands
    ):
        liquidity += 1
        parts += 1

    # --------------------------------------------------------
    # Очень старые машины
    # --------------------------------------------------------

    if year:

        if year < 1998:
            reliability -= 1
            liquidity -= 1

        elif year >= 2005:
            reliability += 1

    # --------------------------------------------------------
    # Пробег
    # --------------------------------------------------------

    if mileage:

        if mileage > 400000:
            reliability -= 2

        elif mileage > 300000:
            reliability -= 1

        elif mileage < 200000:
            reliability += 1

    # --------------------------------------------------------
    # Старая автоматическая коробка
    # --------------------------------------------------------

    if transmission:

        transmission_lower = transmission.lower()

        if (
            "автомат" in transmission_lower
            or "робот" in transmission_lower
            or "вариатор" in transmission_lower
        ):

            if year and year < 2005:
                reliability -= 1

    # --------------------------------------------------------
    # Ограничиваем оценки
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Потенциал перепродажи
    # --------------------------------------------------------

    resale = round(
        (
            liquidity
            + parts
        ) / 2
    )

    # --------------------------------------------------------
    # Общая оценка
    # --------------------------------------------------------

    total = round(
        (
            liquidity
            + parts
            + reliability
            + resale
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

        # Kufar отдаёт цену в копейках
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

        # Попытаемся получить характеристики
        description = clean_text(
            product.get(
                "description",
                ""
            )
        )

        combined_text = (
            name
            + " "
            + description
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

        # На этом этапе автомат
        # определяется по данным объявления.
        # Если Kufar не передал КПП в JSON-LD,
        # объявление всё равно сохраняем.
        rating = rate_car(
            name=name,
            year=year,
            mileage=mileage,
            transmission=transmission
        )

        ads.append({
            "id": f"kufar_{ad_id}",
            "source": "Kufar",
            "name": name,
            "price_byn": price_byn,
            "price_usd": price_usd,
            "url": url,
            "year": year,
            "mileage": mileage,
            "transmission": transmission,
            "rating": rating
        })

    return ads


# ============================================================
# ФОРМИРОВАНИЕ TELEGRAM-СООБЩЕНИЯ
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

    return (
        f"🚗 <b>{ad['name']}</b>\n\n"

        f"📅 Год: {year_text}\n"
        f"🛣 Пробег: {mileage_text}\n"
        f"⚙️ КПП: {transmission_text}\n"
        f"📍 Источник: {ad['source']}\n\n"

        f"💵 <b>${ad['price_usd']:,.0f}</b>\n"
        f"💰 {ad['price_byn']:,.0f} BYN\n\n"

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

        f"🔗 <a href=\"{ad['url']}\">"
        f"Открыть объявление"
        f"</a>"
    )


# ============================================================
# ЗАПУСК
# ============================================================

print("=" * 50)
print("🚗 CAR ALERT BOT")
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

        "📍 Минск + Минская область\n"
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

        # Максимум 5 объявлений
        # за один запуск
        for ad in new_ads[:5]:

            send_message(
                chat_id,
                format_ad(ad)
            )

    else:

        print(
            "Новых объявлений нет."
        )

print("=" * 50)
print("Готово.")
print("=" * 50)
