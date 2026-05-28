from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.bot.messages import (
    CHANNELS_ADD_USAGE,
    CHANNELS_EMPTY,
    CHANNELS_LIST_HEADER,
    CHANNELS_REMOVE_USAGE,
)
from app.service.parser.channel.config import DATABASE_PATH, DEFAULT_CHANNELS
from app.storage.channel_names import parse_channels
from app.storage.channels_repository import ChannelsRepository

router = Router(name="channels")


def _command_args(message: Message) -> str:
    if not message.text:
        return ""
    parts = message.text.strip().split(maxsplit=1)
    return parts[1] if len(parts) > 1 else ""


def _open_repo() -> ChannelsRepository:
    repo = ChannelsRepository(DATABASE_PATH)
    repo.connect()
    repo.seed_defaults(DEFAULT_CHANNELS)
    return repo


@router.message(Command("chennels"))
async def cmd_chennels(message: Message) -> None:
    repo = _open_repo()
    try:
        channels = repo.list_all()
    finally:
        repo.close()

    if not channels:
        await message.answer(CHANNELS_EMPTY)
        return

    lines = [CHANNELS_LIST_HEADER, ""]
    for idx, name in enumerate(channels, start=1):
        lines.append(f"{idx}. @{name}")
    lines.append("")
    lines.append(f"Всего: {len(channels)}")
    await message.answer("\n".join(lines))


@router.message(Command("add_chennel"))
async def cmd_add_chennel(message: Message) -> None:
    requested = parse_channels(_command_args(message))
    if not requested:
        await message.answer(CHANNELS_ADD_USAGE)
        return

    repo = _open_repo()
    try:
        before = set(repo.list_all())
        added_count = repo.add_many(requested)
        after = set(repo.list_all())
        added_names = sorted(after - before)
        skipped_names = [name for name in requested if name in before]
    finally:
        repo.close()

    lines = [
        f"✅ Добавлено: {added_count}",
        f"⏭ Уже в списке: {len(skipped_names)}",
    ]
    if added_names:
        lines.extend(["", "Новые каналы:"])
        lines.extend(f"• @{name}" for name in added_names)
    if skipped_names:
        lines.extend(["", "Пропущены (уже были):"])
        lines.extend(f"• @{name}" for name in skipped_names)

    await message.answer("\n".join(lines))


@router.message(Command("remove_chennel"))
async def cmd_remove_chennel(message: Message) -> None:
    requested = parse_channels(_command_args(message))
    if not requested:
        await message.answer(CHANNELS_REMOVE_USAGE)
        return

    repo = _open_repo()
    try:
        existing = set(repo.list_all())
        to_remove = [name for name in requested if name in existing]
        missing = [name for name in requested if name not in existing]
        removed_count = repo.remove_many(to_remove)
        total = repo.count()
    finally:
        repo.close()

    lines = [
        f"🗑 Удалено: {removed_count}",
        f"❓ Не найдены в списке: {len(missing)}",
        f"📋 Осталось каналов: {total}",
    ]
    if to_remove:
        lines.extend(["", "Удалены:"])
        lines.extend(f"• @{name}" for name in to_remove)
    if missing:
        lines.extend(["", "Не были в списке:"])
        lines.extend(f"• @{name}" for name in missing)

    await message.answer("\n".join(lines))
