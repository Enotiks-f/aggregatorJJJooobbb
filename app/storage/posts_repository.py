"""Репозиторий распарсенных постов Telegram (с дедупликацией по содержимому)."""

from __future__ import annotations

import hashlib
import re
import sqlite3
from pathlib import Path

from app.core.database import init_schema, open_connection


def _normalize_for_hash(text: str) -> str:
    """Приводит текст к каноническому виду для сравнения."""
    text = text.lower()
    # удаляем пунктуацию, оставляем буквы, цифры, пробелы
    text = re.sub(r'[^\w\s]', ' ', text)
    # удаляем лишние пробелы
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _text_hash(raw_text: str) -> str:
    """Возвращает MD5 хеш нормализованного текста."""
    norm = _normalize_for_hash(raw_text)
    return hashlib.md5(norm.encode('utf-8')).hexdigest()


class PostsRepository:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._conn: sqlite3.Connection | None = None

    def connect(self) -> None:
        self._conn = open_connection(self.path)
        init_schema(self._conn)
        self._migrate()

    def _migrate(self) -> None:
        """Добавляет новые колонки для дедупликации, если они отсутствуют."""
        cur = self.connection.execute("PRAGMA table_info(parsed_posts)")
        columns = {row[1] for row in cur.fetchall()}
        if "raw_text" not in columns:
            self.connection.execute("ALTER TABLE parsed_posts ADD COLUMN raw_text TEXT")
        if "text_hash" not in columns:
            self.connection.execute("ALTER TABLE parsed_posts ADD COLUMN text_hash TEXT")
            self.connection.execute("CREATE INDEX IF NOT EXISTS idx_text_hash ON parsed_posts (text_hash)")

        # Заполняем хеши для старых записей, где raw_text есть, а text_hash NULL
        rows = self.connection.execute(
            "SELECT id, raw_text FROM parsed_posts WHERE raw_text IS NOT NULL AND text_hash IS NULL"
        ).fetchall()
        for row_id, raw in rows:
            h = _text_hash(raw)
            self.connection.execute("UPDATE parsed_posts SET text_hash = ? WHERE id = ?", (h, row_id))
        self.connection.commit()

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
        """Проверяет существование поста по URL."""
        row = self.connection.execute(
            "SELECT 1 FROM parsed_posts WHERE post_url = ? LIMIT 1",
            (post_url,),
        ).fetchone()
        return row is not None

    def exists_by_text(self, raw_text: str) -> bool:
        """Проверяет, есть ли уже пост с таким же содержимым (по хешу)."""
        h = _text_hash(raw_text)
        row = self.connection.execute(
            "SELECT 1 FROM parsed_posts WHERE text_hash = ? LIMIT 1",
            (h,),
        ).fetchone()
        return row is not None

    def filter_new(self, results: list) -> tuple[list, int]:
        """
        Оставляет только посты, которых ещё нет в БД (ни по URL, ни по хешу).
        Возвращает (new_results, skipped_count).
        """
        if not results:
            return [], 0

        urls = [r.post_url for r in results]
        hashes = [_text_hash(r.raw_text) for r in results]

        placeholders_url = ",".join("?" * len(urls))
        placeholders_hash = ",".join("?" * len(hashes))

        # Существующие URL
        existing_urls = {
            row["post_url"] for row in self.connection.execute(
                f"SELECT post_url FROM parsed_posts WHERE post_url IN ({placeholders_url})",
                urls,
            ).fetchall()
        }

        # Существующие хеши
        existing_hashes = {
            row["text_hash"] for row in self.connection.execute(
                f"SELECT text_hash FROM parsed_posts WHERE text_hash IN ({placeholders_hash})",
                hashes,
            ).fetchall()
        }

        new_results = []
        for r in results:
            if r.post_url not in existing_urls and _text_hash(r.raw_text) not in existing_hashes:
                new_results.append(r)

        skipped = len(results) - len(new_results)
        return new_results, skipped

    def save_many(self, results: list) -> int:
        """
        Сохраняет только уникальные посты (проверка на дубликат по хешу выполняется вызывающим кодом).
        """
        if not results:
            return 0

        self.connection.executemany(
            """
            INSERT OR IGNORE INTO parsed_posts (
                post_url, channel, message_id, publish_channel, opportunity_type,
                direction, company, text_preview, is_paid, is_remote, deadline, score,
                raw_text, text_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    r.raw_text,
                    _text_hash(r.raw_text),
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