"""
Generic database service providing CRUD helpers on top of aiosqlite.
"""

from __future__ import annotations

import aiosqlite
import json
from typing import Any, Optional

from database import get_db
from utils.logger import get_logger

log = get_logger("db_service")


async def fetchone(query: str, params: tuple = ()) -> Optional[aiosqlite.Row]:
    async with get_db() as db:
        async with db.execute(query, params) as cur:
            return await cur.fetchone()


async def fetchall(query: str, params: tuple = ()) -> list[aiosqlite.Row]:
    async with get_db() as db:
        async with db.execute(query, params) as cur:
            return await cur.fetchall()


async def execute(query: str, params: tuple = ()) -> int:
    """Execute a write query, return lastrowid."""
    async with get_db() as db:
        async with db.execute(query, params) as cur:
            await db.commit()
            return cur.lastrowid or 0


async def executemany(query: str, params_list: list[tuple]) -> None:
    async with get_db() as db:
        await db.executemany(query, params_list)
        await db.commit()


# ── Guild config ──────────────────────────────────────────────────────────────

async def get_guild_config(guild_id: int) -> Optional[aiosqlite.Row]:
    return await fetchone("SELECT * FROM guild_config WHERE guild_id = ?", (guild_id,))


async def upsert_guild_config(guild_id: int, **kwargs: Any) -> None:
    cols = ", ".join(kwargs.keys())
    placeholders = ", ".join("?" * len(kwargs))
    updates = ", ".join(f"{k} = excluded.{k}" for k in kwargs)
    await execute(
        f"INSERT INTO guild_config (guild_id, {cols}) VALUES (?, {placeholders}) "
        f"ON CONFLICT(guild_id) DO UPDATE SET {updates}, updated_at = datetime('now')",
        (guild_id, *kwargs.values()),
    )
