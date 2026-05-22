"""
CLI-запуск парсера: python -m app.service.parser.channel.testing
или из папки channel: python testing.py
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from app.service.parser.channel.config import (
    CHANNELS,
    MAX_POST_AGE_DAYS,
    MESSAGES_LIMIT,
    MIN_MESSAGE_LENGTH,
)
from app.service.parser.channel.runner import DEFAULT_MIN_SCORE, run_search

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description="Поиск вакансий в Telegram-каналах")
    parser.add_argument("--channels", nargs="+", default=None)
    parser.add_argument("--limit", type=int, default=MESSAGES_LIMIT)
    parser.add_argument("--days", type=int, default=MAX_POST_AGE_DAYS)
    parser.add_argument("--min-score", type=int, default=DEFAULT_MIN_SCORE)
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args()


async def _main() -> None:
    args = parse_args()
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    summary = await run_search(
        channels=args.channels or CHANNELS,
        limit=args.limit,
        max_age_days=args.days,
        min_score=args.min_score,
    )

    log.info("Каналов: %s", summary.channels_count)
    log.info("Найдено: %s", summary.total_found)
    log.info("После фильтра: %s", summary.filtered_count)
    log.info("Пропущено (БД): %s", summary.skipped_in_db)
    log.info("Экспортировано: %s", summary.exported_count)
    log.info("Таблица: %s", summary.sheet_url)
    if summary.error:
        log.error("Ошибка: %s", summary.error)


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
