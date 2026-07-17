"""
Central configuration for the Discord bot.
All settings are read from environment variables or .env file.
No hardcoded IDs — all channel/role IDs are configured here.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


def _env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


def _env_int(key: str, default: int = 0) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default


def _env_list(key: str, sep: str = ",") -> list[int]:
    raw = os.getenv(key, "")
    if not raw.strip():
        return []
    try:
        return [int(x.strip()) for x in raw.split(sep) if x.strip()]
    except ValueError:
        return []


def _env_bool(key: str, default: bool = False) -> bool:
    val = os.getenv(key, str(default)).lower()
    return val in ("1", "true", "yes", "on")


# ─── Bot Identity ─────────────────────────────────────────────────────────────

BOT_TOKEN: str = _env("DISCORD_TOKEN")
BOT_PREFIX: str = _env("BOT_PREFIX", "!")
BOT_DESCRIPTION: str = _env("BOT_DESCRIPTION", "A multi-purpose Discord bot")
OWNER_IDS: list[int] = _env_list("OWNER_IDS")

# ─── Guild ────────────────────────────────────────────────────────────────────

GUILD_ID: Optional[int] = _env_int("GUILD_ID") or None

# ─── Channels ─────────────────────────────────────────────────────────────────

CHANNEL_WELCOME: Optional[int] = _env_int("CHANNEL_WELCOME") or None
CHANNEL_LEAVE: Optional[int] = _env_int("CHANNEL_LEAVE") or None
CHANNEL_LOGS: Optional[int] = _env_int("CHANNEL_LOGS") or None
CHANNEL_MOD_LOGS: Optional[int] = _env_int("CHANNEL_MOD_LOGS") or None
CHANNEL_VERIFICATION: Optional[int] = _env_int("CHANNEL_VERIFICATION") or None
CHANNEL_ANNOUNCEMENTS: Optional[int] = _env_int("CHANNEL_ANNOUNCEMENTS") or None
CHANNEL_SUGGESTIONS: Optional[int] = _env_int("CHANNEL_SUGGESTIONS") or None
CHANNEL_SECURITY_LOGS: Optional[int] = _env_int("CHANNEL_SECURITY_LOGS") or None

# ─── Roles ────────────────────────────────────────────────────────────────────

ROLE_VERIFIED: Optional[int] = _env_int("ROLE_VERIFIED") or None
ROLE_MUTED: Optional[int] = _env_int("ROLE_MUTED") or None
ROLE_MOD: Optional[int] = _env_int("ROLE_MOD") or None
ROLE_ADMIN: Optional[int] = _env_int("ROLE_ADMIN") or None
ROLE_UNVERIFIED: Optional[int] = _env_int("ROLE_UNVERIFIED") or None

# ─── Moderation ───────────────────────────────────────────────────────────────

MOD_WARN_THRESHOLD_MUTE: int = _env_int("MOD_WARN_THRESHOLD_MUTE", 3)
MOD_WARN_THRESHOLD_KICK: int = _env_int("MOD_WARN_THRESHOLD_KICK", 5)
MOD_WARN_THRESHOLD_BAN: int = _env_int("MOD_WARN_THRESHOLD_BAN", 7)
MOD_DEFAULT_MUTE_DURATION: int = _env_int("MOD_DEFAULT_MUTE_DURATION", 600)  # seconds

# ─── Security ────────────────────────────────────────────────────────────────

SECURITY_ANTI_SPAM_ENABLED: bool = _env_bool("SECURITY_ANTI_SPAM_ENABLED", True)
SECURITY_ANTI_RAID_ENABLED: bool = _env_bool("SECURITY_ANTI_RAID_ENABLED", True)
SECURITY_ANTI_SCAM_ENABLED: bool = _env_bool("SECURITY_ANTI_SCAM_ENABLED", True)
SECURITY_ANTI_INVITE_ENABLED: bool = _env_bool("SECURITY_ANTI_INVITE_ENABLED", True)
SECURITY_ANTI_MASS_MENTION_ENABLED: bool = _env_bool("SECURITY_ANTI_MASS_MENTION_ENABLED", True)

SECURITY_SPAM_THRESHOLD: int = _env_int("SECURITY_SPAM_THRESHOLD", 5)   # messages
SECURITY_SPAM_INTERVAL: float = float(_env("SECURITY_SPAM_INTERVAL", "5"))  # seconds
SECURITY_SPAM_MUTE_DURATION: int = _env_int("SECURITY_SPAM_MUTE_DURATION", 300)  # seconds

SECURITY_RAID_JOIN_THRESHOLD: int = _env_int("SECURITY_RAID_JOIN_THRESHOLD", 10)  # joins
SECURITY_RAID_INTERVAL: float = float(_env("SECURITY_RAID_INTERVAL", "10"))  # seconds
SECURITY_RAID_LOCKDOWN_DURATION: int = _env_int("SECURITY_RAID_LOCKDOWN_DURATION", 300)  # seconds

SECURITY_MASS_MENTION_THRESHOLD: int = _env_int("SECURITY_MASS_MENTION_THRESHOLD", 5)

SECURITY_MIN_ACCOUNT_AGE: int = _env_int("SECURITY_MIN_ACCOUNT_AGE", 7)  # days
SECURITY_IGNORED_CHANNELS: list[int] = _env_list("SECURITY_IGNORED_CHANNELS")
SECURITY_IGNORED_ROLES: list[int] = _env_list("SECURITY_IGNORED_ROLES")

SCAM_DOMAINS_URL: str = _env(
    "SCAM_DOMAINS_URL",
    "https://raw.githubusercontent.com/Discord-AntiScam/scam-links/main/list.json",
)

# ─── Verification ─────────────────────────────────────────────────────────────

VERIFICATION_MIN_ACCOUNT_AGE: int = _env_int("VERIFICATION_MIN_ACCOUNT_AGE", 7)  # days
VERIFICATION_CAPTCHA_LENGTH: int = _env_int("VERIFICATION_CAPTCHA_LENGTH", 6)
VERIFICATION_CAPTCHA_TIMEOUT: int = _env_int("VERIFICATION_CAPTCHA_TIMEOUT", 120)  # seconds
VERIFICATION_MAX_ATTEMPTS: int = _env_int("VERIFICATION_MAX_ATTEMPTS", 3)

# ─── Giveaways ────────────────────────────────────────────────────────────────

GIVEAWAY_DEFAULT_WINNERS: int = _env_int("GIVEAWAY_DEFAULT_WINNERS", 1)
GIVEAWAY_MIN_DURATION: int = _env_int("GIVEAWAY_MIN_DURATION", 60)  # seconds
GIVEAWAY_MAX_DURATION: int = _env_int("GIVEAWAY_MAX_DURATION", 2592000)  # 30 days

# ─── AI ───────────────────────────────────────────────────────────────────────

OPENAI_API_KEY: str = _env("OPENAI_API_KEY")
OPENAI_MODEL: str = _env("OPENAI_MODEL", "gpt-4o-mini")
AI_MAX_TOKENS: int = _env_int("AI_MAX_TOKENS", 500)
AI_TEMPERATURE: float = float(_env("AI_TEMPERATURE", "0.7"))
AI_SYSTEM_PROMPT: str = _env(
    "AI_SYSTEM_PROMPT",
    "You are a helpful assistant for a Discord server. Answer questions concisely and accurately.",
)
AI_COOLDOWN_SECONDS: int = _env_int("AI_COOLDOWN_SECONDS", 10)

# ─── Roblox API ──────────────────────────────────────────────────────────────

ROBLOX_API_URL: str = _env("ROBLOX_API_URL")
ROBLOX_API_KEY: str = _env("ROBLOX_API_KEY")

# ─── Announcements ────────────────────────────────────────────────────────────

ANNOUNCEMENT_DEFAULT_COLOR: int = 0x5865F2  # Discord blurple
POLL_DEFAULT_DURATION: int = _env_int("POLL_DEFAULT_DURATION", 86400)  # 24h

# ─── Database ─────────────────────────────────────────────────────────────────

DATABASE_PATH: str = _env("DATABASE_PATH", "bot/data/database.db")
DATABASE_BACKUP_DIR: str = _env("DATABASE_BACKUP_DIR", "bot/data/backups/")
DATABASE_BACKUP_INTERVAL: int = _env_int("DATABASE_BACKUP_INTERVAL", 86400)  # 24h

# ─── Logging ──────────────────────────────────────────────────────────────────

LOG_LEVEL: str = _env("LOG_LEVEL", "INFO")
LOG_DIR: str = _env("LOG_DIR", "bot/data/logs/")
LOG_FILE: str = _env("LOG_FILE", "bot.log")

# ─── Cooldowns (global defaults) ──────────────────────────────────────────────

DEFAULT_COOLDOWN_RATE: int = _env_int("DEFAULT_COOLDOWN_RATE", 1)
DEFAULT_COOLDOWN_PER: float = float(_env("DEFAULT_COOLDOWN_PER", "3"))

# ─── Welcome / Leave ──────────────────────────────────────────────────────────

WELCOME_MESSAGE: str = _env(
    "WELCOME_MESSAGE",
    "Welcome to the server, {mention}! You are member #{count}.",
)
LEAVE_MESSAGE: str = _env(
    "LEAVE_MESSAGE",
    "{name} has left the server. We now have {count} members.",
)
WELCOME_COLOR: int = 0x57F287  # green
LEAVE_COLOR: int = 0xED4245   # red
