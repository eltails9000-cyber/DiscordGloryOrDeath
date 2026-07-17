"""
Moderation service — warnings, mutes, bans, case management.
"""

from __future__ import annotations

from typing import Optional

import discord

from services.database_service import execute, fetchall, fetchone
from utils.logger import get_logger

log = get_logger("moderation")


# ── Warnings ──────────────────────────────────────────────────────────────────

async def add_warning(
    guild_id: int,
    user_id: int,
    moderator_id: int,
    reason: str,
) -> int:
    warn_id = await execute(
        "INSERT INTO warnings (guild_id, user_id, moderator_id, reason) VALUES (?, ?, ?, ?)",
        (guild_id, user_id, moderator_id, reason),
    )
    log.info("Warning #%d added for user %d in guild %d", warn_id, user_id, guild_id)
    return warn_id


async def get_warnings(guild_id: int, user_id: int) -> list:
    return await fetchall(
        "SELECT * FROM warnings WHERE guild_id = ? AND user_id = ? ORDER BY created_at DESC",
        (guild_id, user_id),
    )


async def count_warnings(guild_id: int, user_id: int) -> int:
    row = await fetchone(
        "SELECT COUNT(*) as cnt FROM warnings WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id),
    )
    return row["cnt"] if row else 0


async def remove_warning(warn_id: int, guild_id: int) -> bool:
    rows = await fetchone(
        "SELECT id FROM warnings WHERE id = ? AND guild_id = ?", (warn_id, guild_id)
    )
    if not rows:
        return False
    await execute("DELETE FROM warnings WHERE id = ?", (warn_id,))
    return True


async def clear_warnings(guild_id: int, user_id: int) -> int:
    count = await count_warnings(guild_id, user_id)
    await execute(
        "DELETE FROM warnings WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id),
    )
    return count


# ── Mutes ─────────────────────────────────────────────────────────────────────

async def log_mute(
    guild_id: int,
    user_id: int,
    moderator_id: int,
    reason: str,
    expires_at: Optional[str] = None,
) -> int:
    return await execute(
        "INSERT INTO mutes (guild_id, user_id, moderator_id, reason, expires_at) VALUES (?, ?, ?, ?, ?)",
        (guild_id, user_id, moderator_id, reason, expires_at),
    )


# ── Bans ──────────────────────────────────────────────────────────────────────

async def log_ban(
    guild_id: int,
    user_id: int,
    moderator_id: int,
    reason: str,
) -> int:
    return await execute(
        "INSERT INTO bans (guild_id, user_id, moderator_id, reason) VALUES (?, ?, ?, ?)",
        (guild_id, user_id, moderator_id, reason),
    )


async def get_ban_history(guild_id: int, user_id: int) -> list:
    return await fetchall(
        "SELECT * FROM bans WHERE guild_id = ? AND user_id = ? ORDER BY created_at DESC",
        (guild_id, user_id),
    )
