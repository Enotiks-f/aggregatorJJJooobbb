"""Запуск парсинга каналов (для CLI и Telegram-бота)."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List

from telethon import TelegramClient
from telethon.errors import (
    ChannelPrivateError,
    ChatAdminRequiredError,
    FloodWaitError,
    UsernameNotOccupiedError,
)
from telethon.tl.types import Message

from app.storage.channels_repository import ChannelsRepository
from app.storage.posts_repository import PostsRepository

from .classifier import VacancyResult, build_post_url, classify
from .config import (
    API_HASH,
    API_ID,
    DATABASE_PATH,
    DEFAULT_CHANNELS,
    GOOGLE_SPREADSHEET_ID,
    MAX_POST_AGE_DAYS,
    MESSAGES_LIMIT,
    MIN_MESSAGE_LENGTH,
    PHONE,
    SESSION_NAME,
)
from .exporter import export_to_google_sheets

log = logging.getLogger(__name__)

DEFAULT_MIN_SCORE = 5


@dataclass(slots=True)
class ParseSummary:
    channels_count: int
    total_found: int
    filtered_count: int
    skipped_in_db: int
    exported_count: int
    sheet_url: str
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


def spreadsheet_url() -> str:
    return f"https://docs.google.com/spreadsheets/d/{GOOGLE_SPREADSHEET_ID}/edit"


async def search_channel(
    client: TelegramClient,
    channel: str,
    limit: int,
    max_age_days: int,
    min_length: int,
    repo: PostsRepository,
) -> List[VacancyResult]:
    results: List[VacancyResult] = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)

    try:
        log.info("📡 Читаю канал: @%s", channel)
        async for message in client.iter_messages(channel, limit=limit):
            msg: Message = message

            if not msg.text or len(msg.text) < min_length:
                continue

            if msg.date and msg.date < cutoff:
                break

            if repo.exists(build_post_url(channel, msg.id)):
                continue

            result = classify(msg.text, channel, msg.id)
            if result:
                results.append(result)

        log.info("  → Найдено %s релевантных из @%s", len(results), channel)

    except FloodWaitError as e:
        log.warning("⚠️ FloodWait %ss для @%s", e.seconds, channel)
        await asyncio.sleep(min(e.seconds, 60))
    except ChannelPrivateError:
        log.warning("🔒 Канал @%s приватный", channel)
    except UsernameNotOccupiedError:
        log.warning("❓ Канал @%s не найден", channel)
    except ChatAdminRequiredError:
        log.warning("🔒 Нет доступа к @%s", channel)
    except Exception as e:
        log.error("💥 Ошибка @%s: %s", channel, e)

    return results


OnParsingDone = Callable[[], Awaitable[None]]


def load_channels_for_parse(channels: List[str] | None = None) -> tuple[List[str], str | None]:
    if channels is not None:
        return channels, None

    repo = ChannelsRepository(DATABASE_PATH)
    repo.connect()
    try:
        repo.seed_defaults(DEFAULT_CHANNELS)
        loaded = repo.list_all()
    finally:
        repo.close()

    if not loaded:
        return [], "Список каналов пуст. Добавьте каналы: /add_chennel"
    return loaded, None


async def run_search(
    *,
    channels: List[str] | None = None,
    limit: int = MESSAGES_LIMIT,
    max_age_days: int = MAX_POST_AGE_DAYS,
    min_length: int = MIN_MESSAGE_LENGTH,
    min_score: int = DEFAULT_MIN_SCORE,
    on_parsing_done: OnParsingDone | None = None,
) -> ParseSummary:
    channels, channels_error = load_channels_for_parse(channels)
    sheet_url = spreadsheet_url()

    if channels_error:
        return ParseSummary(
            channels_count=0,
            total_found=0,
            filtered_count=0,
            skipped_in_db=0,
            exported_count=0,
            sheet_url=sheet_url,
            error=channels_error,
        )

    if not API_ID or not API_HASH:
        return ParseSummary(
            channels_count=len(channels),
            total_found=0,
            filtered_count=0,
            skipped_in_db=0,
            exported_count=0,
            sheet_url=sheet_url,
            error="Не заданы TELEGRAM_API_ID / TELEGRAM_API_HASH в .env",
        )

    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    all_results: List[VacancyResult] = []
    repo = PostsRepository(DATABASE_PATH)
    repo.connect()

    try:
        async with client:
            await client.start(phone=PHONE)
            log.info("🚀 Поиск по %s каналам", len(channels))

            for channel in channels:
                channel_results = await search_channel(
                    client, channel, limit, max_age_days, min_length, repo,
                )
                all_results.extend(channel_results)
                await asyncio.sleep(2)

        filtered = [r for r in all_results if r.score >= min_score]
        filtered.sort(key=lambda r: r.score, reverse=True)
        new_results, skipped_in_db = repo.filter_new(filtered)

        if on_parsing_done is not None:
            await on_parsing_done()

        exported_count = 0
        if new_results:
            sheet_url = export_to_google_sheets(new_results)
            exported_count = repo.save_many(new_results)

        return ParseSummary(
            channels_count=len(channels),
            total_found=len(all_results),
            filtered_count=len(filtered),
            skipped_in_db=skipped_in_db,
            exported_count=exported_count,
            sheet_url=sheet_url,
        )
    except Exception as e:
        log.exception("Ошибка парсинга")
        return ParseSummary(
            channels_count=len(channels),
            total_found=len(all_results),
            filtered_count=0,
            skipped_in_db=0,
            exported_count=0,
            sheet_url=sheet_url,
            error=str(e),
        )
    finally:
        repo.close()
