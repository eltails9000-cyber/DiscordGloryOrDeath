"""
Security service — anti-spam, anti-raid, anti-scam, anti-invite.
Manages in-memory state for rate tracking and calls database for logging.
"""

from __future__ import annotations

import asyncio
import re
import time
from collections import defaultdict
from typing import Optional

import aiohttp
import discord

import config
from services.database_service import execute
from utils.helpers import extract_urls, extract_invites, extract_domain
from utils.logger import get_logger

log = get_logger("security")

# ── In-memory state ───────────────────────────────────────────────────────────

# spam tracking: guild_id -> user_id -> [timestamps]
_spam_tracker: dict[int, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))

# raid tracking: guild_id -> [join timestamps]
_raid_tracker: dict[int, list[float]] = defaultdict(list)

# lockdown state: guild_id -> bool
_lockdown_state: dict[int, bool] = {}

# scam domains set (loaded from remote)
_scam_domains: set[str] = set()
_scam_domains_loaded = False


async def load_scam_domains() -> None:
    global _scam_domains, _scam_domains_loaded
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(config.SCAM_DOMAINS_URL, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    if isinstance(data, list):
                        _scam_domains = {d.lower().strip() for d in data}
                    elif isinstance(data, dict):
                        _scam_domains = {d.lower().strip() for lst in data.values() for d in lst}
                    _scam_domains_loaded = True
                    log.info("Loaded %d scam domains", len(_scam_domains))
    except Exception as exc:
        log.warning("Failed to load scam domains: %s", exc)


# ── Permission bypass check ───────────────────────────────────────────────────

def _is_exempt(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    if member.id in config.OWNER_IDS:
        return True
    exempt_roles = set(config.SECURITY_IGNORED_ROLES)
    if any(r.id in exempt_roles for r in member.roles):
        return True
    return False


def _is_exempt_channel(channel_id: int) -> bool:
    return channel_id in config.SECURITY_IGNORED_CHANNELS


# ── Anti-Spam ────────────────────────────────────────────────────────────────

async def check_spam(message: discord.Message) -> bool:
    """Return True if this message triggered a spam action."""
    if not config.SECURITY_ANTI_SPAM_ENABLED:
        return False
    if not isinstance(message.author, discord.Member):
        return False
    if _is_exempt(message.author):
        return False
    if _is_exempt_channel(message.channel.id):
        return False

    now = time.monotonic()
    guild_id = message.guild.id  # type: ignore[union-attr]
    user_id = message.author.id

    tracker = _spam_tracker[guild_id][user_id]
    tracker.append(now)
    # Purge old entries
    cutoff = now - config.SECURITY_SPAM_INTERVAL
    _spam_tracker[guild_id][user_id] = [t for t in tracker if t > cutoff]

    if len(_spam_tracker[guild_id][user_id]) >= config.SECURITY_SPAM_THRESHOLD:
        _spam_tracker[guild_id][user_id].clear()
        await _punish_spam(message)
        return True
    return False


async def _punish_spam(message: discord.Message) -> None:
    member = message.author
    guild = message.guild
    if guild is None or not isinstance(member, discord.Member):
        return
    duration = config.SECURITY_SPAM_MUTE_DURATION
    try:
        await member.timeout(
            discord.utils.utcnow() + discord.timedelta(seconds=duration),
            reason="Anti-spam: message flood",
        )
        log.info("Timed out %s for spam in guild %d", member, guild.id)
        await _log_security_event(guild.id, "anti_spam", member.id, f"Timeout {duration}s")
    except discord.Forbidden:
        log.warning("Cannot timeout %s — insufficient permissions", member)


# ── Anti-Raid ────────────────────────────────────────────────────────────────

async def check_raid(member: discord.Member) -> bool:
    """Return True if a raid was detected."""
    if not config.SECURITY_ANTI_RAID_ENABLED:
        return False

    now = time.monotonic()
    guild_id = member.guild.id
    _raid_tracker[guild_id].append(now)
    cutoff = now - config.SECURITY_RAID_INTERVAL
    _raid_tracker[guild_id] = [t for t in _raid_tracker[guild_id] if t > cutoff]

    if len(_raid_tracker[guild_id]) >= config.SECURITY_RAID_JOIN_THRESHOLD:
        if not _lockdown_state.get(guild_id):
            await _activate_lockdown(member.guild)
            return True
    return False


async def _activate_lockdown(guild: discord.Guild) -> None:
    _lockdown_state[guild.id] = True
    log.warning("RAID DETECTED — activating lockdown in guild %d", guild.id)
    await _log_security_event(guild.id, "anti_raid", None, "Lockdown activated")
    # Lock all text channels
    for channel in guild.text_channels:
        try:
            await channel.set_permissions(
                guild.default_role,
                send_messages=False,
                reason="Anti-raid lockdown",
            )
        except discord.Forbidden:
            pass
    # Schedule unlock
    asyncio.create_task(_schedule_unlock(guild))


async def _schedule_unlock(guild: discord.Guild) -> None:
    await asyncio.sleep(config.SECURITY_RAID_LOCKDOWN_DURATION)
    await deactivate_lockdown(guild)


async def deactivate_lockdown(guild: discord.Guild) -> None:
    _lockdown_state[guild.id] = False
    for channel in guild.text_channels:
        try:
            await channel.set_permissions(
                guild.default_role,
                send_messages=None,
                reason="Anti-raid lockdown lifted",
            )
        except discord.Forbidden:
            pass
    log.info("Lockdown deactivated in guild %d", guild.id)
    await _log_security_event(guild.id, "anti_raid", None, "Lockdown deactivated")


def is_locked_down(guild_id: int) -> bool:
    return _lockdown_state.get(guild_id, False)


# ── Anti-Scam ────────────────────────────────────────────────────────────────

async def check_scam_links(message: discord.Message) -> bool:
    if not config.SECURITY_ANTI_SCAM_ENABLED:
        return False
    if not isinstance(message.author, discord.Member):
        return False
    if _is_exempt(message.author):
        return False

    urls = extract_urls(message.content)
    if not urls:
        return False

    for url in urls:
        domain = extract_domain(url)
        if domain in _scam_domains:
            await _handle_scam(message, domain)
            return True
    return False


async def _handle_scam(message: discord.Message, domain: str) -> None:
    member = message.author
    guild = message.guild
    if guild is None or not isinstance(member, discord.Member):
        return
    try:
        await message.delete()
    except discord.Forbidden:
        pass
    try:
        await member.timeout(
            discord.utils.utcnow() + discord.timedelta(seconds=600),
            reason=f"Anti-scam: posted scam link ({domain})",
        )
    except discord.Forbidden:
        pass
    log.warning("Scam link from %s: %s", member, domain)
    await _log_security_event(guild.id, "anti_scam", member.id, f"Domain: {domain}")


# ── Anti-Invite ───────────────────────────────────────────────────────────────

async def check_invite(message: discord.Message) -> bool:
    if not config.SECURITY_ANTI_INVITE_ENABLED:
        return False
    if not isinstance(message.author, discord.Member):
        return False
    if _is_exempt(message.author):
        return False

    invites = extract_invites(message.content)
    if not invites:
        return False

    # Allow own guild's invites
    guild = message.guild
    if guild is None:
        return False
    try:
        own_invites = {inv.code for inv in await guild.invites()}
        if all(
            any(inv.endswith(code) for code in own_invites)
            for inv in invites
        ):
            return False
    except discord.Forbidden:
        pass

    try:
        await message.delete()
    except discord.Forbidden:
        pass
    log.info("Deleted invite link from %s in guild %d", message.author, guild.id)
    await _log_security_event(guild.id, "anti_invite", message.author.id, str(invites))
    return True


# ── Anti-Mass-Mention ─────────────────────────────────────────────────────────

async def check_mass_mention(message: discord.Message) -> bool:
    if not config.SECURITY_ANTI_MASS_MENTION_ENABLED:
        return False
    if not isinstance(message.author, discord.Member):
        return False
    if _is_exempt(message.author):
        return False

    mentions = len(set(message.mentions)) + len(set(message.role_mentions))
    if mentions >= config.SECURITY_MASS_MENTION_THRESHOLD:
        try:
            await message.delete()
        except discord.Forbidden:
            pass
        try:
            await message.author.timeout(
                discord.utils.utcnow() + discord.timedelta(seconds=300),
                reason=f"Anti-mass-mention: {mentions} mentions",
            )
        except discord.Forbidden:
            pass
        log.info("Mass mention from %s: %d mentions", message.author, mentions)
        await _log_security_event(
            message.guild.id, "anti_mass_mention", message.author.id,  # type: ignore
            f"{mentions} mentions",
        )
        return True
    return False


# ── Anti-Alt ──────────────────────────────────────────────────────────────────

def is_alt_account(member: discord.Member) -> bool:
    """Return True if account is younger than the minimum age threshold."""
    age_days = (discord.utils.utcnow() - member.created_at).days
    return age_days < config.SECURITY_MIN_ACCOUNT_AGE


# ── Internal helpers ──────────────────────────────────────────────────────────

async def _log_security_event(
    guild_id: int,
    event_type: str,
    user_id: Optional[int],
    details: str = "",
) -> None:
    await execute(
        "INSERT INTO security_events (guild_id, event_type, user_id, details) VALUES (?, ?, ?, ?)",
        (guild_id, event_type, user_id, details),
    )
