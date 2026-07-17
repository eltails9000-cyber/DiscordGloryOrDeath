"""
Database initialization and schema management.
Uses aiosqlite for fully async SQLite access.
"""

from __future__ import annotations

import aiosqlite
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

import config
from utils.logger import get_logger

log = get_logger("database")

_DB_PATH = config.DATABASE_PATH


async def init_db() -> None:
    """Create all tables if they do not exist."""
    Path(_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.executescript(SCHEMA)
        await db.commit()
    log.info("Database initialised at %s", _DB_PATH)


@asynccontextmanager
async def get_db() -> AsyncIterator[aiosqlite.Connection]:
    """Async context manager yielding a configured DB connection.

    Usage::

        async with get_db() as db:
            ...
    """
    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")
        yield db


# ─── Schema ───────────────────────────────────────────────────────────────────

SCHEMA = """
-- Guild configuration
CREATE TABLE IF NOT EXISTS guild_config (
    guild_id        INTEGER PRIMARY KEY,
    prefix          TEXT    DEFAULT '!',
    log_channel     INTEGER,
    mod_log_channel INTEGER,
    welcome_channel INTEGER,
    leave_channel   INTEGER,
    suggestion_channel INTEGER,
    security_channel INTEGER,
    updated_at      TEXT    DEFAULT (datetime('now'))
);

-- Warnings
CREATE TABLE IF NOT EXISTS warnings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id    INTEGER NOT NULL,
    user_id     INTEGER NOT NULL,
    moderator_id INTEGER NOT NULL,
    reason      TEXT    NOT NULL,
    created_at  TEXT    DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_warnings_guild_user ON warnings(guild_id, user_id);

-- Mutes
CREATE TABLE IF NOT EXISTS mutes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id    INTEGER NOT NULL,
    user_id     INTEGER NOT NULL,
    moderator_id INTEGER NOT NULL,
    reason      TEXT,
    expires_at  TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

-- Bans
CREATE TABLE IF NOT EXISTS bans (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id    INTEGER NOT NULL,
    user_id     INTEGER NOT NULL,
    moderator_id INTEGER NOT NULL,
    reason      TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

-- Giveaways
CREATE TABLE IF NOT EXISTS giveaways (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id    INTEGER NOT NULL,
    channel_id  INTEGER NOT NULL,
    message_id  INTEGER UNIQUE,
    host_id     INTEGER NOT NULL,
    prize       TEXT    NOT NULL,
    winners     INTEGER NOT NULL DEFAULT 1,
    ends_at     TEXT    NOT NULL,
    ended       INTEGER NOT NULL DEFAULT 0,
    requirements TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS giveaway_entries (
    giveaway_id INTEGER NOT NULL REFERENCES giveaways(id) ON DELETE CASCADE,
    user_id     INTEGER NOT NULL,
    PRIMARY KEY (giveaway_id, user_id)
);

-- Verification
CREATE TABLE IF NOT EXISTS verification_attempts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id    INTEGER NOT NULL,
    user_id     INTEGER NOT NULL,
    attempts    INTEGER NOT NULL DEFAULT 0,
    verified    INTEGER NOT NULL DEFAULT 0,
    captcha     TEXT,
    created_at  TEXT DEFAULT (datetime('now')),
    verified_at TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_verify_guild_user ON verification_attempts(guild_id, user_id);

-- Scheduled announcements
CREATE TABLE IF NOT EXISTS scheduled_announcements (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id    INTEGER NOT NULL,
    channel_id  INTEGER NOT NULL,
    author_id   INTEGER NOT NULL,
    title       TEXT,
    content     TEXT    NOT NULL,
    color       INTEGER DEFAULT 5793266,
    scheduled_at TEXT   NOT NULL,
    sent        INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT DEFAULT (datetime('now'))
);

-- Polls
CREATE TABLE IF NOT EXISTS polls (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id    INTEGER NOT NULL,
    channel_id  INTEGER NOT NULL,
    message_id  INTEGER UNIQUE,
    author_id   INTEGER NOT NULL,
    question    TEXT    NOT NULL,
    options     TEXT    NOT NULL,  -- JSON array
    ends_at     TEXT,
    ended       INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS poll_votes (
    poll_id     INTEGER NOT NULL REFERENCES polls(id) ON DELETE CASCADE,
    user_id     INTEGER NOT NULL,
    option_idx  INTEGER NOT NULL,
    PRIMARY KEY (poll_id, user_id)
);

-- AI Knowledge base
CREATE TABLE IF NOT EXISTS ai_knowledge (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id    INTEGER NOT NULL,
    keyword     TEXT    NOT NULL,
    answer      TEXT    NOT NULL,
    added_by    INTEGER NOT NULL,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_ai_knowledge_guild ON ai_knowledge(guild_id);

-- Security events
CREATE TABLE IF NOT EXISTS security_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id    INTEGER NOT NULL,
    event_type  TEXT    NOT NULL,
    user_id     INTEGER,
    details     TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

-- Suggestions
CREATE TABLE IF NOT EXISTS suggestions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id    INTEGER NOT NULL,
    author_id   INTEGER NOT NULL,
    message_id  INTEGER UNIQUE,
    content     TEXT    NOT NULL,
    status      TEXT    DEFAULT 'pending',
    reviewed_by INTEGER,
    review_note TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);
"""
