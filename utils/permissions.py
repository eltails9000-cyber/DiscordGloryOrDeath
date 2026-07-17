"""
Permission helpers — centralised role/permission checks.
"""

from __future__ import annotations

import discord
from typing import Optional

import config
from utils.logger import get_logger

log = get_logger("permissions")


def is_owner(user: discord.Member | discord.User) -> bool:
    return user.id in config.OWNER_IDS


def has_role(member: discord.Member, role_id: Optional[int]) -> bool:
    if role_id is None:
        return False
    return any(r.id == role_id for r in member.roles)


def is_admin(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    return has_role(member, config.ROLE_ADMIN)


def is_moderator(member: discord.Member) -> bool:
    if is_admin(member):
        return True
    return has_role(member, config.ROLE_MOD)


def can_moderate(moderator: discord.Member, target: discord.Member) -> bool:
    """Return True if moderator can action target (higher hierarchy)."""
    if moderator == target:
        return False
    if target.guild.owner_id == target.id:
        return False
    return moderator.top_role > target.top_role


def bot_can_moderate(guild: discord.Guild, target: discord.Member) -> bool:
    bot_member = guild.me
    if not bot_member:
        return False
    return bot_member.top_role > target.top_role
