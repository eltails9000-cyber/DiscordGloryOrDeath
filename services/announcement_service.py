"""
Announcement service — scheduled announcements, polls, suggestions.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Optional

import discord

from services.database_service import execute, fetchone, fetchall
from utils.helpers import utcnow
from utils.logger import get_logger

log = get_logger("announcements")


# ── Announcements ─────────────────────────────────────────────────────────────

async def schedule_announcement(
    guild_id: int,
    channel_id: int,
    author_id: int,
    content: str,
    scheduled_at: datetime,
    title: str = "",
    color: int = 0x5865F2,
) -> int:
    ann_id = await execute(
        "INSERT INTO scheduled_announcements (guild_id, channel_id, author_id, title, content, color, scheduled_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (guild_id, channel_id, author_id, title, content, color, scheduled_at.isoformat()),
    )
    delay = (scheduled_at - utcnow()).total_seconds()
    if delay > 0:
        asyncio.create_task(_send_scheduled(ann_id, delay))
    else:
        asyncio.create_task(_send_scheduled(ann_id, 0))
    return ann_id


async def _send_scheduled(ann_id: int, delay: float) -> None:
    if delay > 0:
        await asyncio.sleep(delay)
    row = await fetchone("SELECT * FROM scheduled_announcements WHERE id = ? AND sent = 0", (ann_id,))
    if not row:
        return
    # We need a bot reference — import here to avoid circular issues
    import main as bot_main
    bot = bot_main.bot
    channel = bot.get_channel(row["channel_id"])
    if not channel or not isinstance(channel, discord.TextChannel):
        return
    embed = discord.Embed(
        title=row["title"] or "📢 Announcement",
        description=row["content"],
        color=row["color"],
        timestamp=utcnow(),
    )
    await channel.send(embed=embed)
    await execute("UPDATE scheduled_announcements SET sent = 1 WHERE id = ?", (ann_id,))
    log.info("Sent scheduled announcement #%d", ann_id)


async def restore_announcements(bot: discord.Bot) -> None:
    rows = await fetchall(
        "SELECT * FROM scheduled_announcements WHERE sent = 0",
    )
    now = utcnow()
    for row in rows:
        scheduled_at = datetime.fromisoformat(row["scheduled_at"]).replace(tzinfo=timezone.utc)
        delay = max(0.0, (scheduled_at - now).total_seconds())
        asyncio.create_task(_send_scheduled(row["id"], delay))
    log.info("Restored %d scheduled announcements", len(rows))


# ── Polls ─────────────────────────────────────────────────────────────────────

async def create_poll(
    channel: discord.TextChannel,
    author: discord.Member,
    question: str,
    options: list[str],
    ends_at: Optional[datetime] = None,
) -> int:
    options_json = json.dumps(options)
    poll_id = await execute(
        "INSERT INTO polls (guild_id, channel_id, author_id, question, options, ends_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            channel.guild.id,
            channel.id,
            author.id,
            question,
            options_json,
            ends_at.isoformat() if ends_at else None,
        ),
    )

    from utils.views import PollView
    embed = _poll_embed(question, options, {})
    view = PollView(poll_id, options)
    msg = await channel.send(embed=embed, view=view)
    await execute("UPDATE polls SET message_id = ? WHERE id = ?", (msg.id, poll_id))

    if ends_at:
        delay = (ends_at - utcnow()).total_seconds()
        if delay > 0:
            asyncio.create_task(_end_poll_after(poll_id, delay))

    return poll_id


def _poll_embed(question: str, options: list[str], votes: dict[int, int]) -> discord.Embed:
    total = sum(votes.values()) or 1
    desc_lines = []
    for i, opt in enumerate(options):
        count = votes.get(i, 0)
        bar_len = int((count / total) * 20)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        desc_lines.append(f"**{opt}**\n`{bar}` {count} votes")
    embed = discord.Embed(
        title=f"📊 {question}",
        description="\n\n".join(desc_lines),
        color=0x5865F2,
        timestamp=utcnow(),
    )
    embed.set_footer(text=f"Total votes: {sum(votes.values())}")
    return embed


async def record_vote(interaction: discord.Interaction, poll_id: int, option_idx: int) -> None:
    row = await fetchone("SELECT * FROM polls WHERE id = ? AND ended = 0", (poll_id,))
    if not row:
        await interaction.response.send_message("This poll has ended.", ephemeral=True)
        return

    # Upsert vote (change vote if already voted)
    await execute(
        "INSERT INTO poll_votes (poll_id, user_id, option_idx) VALUES (?, ?, ?) "
        "ON CONFLICT(poll_id, user_id) DO UPDATE SET option_idx = excluded.option_idx",
        (poll_id, interaction.user.id, option_idx),
    )

    # Refresh embed
    vote_rows = await fetchall("SELECT option_idx, COUNT(*) as cnt FROM poll_votes WHERE poll_id = ? GROUP BY option_idx", (poll_id,))
    votes = {r["option_idx"]: r["cnt"] for r in vote_rows}
    options = json.loads(row["options"])
    embed = _poll_embed(row["question"], options, votes)

    if interaction.message:
        await interaction.message.edit(embed=embed)
    await interaction.response.send_message("✅ Vote recorded!", ephemeral=True)


async def _end_poll_after(poll_id: int, delay: float) -> None:
    await asyncio.sleep(delay)
    await execute("UPDATE polls SET ended = 1 WHERE id = ?", (poll_id,))


# ── Suggestions ────────────────────────────────────────────────────────────────

async def submit_suggestion(interaction: discord.Interaction, content: str) -> None:
    guild = interaction.guild
    member = interaction.user
    if not guild or not isinstance(member, discord.Member):
        await interaction.response.send_message("Server only.", ephemeral=True)
        return

    import config
    channel = guild.get_channel(config.CHANNEL_SUGGESTIONS) if config.CHANNEL_SUGGESTIONS else None
    if not channel or not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message("❌ No suggestion channel configured.", ephemeral=True)
        return

    suggestion_id = await execute(
        "INSERT INTO suggestions (guild_id, author_id, content) VALUES (?, ?, ?)",
        (guild.id, member.id, content),
    )

    embed = discord.Embed(
        title=f"💡 Suggestion #{suggestion_id}",
        description=content,
        color=0x5865F2,
        timestamp=utcnow(),
    )
    embed.set_author(name=str(member), icon_url=member.display_avatar.url)
    embed.set_footer(text=f"User ID: {member.id}")

    msg = await channel.send(embed=embed)
    await msg.add_reaction("👍")
    await msg.add_reaction("👎")
    await execute("UPDATE suggestions SET message_id = ? WHERE id = ?", (msg.id, suggestion_id))

    await interaction.response.send_message(
        f"✅ Your suggestion has been submitted (#{suggestion_id})!", ephemeral=True
    )
