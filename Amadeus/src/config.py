from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    token: str
    guild_id: int | None
    owner_ids: List[int]
    log_level: str
    db_path: str
    prefix: str


def load_settings() -> Settings:
    load_dotenv()

    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN is not set in environment")

    guild_id_raw = os.getenv("GUILD_ID")
    guild_id = int(guild_id_raw) if guild_id_raw else None

    owner_ids_raw = os.getenv("OWNER_IDS", "").strip()
    owner_ids: List[int] = []
    if owner_ids_raw:
        owner_ids = [int(x) for x in owner_ids_raw.split(",") if x.strip().isdigit()]

    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    db_path = os.getenv("DB_PATH", "./src/data/amadeus.db")
    prefix = os.getenv("PREFIX", "!")

    return Settings(
        token=token,
        guild_id=guild_id,
        owner_ids=owner_ids,
        log_level=log_level,
        db_path=db_path,
        prefix=prefix,
    )


