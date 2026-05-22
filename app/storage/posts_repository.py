"""Репозиторий распарсенных постов Telegram."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from app.core.database import init_schema, open_connection


class PostsRepository:
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
            raise RuntimeError("Репозиторий не подключён к БД")
        return self._conn

    def exists(self, post_url: str) -> bool:
        row = self.connection.execute(
            "SELECT 1 FROM parsed_posts WHERE post_url = ? LIMIT 1",
            (post_url,),
        ).fetchone()
        return row is not None

    def filter_new(self, results: list) -> tuple[list, int]:
        """Оставляет только посты, которых ещё нет в БД."""
        if not results:
            return [], 0

        urls = [r.post_url for r in results]
        placeholders = ",".join("?" * len(urls))
        rows = self.connection.execute(
            f"SELECT post_url FROM parsed_posts WHERE post_url IN ({placeholders})",
            urls,
        ).fetchall()
        existing = {row["post_url"] for row in rows}

        new_results = [r for r in results if r.post_url not in existing]
        skipped = len(results) - len(new_results)
        return new_results, skipped

    def save_many(self, results: list) -> int:
        if not results:
            return 0

        self.connection.executemany(
            """
            INSERT OR IGNORE INTO parsed_posts (
                post_url, channel, message_id, publish_channel, opportunity_type,
                direction, company, text_preview, is_paid, is_remote, deadline, score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    r.post_url,
                    r.channel,
                    _message_id_from_url(r.post_url),
                    r.publish_channel,
                    r.opportunity_type,
                    r.direction,
                    r.company,
                    r.text_preview,
                    _bool_to_db(r.is_paid),
                    _bool_to_db(r.is_remote),
                    r.deadline,
                    r.score,
                )
                for r in results
            ],
        )
        self.connection.commit()
        return self.connection.total_changes


def _message_id_from_url(post_url: str) -> int:
    return int(post_url.rsplit("/", 1)[-1])


def _bool_to_db(value: bool | None) -> int | None:
    if value is None:
        return None
    return int(value)
