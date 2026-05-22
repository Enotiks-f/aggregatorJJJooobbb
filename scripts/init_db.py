"""Инициализация SQLite: python scripts/init_db.py"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

from app.core.database import init_schema, open_connection
from app.service.parser.channel.config import DATABASE_PATH, DEFAULT_CHANNELS
from app.storage.channels_repository import ChannelsRepository

load_dotenv(_ROOT / ".env")


def main() -> None:
    conn = open_connection(DATABASE_PATH)
    init_schema(conn)
    conn.close()

    channels_repo = ChannelsRepository(DATABASE_PATH)
    channels_repo.connect()
    seeded = channels_repo.seed_defaults(DEFAULT_CHANNELS)
    total = channels_repo.count()
    channels_repo.close()

    print(f"БД инициализирована: {DATABASE_PATH.resolve()}")
    print(f"Каналов в списке: {total} (добавлено из defaults: {seeded})")


if __name__ == "__main__":
    main()
