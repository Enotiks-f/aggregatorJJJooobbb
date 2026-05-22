"""SQLite: схема и подключение."""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS parsed_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_url TEXT NOT NULL UNIQUE,
    channel TEXT NOT NULL,
    message_id INTEGER NOT NULL,
    publish_channel TEXT NOT NULL,
    opportunity_type TEXT NOT NULL,
    direction TEXT,
    company TEXT NOT NULL DEFAULT '',
    text_preview TEXT NOT NULL,
    is_paid INTEGER,
    is_remote INTEGER,
    deadline TEXT NOT NULL DEFAULT '',
    score INTEGER NOT NULL,
    parsed_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (channel, message_id)
);

CREATE INDEX IF NOT EXISTS idx_parsed_posts_channel ON parsed_posts (channel);
CREATE INDEX IF NOT EXISTS idx_parsed_posts_parsed_at ON parsed_posts (parsed_at);
"""


def open_connection(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
    conn.commit()
