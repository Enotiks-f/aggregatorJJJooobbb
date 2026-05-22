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

# ─── Каналы для поиска ──────────────────────────────────────────────────────
# Добавляй username каналов без @
CHANNELS = [
    "easycareerstart",
    "workenot",
    "futru_it",
    "jobskolkovo",
    "remote_jobs_relocate",
    "cozy_hr",
    "edujobs",
    "interns_stazhirovki_remote"
]

# ─── Параметры поиска ────────────────────────────────────────────────────────
# Глубина поиска — сколько последних постов брать из каждого канала
MESSAGES_LIMIT = 30

# Минимальная длина поста (символов) — фильтруем мусор
MIN_MESSAGE_LENGTH = 100

# Насколько старые посты брать (в днях)
MAX_POST_AGE_DAYS = 14

# ─── Ключевые слова ──────────────────────────────────────────────────────────
# Обязательные слова — пост ДОЛЖЕН содержать хотя бы одно из них
REQUIRED_KEYWORDS = [
    "стажёр", "стажер", "стажировка", "стажировки",
    "junior", "джуниор", "джун",
    "начинающий", "начинающим", "начинающих",
    "практикант", "практика",
    "без опыта", "без опыта работы",
    "хакатон", "марафон", "кейс-чемпионат", "кейс чемпионат",
    "буткемп", "bootcamp",
    "для студентов", "студентам", "для студента",
]

# Стоп-слова — если пост содержит их БЕЗ контекста вакансии — пропускаем
STOP_KEYWORDS = [
    "купи курс",
    "бакалавриат",
    "специалитет",
    "магистратура",
    "аспирантура",
    "поступление в вуз",
    "приём в вуз",
    "приемная комиссия",
    "егэ",
]

# ─── Приоритетные сигналы ────────────────────────────────────────────────────
# Повышают score поста
PRIORITY_KEYWORDS = [
    "удалённо", "удаленно", "remote", "онлайн", "online",
    "оплачиваем", "оплата", "зарплата", "stipend", "стипендия",
    "студент",
]

# ─── Направления (для тега канала) ──────────────────────────────────────────
DIRECTIONS = {
    "дизайн": [
        "дизайн", "design", "ui", "ux", "figma", "графика",
        "illustrator", "photoshop", "motion", "3d", "брендинг",
        "визуал", "арт-директор",
    ],
    "разработка": [
        "разработк", "developer", "программист", "frontend", "backend",
        "fullstack", "python", "javascript", "java", "swift", "kotlin",
        "react", "vue", "android", "ios", "devops", "1c", "golang",
        "c++", "c#", "php", "ruby",
    ],
    "менеджмент": [
        "менеджер", "manager", "product", "проджект", "project",
        "продуктовый", "scrum", "agile", "операционный", "бизнес-аналитик",
        "маркетинг", "smm", "pr-менеджер", "event",
    ],
    "аналитика": [
        "аналитик", "analyst", "data", "данные", "sql", "tableau",
        "power bi", "excel", "research", "исследователь", "bi-аналитик",
        "data science", "ml", "machine learning",
    ],
    "тестирование": [
        "тестировщик", "qa", "qc", "tester", "тестирование",
        "автотест", "selenium", "appium", "ручное тестирование",
    ],
}

# ─── Маппинг направления → канал публикации ─────────────────────────────────
DIRECTION_TO_CHANNEL = {
    "дизайн":       "vacancies",
    "разработка":   "vacancies",
    "менеджмент":   "vacancies",
    "аналитика":    "vacancies",
    "тестирование": "vacancies",
}

# Типы возможностей
OPPORTUNITY_TYPES = {
    "вакансия": ["вакансия", "требуется", "ищем", "нужен", "нужна", "открыта позиция"],
    "стажировка": ["стажировка", "стажёр", "стажер", "практика", "практикант", "intern"],
    "проект": ["хакатон", "марафон", "кейс", "чемпионат", "конкурс", "буткемп", "bootcamp"],
    "мероприятие": ["мероприятие", "конференция", "воркшоп", "вебинар", "meetup"],
}