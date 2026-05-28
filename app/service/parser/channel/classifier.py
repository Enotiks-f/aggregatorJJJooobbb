"""
Классификатор вакансий: определяет направление, тип и релевантность поста.
"""

from __future__ import annotations
import re
import hashlib
from dataclasses import dataclass, field
from typing import Optional

from .config import (
    REQUIRED_KEYWORDS,
    STOP_KEYWORDS,
    PRIORITY_KEYWORDS,
    DIRECTIONS,
    OPPORTUNITY_TYPES,
    DIRECTION_TO_CHANNEL,
    ABROAD_SIGNALS,
    BIG_COMPANIES,
    TARGET_CITY,
)




def normalize_text_for_hash(text: str) -> str:
    """Приводит текст к каноническому виду для сравнения."""
    # Нижний регистр
    text = text.lower()
    # Удаляем все знаки препинания, цифры и лишние пробелы
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\d+', '', text)  # удаляем числа
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def text_hash(text: str) -> str:
    norm = normalize_text_for_hash(text)
    return hashlib.md5(norm.encode('utf-8')).hexdigest()

def build_post_url(channel_username: str, message_id: int) -> str:
    return f"https://t.me/{channel_username}/{message_id}"


@dataclass
class VacancyResult:
    """Структура найденной вакансии/проекта."""
    channel: str
    post_url: str
    text_preview: str
    direction: Optional[str]
    opportunity_type: str
    publish_channel: str
    score: int = 0
    company: str = ""
    deadline: str = ""
    is_paid: Optional[bool] = None
    is_remote: Optional[bool] = None
    raw_text: str = field(default="", repr=False)


def normalize(text: str) -> str:
    return text.lower().strip()


# ─── Новые фильтры ────────────────────────────────────────────────────────────

def is_abroad(text: str) -> bool:
    """Возвращает True, если вакансия явно зарубежная."""
    low = normalize(text)
    return any(signal in low for signal in ABROAD_SIGNALS)


def is_big_company(text: str) -> bool:
    """Возвращает True, если в тексте упомянута крупная компания."""
    low = normalize(text)
    return any(company in low for company in BIG_COMPANIES)


def has_wrong_city_office(text: str) -> bool:
    """
    Возвращает True, если вакансия предполагает работу в офисе
    в другом городе (не Чебоксары), и компания не крупная.

    Логика:
    1. Если явный remote/удалённо — всё ок, возвращаем False.
    2. Если упомянут офис или конкретный город ≠ Чебоксары — плохо.
    3. Но если компания крупная — разрешаем.
    """
    low = normalize(text)

    # Явно удалённо — не офисная
    remote_signals = ["удалённо", "удаленно", "remote", "из любой точки", "онлайн-стажировка", "онлайн стажировка"]
    if any(s in low for s in remote_signals):
        return False

    # Города, которые нас не устраивают как место офиса
    other_cities = [
        "москв", "санкт-петербург", "питер", "спб",
        "казань", "нижний новгород", "екатеринбург", "новосибирск",
        "самара", "уфа", "краснодар", "ростов-на-дону", "ростов",
        "воронеж", "пермь", "волгоград", "красноярск",
        "алматы", "алма-ата",
    ]

    has_other_city = any(city in low for city in other_cities)
    has_target_city = TARGET_CITY in low

    if has_other_city and not has_target_city:
        # Если упомянут другой город и нет Чебоксар — проверяем, крупная ли компания
        if is_big_company(text):
            return False  # Крупным разрешаем
        return True  # Остальным — нет

    return False


def has_too_much_experience(text: str) -> bool:
    """Проверяет, требуется ли опыт более 1-2 лет явно."""
    low = normalize(text)
    patterns = [
        r"\b[3-9]\+?\s*лет\s*(опыта|работы)",
        r"опыт\s*(работы\s*)?(от|не менее|более)\s*[3-9]",
        r"(от|не менее|более)\s*[3-9]\s*лет",
        r"\b[3-9]\+\s*(года?|лет)\b",
        r"middle\s*[\+\-]?\s*(and|/|или)\s*senior",
        r"\bsenior\b",
        r"\bsrе\b",
        r"старший\s+(разработчик|аналитик|дизайнер|инженер|менеджер)",
        r"ведущий\s+(разработчик|аналитик|дизайнер|инженер)",
    ]
    return any(re.search(p, low) for p in patterns)


def has_management_role(text: str) -> bool:
    """Проверяет, является ли позиция руководящей."""
    low = normalize(text)
    patterns = [
        r"\bhead\s+of\b",
        r"\bchief\b",
        r"руководитель\s+(направления|отдела|команды|группы|проекта)",
        r"начальник\s+отдела",
        r"\bdirector\b",
        r"\bcto\b", r"\bceo\b", r"\bcpo\b", r"\bcmo\b",
        r"tech\s*lead",
        r"team\s*lead",
        r"вице-президент",
    ]
    return any(re.search(p, low) for p in patterns)


def has_education_requirement(text: str) -> bool:
    """Проверяет, требуется ли высшее образование или обучение в вузе."""
    low = normalize(text)
    signals = [
        "высшее образование",
        "диплом о высшем",
        "обязательное высшее",
        "наличие высшего",
        "учитесь в вузе",
        "обучаетесь в вузе",
        "студент вуза",          # требование, а не аудитория
        "гражданин рф.*учишься очно",  # как в стипендиях
    ]
    for s in signals:
        if re.search(s, low):
            return True
    return False


def is_noise_content(text: str) -> bool:
    """
    Проверяет, является ли пост нерелевантным «шумом»:
    личные истории, курсы, обучающий контент, правозащита и т.п.
    """
    low = normalize(text)

    # Признаки нарратива / личной истории
    narrative_signals = [
        "история успеха",
        "неделя из жизни",
        "день из жизни",
        "расскажу о своей",
        "мой путь",
        "в следующих постах расскажу",
        "я продолжила",
        "я продолжил",
        "я сделала",
        "я сделал",
        "как я",
    ]
    if any(s in low for s in narrative_signals):
        return True

    # Курсы, обучение
    course_signals = [
        "онлайн-курс", "онлайн курс", "запишись на курс",
        "купи курс", "образовательная платформа",
        "правовые основы", "природоохран",
    ]
    if any(s in low for s in course_signals):
        return True

    # Нет ни одного слова связанного с работой/позицией — явный шум
    job_signals = [
        "вакансия", "vacancy", "стажировка", "internship", "intern",
        "junior", "ищем", "требуется", "нужен", "нужна", "позиция",
        "работа", "job", "хакатон", "кейс", "практика", "буткемп",
        "bootcamp", "конкурс", "марафон",
    ]
    if not any(s in low for s in job_signals):
        return True

    return False


def has_unknown_direction(text: str) -> bool:
    """
    Проверяет, относится ли пост к специальности, которой у нас нет.
    Это «белый список»: если ни одно направление не определено → возможно шум.
    Используется в связке с detect_direction.
    """
    # Сигналы несуществующих у нас специальностей
    low = normalize(text)
    unknown_signals = [
        "e-commerce operations",
        "amazon ppc",
        "customer success manager",
        "supply chain",
        "hr-менеджер", "hr менеджер", "hr specialist",
        "кадровый специалист",
        "бухгалтер", "бухгалтерия",
        "юрист", "legal",
        "security engineer", "информационная безопасность инженер",
        "инженер систем мониторинга",
        "сетевой инженер",
        "devrel",
        "комьюнити-менеджер", "community manager",
    ]
    return any(s in low for s in unknown_signals)


# ─── Основные функции ─────────────────────────────────────────────────────────

def is_relevant(text: str) -> bool:
    """
    Проверяет, подходит ли пост для канала.
    Порядок проверок: быстрые фильтры первыми.
    """
    low = normalize(text)

    # 1. Стоп-слова
    for stop in STOP_KEYWORDS:
        if stop in low:
            return False

    # 2. Хотя бы одно обязательное слово
    if not any(kw in low for kw in REQUIRED_KEYWORDS):
        return False

    # 3. «Шумовой» контент
    if is_noise_content(text):
        return False

    # 4. Зарубежные вакансии
    if is_abroad(text):
        return False

    # 5. Офис в другом городе (без крупных компаний)
    if has_wrong_city_office(text):
        return False

    # 6. Слишком большой опыт
    if has_too_much_experience(text):
        return False

    # 7. Руководящая должность
    if has_management_role(text):
        return False

    # 8. Требование высшего образования
    if has_education_requirement(text):
        return False

    # 9. Неизвестная специальность
    if has_unknown_direction(text):
        return False

    return True


def detect_direction(text: str) -> Optional[str]:
    """
    Определяет направление вакансии.
    Улучшена точность: учитываем хэш-теги и более специфичные фразы.
    """
    low = normalize(text)
    scores: dict[str, int] = {}

    for direction, keywords in DIRECTIONS.items():
        count = 0
        for kw in keywords:
            if kw in low:
                # Хэш-теги и точные фразы имеют больший вес
                weight = 3 if kw.startswith("#") or " " in kw else 1
                count += weight
        if count:
            scores[direction] = count

    if not scores:
        return None

    # Дополнительное уточнение: если высокий балл у нескольких — берём максимум
    return max(scores, key=lambda k: scores[k])


def detect_opportunity_type(text: str) -> str:
    """Определяет тип возможности. Порядок важен: стажировка > проект > мероприятие > вакансия."""
    low = normalize(text)
    for opp_type in ("стажировка", "проект", "мероприятие", "вакансия"):
        keywords = OPPORTUNITY_TYPES[opp_type]
        if any(kw in low for kw in keywords):
            return opp_type
    return "вакансия"


def detect_publish_channel(direction: Optional[str], opp_type: str) -> str:
    if opp_type == "мероприятие":
        return "as_is"
    if opp_type == "проект":
        return "project"
    return "vacancies"


def detect_is_paid(text: str) -> Optional[bool]:
    low = normalize(text)
    paid_signals = ["зарплата", "оплата", "оплачивается", "₽", "руб", "rub",
                    "оплачиваем", "вознаграждение", "гонорар"]
    unpaid_signals = ["бесплатно", "без оплаты", "добровольно"]
    if any(s in low for s in unpaid_signals):
        return False
    if any(s in low for s in paid_signals):
        return True
    return None


def detect_is_remote(text: str) -> Optional[bool]:
    low = normalize(text)
    remote_signals = ["удалённо", "удаленно", "remote", "из любой точки", "онлайн-стажировка"]
    office_signals = ["офис", "в офисе", "очно", "на месте", "гибрид"]
    if any(s in low for s in remote_signals):
        return True
    if any(s in low for s in office_signals):
        return False
    return None


def extract_company(text: str) -> str:
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
    low = normalize(text)
    score = 0

    score += sum(2 for kw in PRIORITY_KEYWORDS if kw in low)

    if direction:
        score += 10

    if is_remote is True:
        score += 15

    if is_paid is True:
        score += 10

    if "студент" in low:
        score += 8

    if TARGET_CITY in low:
        score += 20  # Вакансии в Чебоксарах — высший приоритет

    # Явные джун/интерн-маркеры — бонус
    if any(kw in low for kw in ["junior", "джун", "intern", "стажёр", "стажер", "без опыта"]):
        score += 10

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
