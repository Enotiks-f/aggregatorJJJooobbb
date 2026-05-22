import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_PROJECT_ROOT / ".env")


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Укажите {name} в .env")
    return value


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str
    worker_url: str | None


def load_settings() -> Settings:
    worker = os.getenv("WORKER_URL", "").strip()
    return Settings(
        bot_token=_require("BOT_TOKEN"),
        worker_url=worker or None,
    )
