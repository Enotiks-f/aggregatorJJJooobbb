"""
Классификатор вакансий: определяет направление, тип и релевантность поста.
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Optional

from .config import (
    REQUIRED_KEYWORDS,
    STOP_KEYWORDS,
    PRIORITY_KEYWORDS,
    DIRECTIONS,
    OPPORTUNITY_TYPES,
    DIRECTION_TO_CHANNEL,
)


def build_post_url(channel_username: str, message_id: int) -> str:
    return f"https://t.me/{channel_username}/{message_id}"


@dataclass
class VacancyResult:
    """Структура найденной вакансии/проекта."""
    channel: str                  # имя источника (канал TG)
    post_url: str                 # ссылка на пост
    text_preview: str             # первые 300 символов текста
    direction: Optional[str]      # дизайн / разработка / менеджмент / аналитика / тестирование
    opportunity_type: str         # вакансия / стажировка / проект / мероприятие
    publish_channel: str          # куда публиковать: vacancies / project / as_is
    score: int = 0                # релевантность (больше = лучше)
    company: str = ""             # название компании (если найдено)
    deadline: str = ""            # дедлайн (если найден)
    is_paid: Optional[bool] = None  # оплачиваемая?
    is_remote: Optional[bool] = None
    raw_text: str = field(default="", repr=False)


def normalize(text: str) -> str:
    """Привести к нижнему регистру для поиска."""
    return text.lower().strip()


def is_relevant(text: str) -> bool:
    """
    Проверяет, подходит ли пост для канала:
    - содержит хотя бы одно обязательное ключевое слово
    - не содержит стоп-слов
    - достаточно длинный
    """
    low = normalize(text)

    # Стоп-слова
    for stop in STOP_KEYWORDS:
        if stop in low:
            return False

    # Хотя бы одно обязательное слово
    return any(kw in low for kw in REQUIRED_KEYWORDS)


def detect_direction(text: str) -> Optional[str]:
    """Определяет направление вакансии."""
    low = normalize(text)
    scores: dict[str, int] = {}
    for direction, keywords in DIRECTIONS.items():
        count = sum(1 for kw in keywords if kw in low)
        if count:
            scores[direction] = count
    if not scores:
        return None
    return max(scores, key=lambda k: scores[k])


def detect_opportunity_type(text: str) -> str:
    """Определяет тип возможности."""
    low = normalize(text)
    for opp_type, keywords in OPPORTUNITY_TYPES.items():
        if any(kw in low for kw in keywords):
            return opp_type
    return "вакансия"


def detect_publish_channel(direction: Optional[str], opp_type: str) -> str:
    """
    Определяет, в какой канал публиковать:
    - project    → хакатоны, марафоны, кейсы
    - as_is      → мероприятия и бесплатный контент
    - vacancies  → вакансии и стажировки
    """
    if opp_type == "мероприятие":
        return "as_is"
    if opp_type == "проект":
        return "project"
    return "vacancies"


def detect_is_paid(text: str) -> Optional[bool]:
    """Пытается определить, оплачивается ли позиция."""
    low = normalize(text)
    paid_signals = ["зарплата", "оплата", "оплачивается", "стипендия", "₽", "руб", "rub",
                    "оплачиваем", "вознаграждение", "гонорар"]
    unpaid_signals = ["бесплатно", "без оплаты", "волонтёр", "волонтер", "добровольно"]
    if any(s in low for s in unpaid_signals):
        return False
    if any(s in low for s in paid_signals):
        return True
    return None


def detect_is_remote(text: str) -> Optional[bool]:
    """Определяет формат работы."""
    low = normalize(text)
    remote_signals = ["удалённо", "удаленно", "remote", "из любой точки", "онлайн-стажировка"]
    office_signals = ["офис", "в офисе", "очно", "на месте", "москва", "санкт-петербург"]
    if any(s in low for s in remote_signals):
        return True
    if any(s in low for s in office_signals):
        return False
    return None


def extract_company(text: str) -> str:
    """Пытается вычленить название компании из текста."""
    patterns = [
        r'компания\s+[«"]?([A-ZА-Я][A-Za-zА-Яа-я0-9\s&]{2,30})[»"]?',
        r'[«"]([A-ZА-Я][A-Za-zА-Яа-я0-9\s&]{2,30})[»"]',
        r'от\s+([A-ZА-Я][A-Za-zА-Яа-я0-9\s&]{2,30})\b',
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()[:50]
    return ""


def extract_deadline(text: str) -> str:
    """Ищет упоминание дедлайна."""
    low = normalize(text)
    deadline_patterns = [
        r'дедлайн[:\s]+(\d{1,2}[./]\d{1,2}(?:[./]\d{2,4})?)',
        r'до\s+(\d{1,2}[./]\d{1,2}(?:[./]\d{2,4})?)',
        r'приём[а-я]*\s+до\s+(\d{1,2}[./]\d{1,2})',
        r'срок[а-я]*\s+подачи[:\s]+(.{5,30})',
        r'успей[те]?\s+до\s+(\d{1,2}[./]\d{1,2})',
    ]
    for pattern in deadline_patterns:
        m = re.search(pattern, low)
        if m:
            return m.group(1).strip()
    return ""


def calculate_score(text: str, direction: Optional[str], is_remote: Optional[bool],
                    is_paid: Optional[bool]) -> int:
    """
    Вычисляет релевантность поста (0-100).
    Выше — интереснее для публикации.
    """
    low = normalize(text)
    score = 0

    # Приоритетные сигналы
    score += sum(2 for kw in PRIORITY_KEYWORDS if kw in low)

    # Есть направление
    if direction:
        score += 10

    # Удалённая работа — приоритет
    if is_remote is True:
        score += 15

    # Оплачивается
    if is_paid is True:
        score += 10

    # Для студентов явно
    if "студент" in low:
        score += 8

    # Подробное описание (много текста)
    score += min(len(text) // 200, 10)

    return score


def classify(text: str, channel_username: str, message_id: int) -> Optional[VacancyResult]:
    """
    Полная классификация одного поста.
    Возвращает None, если пост нерелевантен.
    """
    if not is_relevant(text):
        return None

    direction = detect_direction(text)
    opp_type = detect_opportunity_type(text)
    publish_channel = detect_publish_channel(direction, opp_type)
    is_paid = detect_is_paid(text)
    is_remote = detect_is_remote(text)
    score = calculate_score(text, direction, is_remote, is_paid)
    company = extract_company(text)
    deadline = extract_deadline(text)

    # Превью текста
    clean_text = text.strip().replace("\n", " ")
    preview = clean_text[:300] + ("…" if len(clean_text) > 300 else "")

    post_url = build_post_url(channel_username, message_id)

    return VacancyResult(
        channel=channel_username,
        post_url=post_url,
        text_preview=preview,
        direction=direction,
        opportunity_type=opp_type,
        publish_channel=publish_channel,
        score=score,
        company=company,
        deadline=deadline,
        is_paid=is_paid,
        is_remote=is_remote,
        raw_text=text,
    )