"""
Конфигурация парсера вакансий для Telegram-канала.
Получи API_ID и API_HASH на https://my.telegram.org/apps
"""

import os
from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
load_dotenv(_PROJECT_ROOT / ".env")


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Укажите {name} в .env (корень проекта: {_PROJECT_ROOT})")
    return value


def _require_int(name: str) -> int:
    raw = _require(name)
    try:
        return int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} должен быть целым числом") from exc


# ─── Telegram API ────────────────────────────────────────────────────────────
API_ID = _require_int("TELEGRAM_API_ID")
API_HASH = _require("TELEGRAM_API_HASH")
PHONE = _require("TELEGRAM_PHONE")
SESSION_NAME = str(_PROJECT_ROOT / "data" / "vacancy_session")

# ─── SQLite ──────────────────────────────────────────────────────────────────
_db_path = os.getenv("DATABASE_PATH", "data/aggregator.db").strip() or "data/aggregator.db"
DATABASE_PATH = Path(_db_path)
if not DATABASE_PATH.is_absolute():
    DATABASE_PATH = _PROJECT_ROOT / DATABASE_PATH

# ─── Google Sheets ───────────────────────────────────────────────────────────
GOOGLE_SPREADSHEET_ID = _require("GOOGLE_SPREADSHEET_ID")
_creds_file = os.getenv(
    "GOOGLE_SERVICE_ACCOUNT_FILE",
    "credentials/google_service_account.json",
).strip()
GOOGLE_SERVICE_ACCOUNT_FILE = Path(_creds_file)
if not GOOGLE_SERVICE_ACCOUNT_FILE.is_absolute():
    GOOGLE_SERVICE_ACCOUNT_FILE = _PROJECT_ROOT / GOOGLE_SERVICE_ACCOUNT_FILE

# ─── Каналы по умолчанию (при первом запуске копируются в БД) ───────────────
DEFAULT_CHANNELS = [
    "hubdgtl",
    "cozy_hr",
    "edujobs",
    "workenot",
    "workvc",
    "extyl_outstaff",
    "interns_stazhirovki_remote",
    "jobskolkovo",
    "futru_it",
    "remote_jobs_relocate",
    "juniors_managers_jobs",
    "easycareerstart",
    "relocationdev",
    "abroadz",
    "CareerPump",
    "edoocate",
    "sea_relocation",
    "nst_itsme",
    "joinyouthuz",
    "edu_traveler",
    "studyqa",
    "check_opportunities",
    "confsci",
    "worldabroad",
]

CHANNELS = DEFAULT_CHANNELS  # обратная совместимость для CLI

# ─── Параметры поиска ────────────────────────────────────────────────────────
MESSAGES_LIMIT = 30
MIN_MESSAGE_LENGTH = 100
MAX_POST_AGE_DAYS = 14

# ─── Целевой город ───────────────────────────────────────────────────────────
TARGET_CITY = "чебоксар"  # вакансии только из этого города (офис)

# ─── Крупные компании: разрешены вакансии в офис в любом городе ─────────────
BIG_COMPANIES = [
    # Бигтехи
    "сбер", "сбербанк", "сберbank", "sber",
    "яндекс", "yandex",
    "т-банк", "тбанк", "tbank", "тинькофф", "tinkoff",
    "vtb", "втб",
    "альфа", "alfa", "alfabank", "альфа-банк",
    "газпромбанк", "gazprombank",
    "россельхозбанк",
    "почта банк",
    "росбанк",
    "открытие",
    # Маркетплейсы
    "озон", "ozon",
    "wildberries", "вайлдберриз", "wb",
    "avito", "авито",
    "lamoda", "ламода",
    # Прочие крупные
    "касперский", "kaspersky",
    "mail.ru", "вконтакте", "vk",
    "мтс", "mts",
    "мегафон", "megafon",
    "билайн", "beeline",
    "ростелеком", "rostelecom",
    "1с", "1c",
    "самолет", "samolet",
    "додо", "dodo",
    "skolkovo", "сколково",
    "selectel", "selectel",
    "hh.ru", "headhunter",
    "2gis", "2гис",
    "ivi",
    "okko",
    "ситимобил", "sitimobil",
    "delivery club", "deliveryclub",
    "самокат",
    "evotor",
    "kontур", "kontur", "контур",
    "астрал",
    "innotech", "иннотех",
    "сириус",
]

# ─── Сигналы зарубежной вакансии ─────────────────────────────────────────────
ABROAD_SIGNALS = [
    "worldwide", "world wide",
    "relocat",  # relocation, relocate
    "germany", "германия",
    "cyprus", "кипр",
    "usa", "united states", "сша",
    "uk ", "united kingdom",
    "poland", "польша",
    "czech", "чехия",
    "netherlands", "нидерланды",
    "amsterdam",
    "london",
    "berlin",
    "warsaw",
    "amsterdam",
    "dubai", "дубай",
    "singapore", "сингапур",
    "kazakhstan", "казахстан",  # если явно зарубеж
    "🇩🇪", "🇺🇸", "🇬🇧", "🇨🇾", "🇵🇱", "🇨🇿", "🇳🇱", "🇦🇪", "🇸🇬", "🇺🇿", "🌏",
]

# ─── Обязательные ключевые слова ─────────────────────────────────────────────
REQUIRED_KEYWORDS = [
    "стажёр", "стажер", "стажировка", "стажировки",
    "junior", "джуниор", "джун",
    "начинающий", "начинающим", "начинающих",
    "практикант", "практика",
    "без опыта", "без опыта работы",
    "хакатон", "марафон", "кейс-чемпионат", "кейс чемпионат",
    "буткемп", "bootcamp",
    "для студентов", "студентам", "для студента",
    "intern", "internship",
    "trainee",
    "0-1 год", "0–1 год",
    "до 1 года", "до года",
]

# ─── Стоп-слова — пост сразу отклоняется ─────────────────────────────────────
STOP_KEYWORDS = [
    # Учебные программы (не вакансии)
    "купи курс",
    "запишись на курс",
    "бакалавриат",
    "специалитет",
    "магистратура",
    "аспирантура",
    "поступление в вуз",
    "приём в вуз",
    "приемная комиссия",
    "приёмная комиссия",
    "егэ",
    "высшее образование",
    "обучение в вузе",
    "учёба в вузе",
    "учеба в вузе",
    "стипендия",          # стипендии от банков/фондов — не вакансии
    "fellowship",         # академические феллоушипы
    "phd",               # докторские программы
    "диссертац",

    # Нерелевантный контент
    "онлайн-курс",
    "онлайн курс",
    "правовые основы",
    "природоохран",
    "волонтёр",
    "волонтер",
    "доброволец",

    # Зарубежные направления явно
    "права человека",      # правозащитные НКО — не наш профиль

    # Руководящие должности
    "руководитель направления",
    "head of",
    "chief ",
    "директор",
    "lead ",              # analytics lead, etc. — слишком опытные
    "tech lead",
    "team lead",
    "teamlead",

    # Опыт > 2 лет явно
    "3+ лет опыта",
    "3+ года опыта",
    "4+ лет",
    "5+ лет",
    "от 3 лет",
    "от 4 лет",
    "от 5 лет",
    "не менее 3 лет",
    "не менее 4 лет",
    "не менее 5 лет",
    "опыт работы от 3",
    "опыт работы от 4",
    "опыт работы от 5",
    "более 2 лет",
    "более 3 лет",
    "2+ лет опыта",

    # Специальности которых нет
    "e-commerce operations",
    "customer success",
    "amazon ppc",
    "hr-менеджер",
    "hr менеджер",
    "кадровый",

    # Нерелевантные истории/нарративы (характерные фразы из «шумовых» постов)
    "история успеха",
    "неделя из жизни",
    "день из жизни",
    "расскажу о своей",
    "мой путь",

    # Другие города в офис (без крупных компаний — проверяется отдельно)
    # (не ставим здесь — логика в classifier.py)
]

# ─── Приоритетные сигналы (повышают score) ───────────────────────────────────
PRIORITY_KEYWORDS = [
    "удалённо", "удаленно", "remote", "онлайн", "online",
    "оплачиваем", "оплата", "зарплата", "₽", "руб",
    "студент",
    "junior", "intern", "стажёр", "стажер",
    "без опыта",
    "чебоксар",   # вакансии конкретно в нашем городе — бонус
]

# ─── Направления ─────────────────────────────────────────────────────────────
# ТОЛЬКО те направления, которые есть у нас
DIRECTIONS = {
    "дизайн": [
        "дизайн", "designer", "ui/ux", "ui ", "ux ", "figma",
        "графический дизайн", "веб-дизайн", "веб дизайн",
        "illustrator", "photoshop", "motion", "3d дизайн",
        "брендинг", "визуальный", "арт-директор",
        "product designer", "продуктовый дизайнер",
        "#design",
    ],
    "разработка": [
        "разработчик", "разработка", "developer", "программист",
        "frontend", "front-end", "бэкенд", "backend", "back-end",
        "fullstack", "full-stack", "full stack",
        "python", "javascript", "typescript", "java", "swift", "kotlin",
        "react", "vue", "angular", "nodejs", "node.js",
        "android", "ios", "mobile developer",
        "devops", "golang", "go developer",
        "c++", "c#", "php", "ruby", "1c", "1с",
        "software engineer", "software developer",
        "#development", "#dev",
    ],
    "менеджмент": [
        "product manager", "продакт менеджер", "продакт-менеджер",
        "project manager", "проджект менеджер",
        "продуктовый менеджер", "менеджер продукта",
        "scrum master", "agile coach",
        "smm", "маркетолог", "маркетинг",
        "#management",
    ],
    "аналитика": [
        "аналитик данных", "data analyst", "data scientist",
        "бизнес-аналитик", "бизнес аналитик", "business analyst",
        "системный аналитик", "системный аналитик",
        "продуктовый аналитик", "product analyst",
        "sql аналитик", "bi аналитик", "bi-аналитик",
        "data science", "machine learning", "ml инженер",
        "исследователь данных",
        "#analytics", "#data",
    ],
    "тестирование": [
        "тестировщик", "тестировщица",
        "qa engineer", "qa инженер", "qc инженер",
        "software tester", "manual tester", "ручное тестирование",
        "автотестировщик", "автотест",
        "selenium", "appium",
        "#qa", "#qc",
    ],
}

# ─── Маппинг направления → канал публикации ──────────────────────────────────
DIRECTION_TO_CHANNEL = {
    "дизайн":       "vacancies",
    "разработка":   "vacancies",
    "менеджмент":   "vacancies",
    "аналитика":    "vacancies",
    "тестирование": "vacancies",
}

# Типы возможностей
OPPORTUNITY_TYPES = {
    "стажировка": [
        "стажировка", "стажёр", "стажер", "практика", "практикант",
        "intern", "internship", "trainee",
    ],
    "проект": [
        "хакатон", "марафон", "кейс-чемпионат", "кейс чемпионат",
        "кейс чемпион", "конкурс", "буткемп", "bootcamp",
    ],
    "мероприятие": [
        "конференция", "воркшоп", "вебинар", "meetup", "митап", "мероприятие",
    ],
    "вакансия": [
        "вакансия", "требуется", "ищем", "нужен", "нужна",
        "открыта позиция", "открыта вакансия", "junior", "джун",
    ],
}