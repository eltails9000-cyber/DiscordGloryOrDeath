"""
Embed builder utilities for consistent, branded Discord embeds.
"""

from __future__ import annotations

import discord
from datetime import datetime, timezone
from typing import Optional

import config


# ── Colour palette ────────────────────────────────────────────────────────────
SUCCESS = 0x57F287   # green
ERROR   = 0xED4245   # red
WARNING = 0xFEE75C   # yellow
INFO    = 0x5865F2   # blurple
MOD     = 0xEB459E   # pink
NEUTRAL = 0x2B2D31   # dark


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def base(
    title: str = "",
    description: str = "",
    color: int = INFO,
    *,
    author: Optional[discord.Member | discord.User] = None,
    footer: str = "",
    thumbnail: str = "",
    image: str = "",
    timestamp: bool = True,
) -> discord.Embed:
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=_now() if timestamp else None,
    )
    if author:
        embed.set_author(name=str(author), icon_url=author.display_avatar.url)
    if footer:
        embed.set_footer(text=footer)
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    if image:
        embed.set_image(url=image)
    return embed


def success(title: str, description: str = "", **kwargs) -> discord.Embed:
    return base(title=f"✅ {title}", description=description, color=SUCCESS, **kwargs)


def error(title: str, description: str = "", **kwargs) -> discord.Embed:
    return base(title=f"❌ {title}", description=description, color=ERROR, **kwargs)


def warning(title: str, description: str = "", **kwargs) -> discord.Embed:
    return base(title=f"⚠️ {title}", description=description, color=WARNING, **kwargs)


def info(title: str, description: str = "", **kwargs) -> discord.Embed:
    return base(title=f"ℹ️ {title}", description=description, color=INFO, **kwargs)


def mod_action(
    action: str,
    target: discord.Member | discord.User,
    moderator: discord.Member | discord.User,
    reason: str = "No reason provided",
    extra_fields: list[tuple[str, str, bool]] | None = None,
) -> discord.Embed:
    embed = base(
        title=f"🔨 {action}",
        color=MOD,
        footer=f"ID: {target.id}",
    )
    embed.add_field(name="User", value=f"{target.mention} (`{target}`)", inline=True)
    embed.add_field(name="Moderator", value=f"{moderator.mention} (`{moderator}`)", inline=True)
    embed.add_field(name="Reason", value=reason, inline=False)
    if extra_fields:
        for name, value, inline in extra_fields:
            embed.add_field(name=name, value=value, inline=inline)
    embed.set_thumbnail(url=target.display_avatar.url)
    return embed


def giveaway(
    prize: str,
    host: discord.Member | discord.User,
    winners: int,
    ends_at: datetime,
    requirements: str = "",
) -> discord.Embed:
    embed = base(
        title="🎉 Giveaway!",
        description=f"**Prize:** {prize}",
        color=0xFF73FA,
    )
    embed.add_field(name="Winners", value=str(winners), inline=True)
    embed.add_field(name="Hosted by", value=host.mention, inline=True)
    embed.add_field(
        name="Ends at",
        value=f"<t:{int(ends_at.timestamp())}:R>",
        inline=True,
    )
    if requirements:
        embed.add_field(name="Requirements", value=requirements, inline=False)
    embed.set_footer(text="Click the button below to enter!")
    return embed


def verification_embed() -> discord.Embed:
    embed = base(
        title="🔐 Server Verification",
        description=(
            "Welcome! To gain access to the server, you must complete verification.\n\n"
            "Click the **Verify** button below to begin.\n"
            "You will be given a captcha to solve."
        ),
        color=0x5865F2,
    )
    return embed


def welcome(member: discord.Member, count: int) -> discord.Embed:
    msg = config.WELCOME_MESSAGE.format(
        mention=member.mention,
        name=str(member),
        count=count,
    )
    embed = base(
        title="👋 Welcome!",
        description=msg,
        color=config.WELCOME_COLOR,
        thumbnail=str(member.display_avatar.url),
    )
    embed.set_footer(text=f"Member #{count}")
    return embed


def leave(member: discord.Member | discord.User, count: int) -> discord.Embed:
    msg = config.LEAVE_MESSAGE.format(
        mention=str(member),
        name=str(member),
        count=count,
    )
    embed = base(
        title="👋 Goodbye!",
        description=msg,
        color=config.LEAVE_COLOR,
    )
    return embed
