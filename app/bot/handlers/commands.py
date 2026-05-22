from __future__ import annotations

import asyncio
import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.bot.messages import (
    HELP_TEXT,
    PARSE_BUSY_TEXT,
    PARSE_STARTED_TEXT,
    PARSE_TABLE_TEXT,
    START_TEXT,
)
from app.service.parser.channel.runner import ParseSummary, run_search

log = logging.getLogger(__name__)
router = Router(name="commands")

_parse_lock = asyncio.Lock()


def format_parse_summary(summary: ParseSummary) -> str:
    if summary.error:
        return (
            "❌ Парсинг завершился с ошибкой\n\n"
            f"{summary.error}\n\n"
            f"📊 Таблица: {summary.sheet_url}"
        )

    lines = [
        "✅ Парсинг завершён",
        "",
        f"📡 Каналов обработано: {summary.channels_count}",
        f"🔍 Найдено релевантных: {summary.total_found}",
        f"📋 После фильтра score: {summary.filtered_count}",
        f"⏭ Уже в БД (пропущено): {summary.skipped_in_db}",
        f"📤 Добавлено в таблицу: {summary.exported_count}",
    ]

    if summary.exported_count == 0 and summary.filtered_count > 0:
        lines.append("")
        lines.append("Новых записей нет — все подходящие посты уже были в базе.")

    lines.extend(["", f"📊 Таблица: {summary.sheet_url}"])
    return "\n".join(lines)


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(START_TEXT)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT)


async def _safe_delete(msg: Message | None) -> None:
    if msg is None:
        return
    try:
        await msg.delete()
    except Exception:
        log.warning("Не удалось удалить служебное сообщение")


@router.message(Command("jjjoobbb"))
async def cmd_jjjoobbb(message: Message) -> None:
    if _parse_lock.locked():
        await message.answer(PARSE_BUSY_TEXT)
        return

    parse_wait_msg = await message.answer(PARSE_STARTED_TEXT)
    table_wait_msg: Message | None = None

    async def on_parsing_done() -> None:
        nonlocal table_wait_msg
        await _safe_delete(parse_wait_msg)
        table_wait_msg = await message.answer(PARSE_TABLE_TEXT)

    async with _parse_lock:
        try:
            summary = await run_search(on_parsing_done=on_parsing_done)
            text = format_parse_summary(summary)
        except Exception as e:
            log.exception("Парсинг из бота")
            text = f"❌ Не удалось выполнить парсинг:\n{e}"

    await _safe_delete(parse_wait_msg)
    await _safe_delete(table_wait_msg)
    await message.answer(text)
