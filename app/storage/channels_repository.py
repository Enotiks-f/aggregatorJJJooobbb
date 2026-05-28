"""Репозиторий каналов для парсинга."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.core.database import init_schema, open_connection


class ChannelsRepository:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._conn: sqlite3.Connection | None = None

    def connect(self) -> None:
        self._conn = open_connection(self.path)
        init_schema(self._conn)

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    @property
    def connection(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("Репозиторий каналов не подключён к БД")
        return self._conn

    def count(self) -> int:
        row = self.connection.execute(
            "SELECT COUNT(*) AS cnt FROM parser_channels"
        ).fetchone()
        return int(row["cnt"])

    def list_all(self) -> list[str]:
        rows = self.connection.execute(
            "SELECT username FROM parser_channels ORDER BY username COLLATE NOCASE"
        ).fetchall()
        return [row["username"] for row in rows]

    def seed_defaults(self, usernames: list[str]) -> int:
        if self.count() > 0:
            return 0
        return self.add_many(usernames)

    def add_many(self, usernames: list[str]) -> int:
        added = 0
        for name in usernames:
            cursor = self.connection.execute(
                "INSERT OR IGNORE INTO parser_channels (username) VALUES (?)",
                (name,),
            )
            if cursor.rowcount > 0:
                added += 1
        self.connection.commit()
        return added

    def remove_many(self, usernames: list[str]) -> int:
        if not usernames:
            return 0
        placeholders = ",".join("?" * len(usernames))
        cursor = self.connection.execute(
            f"DELETE FROM parser_channels WHERE username IN ({placeholders})",
            usernames,
        )
        self.connection.commit()
        return cursor.rowcount

    def find_missing(self, usernames: list[str]) -> list[str]:
        if not usernames:
            return []
        existing = set(self.list_all())
        return [name for name in usernames if name not in existing]
