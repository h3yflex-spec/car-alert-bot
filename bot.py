import os
import json
import re
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

# Максимум новых машин за один запуск
MAX_ADS_PER_RUN = 5


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
        raise Exception(
            f"Telegram error: {data}"
        )

    updates = data.get("result", [])

    if not updates:
        raise Exception(
            "Telegram не видит сообщений.\n"
            "Открой своего бота и отправь ему /start"
        )

    for update in reversed(updates):

        message = update.get("message")

        if message and message.get("chat"):

            return message["chat"]["id"]

    raise Exception(
        "Не удалось найти chat_id Telegram."
    )


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

    print(
        "Telegram:",
        response.text
    )

    if not response.ok:

        raise Exception(
            f"Telegram sendMessage error: "
            f"{response.text}"
        )


# ============================================================
# КУРС USD
# ============================================================

def get_usd_rate():

    response = requests.get(
        "https://api.nbrb.by/exrates/rates/USD?parammode=2",
        timeout=30
    )

    if response.status_code != 200:

        raise Exception(
            "Не удалось получить курс USD"
        )

    data = response.json()

    rate = float(
        data["Cur_OfficialRate"]
    )

    print(
        "Курс USD:",
        rate
    )

    return rate


# ============================================================
# СОХРАНЕНИЕ ОТПРАВЛЕННЫХ
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

        if not isinstance(data, list):

            return set()

        return set(
            str(x)
            for x in data
        )

    except Exception as error:

        print(
            "Ошибка чтения sent_ads.json:",
            error
        )

        return set()


def save_sent_ads(sent_ads):

    with open(
        SENT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            sorted(list(sent_ads)),
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

    return re.sub(
        r"\s+",
        " ",
        str(value)
    ).strip()


def extract_year(text):

    if not text:

        return None

    match = re.search(
        r"\b(19[8-9]\d|20[0-2]\d)\b",
        text
    )

    if match:

        return int(
            match.group(1)
        )

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

    text = (
        text or ""
    ).lower()

    if (
        "вариатор" in text
        or "cvt" in text
    ):

        return "Вариатор"

    if (
        "робот" in text
        or "dsg" in text
    ):

        return "Робот"

    if (
        "автомат" in text
        or "акпп" in text
    ):

        return "Автомат"

    return ""


# ============================================================
# ОЦЕНКА АВТО
# ============================================================

def rate_car(
    name,
    year=None,
    mileage=None,
    transmission=""
):

    text = clean_text(
        name
    ).lower()

    liquidity = 6
    parts = 7
    reliability = 6

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


    if year:

        if year < 1998:

            reliability -= 1
            liquidity -= 1

        elif year >= 2005:

            reliability += 1


    if mileage:

        if mileage > 400000:

            reliability -= 2

        elif mileage > 300000:

            reliability -= 1

        elif mileage < 200000:

            reliability += 1


    if transmission and year:

        if year < 2005:

            reliability -= 1


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
            liquidity
            + parts
        ) / 2
    )


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
            f"Kufar вернул код "
            f"{response.status_code}"
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
                float(raw_price)
                / 100
            )

        except Exception:

            continue


        if price_byn <= 0:

            continue


        price_usd = (
            price_byn
            / usd_rate
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


        rating = rate_car(

            name=name,

            year=year,

            mileage=mileage,

            transmission=transmission

        )


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
# TELEGRAM СООБЩЕНИЕ
# ============================================================

def format_ad(ad):

    rating = ad["rating"]


    if ad["year"]:

        year_text = str(
            ad["year"]
        )

    else:

        year_text = "не указан"


    if ad["mileage"]:

        mileage_text = (

            f"{ad['mileage']:,} км"
            .replace(",", " ")

        )

    else:

        mileage_text = "не указан"


    if ad["transmission"]:

        transmission_text = (
            ad["transmission"]
        )

    else:

        transmission_text = (
            "не указана"
        )


    return (

        f"🚗 <b>{ad['name']}</b>\n\n"

        f"📅 Год: {year_text}\n"

        f"🛣 Пробег: "
        f"{mileage_text}\n"

        f"⚙️ КПП: "
        f"{transmission_text}\n"

        f"📍 Источник: "
        f"{ad['source']}\n\n"

        f"💵 <b>"
        f"${ad['price_usd']:,.0f}"
        f"</b>\n"

        f"💰 "
        f"{ad['price_byn']:,.0f} BYN\n\n"

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


# Получаем Telegram chat ID

chat_id = get_chat_id()


# Получаем курс

usd_rate = get_usd_rate()


# Получаем объявления

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


# Загружаем историю

sent_ads = load_sent_ads()


# ============================================================
# ПЕРВЫЙ ЗАПУСК
# ============================================================

if not sent_ads:

    print(
        "Это первый запуск."
    )


    # Сначала отправляем
    # сообщение о запуске

    send_message(

        chat_id,

        "✅ <b>Мониторинг запущен!</b>\n\n"

        f"🚗 Найдено объявлений: "
        f"<b>{len(kufar_ads)}</b>\n\n"

        "💵 Лимит: до $1600\n"

        "📍 Источник: Kufar\n\n"

        "Сейчас отправлю первые "
        "объявления."

    )


    # Отправляем максимум 5

    for ad in kufar_ads[
        :MAX_ADS_PER_RUN
    ]:

        send_message(

            chat_id,

            format_ad(ad)

        )


    # Запоминаем ВСЕ найденные

    for ad in kufar_ads:

        sent_ads.add(
            ad["id"]
        )


    save_sent_ads(
        sent_ads
    )


    print(
        "Отправлено первых объявлений:",
        min(
            len(kufar_ads),
            MAX_ADS_PER_RUN
        )
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


    print(
        "Новых объявлений:",
        len(new_ads)
    )


    if new_ads:

        for ad in new_ads[
            :MAX_ADS_PER_RUN
        ]:

            send_message(

                chat_id,

                format_ad(ad)

            )

            sent_ads.add(
                ad["id"]
            )


        save_sent_ads(
            sent_ads
        )


        print(
            "Отправлено новых объявлений:",
            min(
                len(new_ads),
                MAX_ADS_PER_RUN
            )
        )


    else:

        print(
            "Новых объявлений нет."
        )


print("=" * 50)

print("Готово.")

print("=" * 50)
