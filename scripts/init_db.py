"""Инициализация SQLite: python scripts/init_db.py"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

from app.core.database import init_schema, open_connection
from app.service.parser.channel.config import DATABASE_PATH

load_dotenv(_ROOT / ".env")


def main() -> None:
    conn = open_connection(DATABASE_PATH)
    init_schema(conn)
    conn.close()
    print(f"БД инициализирована: {DATABASE_PATH.resolve()}")


if __name__ == "__main__":
    main()
