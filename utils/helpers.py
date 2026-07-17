"""
Miscellaneous helper utilities.
"""

from __future__ import annotations

import re
import random
import string
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

import discord


# ── Time parsing ──────────────────────────────────────────────────────────────

_DURATION_RE = re.compile(
    r"(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?",
    re.IGNORECASE,
)


def parse_duration(text: str) -> Optional[timedelta]:
    """
    Parse duration strings like '1d2h30m10s'.
    Returns None if nothing was parsed.
    """
    m = _DURATION_RE.fullmatch(text.strip())
    if not m or not any(m.groups()):
        # Try plain seconds
        try:
            return timedelta(seconds=int(text))
        except ValueError:
            return None
    days, hours, minutes, seconds = (int(g or 0) for g in m.groups())
    return timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)


def duration_str(seconds: int) -> str:
    """Convert seconds to a human-readable string."""
    if seconds < 60:
        return f"{seconds}s"
    parts: list[str] = []
    for unit, label in ((86400, "d"), (3600, "h"), (60, "m"), (1, "s")):
        if seconds >= unit:
            parts.append(f"{seconds // unit}{label}")
            seconds %= unit
    return " ".join(parts)


def utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


def discord_timestamp(dt: datetime, style: str = "R") -> str:
    """Discord <t:UNIX:style> timestamp."""
    return f"<t:{int(dt.timestamp())}:{style}>"


# ── Captcha generation ─────────────────────────────────────────────────────────

def generate_captcha(length: int = 6) -> str:
    chars = string.ascii_uppercase + string.digits
    # Remove confusable characters
    chars = chars.translate(str.maketrans("", "", "0OIl1"))
    return "".join(random.choices(chars, k=length))


# ── Discord utilities ─────────────────────────────────────────────────────────

def resolve_color(value: Any) -> int:
    """Parse a hex color string like '#FF0000' or 0xFF0000."""
    if isinstance(value, int):
        return value
    text = str(value).lstrip("#")
    try:
        return int(text, 16)
    except ValueError:
        return 0x5865F2


async def safe_send(
    channel: discord.abc.Messageable,
    *args: Any,
    **kwargs: Any,
) -> Optional[discord.Message]:
    try:
        return await channel.send(*args, **kwargs)
    except (discord.Forbidden, discord.HTTPException):
        return None


async def try_dm(
    user: discord.User | discord.Member,
    *args: Any,
    **kwargs: Any,
) -> bool:
    try:
        await user.send(*args, **kwargs)
        return True
    except (discord.Forbidden, discord.HTTPException):
        return False


def truncate(text: str, limit: int = 1024, suffix: str = "…") -> str:
    if len(text) <= limit:
        return text
    return text[: limit - len(suffix)] + suffix


def ordinal(n: int) -> str:
    """Return '1st', '2nd', '3rd', etc."""
    if 11 <= n % 100 <= 13:
        return f"{n}th"
    return f"{n}{['th', 'st', 'nd', 'rd', 'th'][min(n % 10, 4)]}"


# ── URL / scam detection ──────────────────────────────────────────────────────

_URL_RE = re.compile(
    r"https?://[^\s<>\"]+|www\.[^\s<>\"]+",
    re.IGNORECASE,
)

_INVITE_RE = re.compile(
    r"discord(?:\.gg|\.com/invite)/[a-zA-Z0-9\-]+",
    re.IGNORECASE,
)


def extract_urls(text: str) -> list[str]:
    return _URL_RE.findall(text)


def extract_invites(text: str) -> list[str]:
    return _INVITE_RE.findall(text)


def extract_domain(url: str) -> str:
    m = re.search(r"(?:https?://)?(?:www\.)?([^/\s?#]+)", url, re.IGNORECASE)
    return m.group(1).lower() if m else url.lower()
