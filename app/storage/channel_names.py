"""Разбор username каналов из текста команды бота."""

from __future__ import annotations

import re

_TME_RE = re.compile(r"(?:https?://)?t\.me/([a-zA-Z0-9_]+)", re.IGNORECASE)
_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,32}$")


def normalize_channel(raw: str) -> str | None:
    value = raw.strip().lstrip("@").strip("/")
    if not value:
        return None

    match = _TME_RE.search(value)
    if match:
        value = match.group(1)

    if _USERNAME_RE.fullmatch(value):
        return value.lower()
    return None


def parse_channels(text: str) -> list[str]:
    """Принимает каналы через пробел, запятую, точку с запятой или с новой строки."""
    if not text or not text.strip():
        return []

    found: list[str] = []
    seen: set[str] = set()

    for part in re.split(r"[\s,;]+", text.strip()):
        username = normalize_channel(part)
        if username and username not in seen:
            seen.add(username)
            found.append(username)

    return found
