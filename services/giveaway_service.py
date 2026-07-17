"""
Giveaway service — create, enter, end, and reroll giveaways.
"""

from __future__ import annotations

import asyncio
import json
import random
from datetime import datetime, timezone
from typing import Optional

import discord

import config
from services.database_service import execute, fetchone, fetchall
from utils.embeds import giveaway as giveaway_embed
from utils.helpers import utcnow
from utils.logger import get_logger

log = get_logger("giveaways")


async def create_giveaway(
    channel: discord.TextChannel,
    host: discord.Member,
    prize: str,
    winners: int,
    ends_at: datetime,
    requirements: str = "",
) -> int:
    """Create a giveaway, post its message, return DB id."""
    embed = giveaway_embed(prize, host, winners, ends_at, requirements)

    from utils.views import GiveawayView

    # Temporary placeholder — we update message_id after send
    giveaway_id = await execute(
        "INSERT INTO giveaways (guild_id, channel_id, host_id, prize, winners, ends_at, requirements) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            channel.guild.id,
            channel.id,
            host.id,
            prize,
            winners,
            ends_at.isoformat(),
            requirements,
        ),
    )

    view = GiveawayView(giveaway_id)
    msg = await channel.send(embed=embed, view=view)

    # Store message_id
    await execute(
        "UPDATE giveaways SET message_id = ? WHERE id = ?",
        (msg.id, giveaway_id),
    )

    # Schedule end
    delay = (ends_at - utcnow()).total_seconds()
    if delay > 0:
        asyncio.create_task(_schedule_end(giveaway_id, delay, channel.guild))

    log.info("Giveaway #%d created in guild %d", giveaway_id, channel.guild.id)
    return giveaway_id


async def toggle_entry(interaction: discord.Interaction, giveaway_id: int) -> None:
    """Toggle a user's entry in a giveaway."""
    user_id = interaction.user.id

    row = await fetchone("SELECT * FROM giveaways WHERE id = ?", (giveaway_id,))
    if not row or row["ended"]:
        await interaction.response.send_message("❌ This giveaway has ended.", ephemeral=True)
        return

    existing = await fetchone(
        "SELECT * FROM giveaway_entries WHERE giveaway_id = ? AND user_id = ?",
        (giveaway_id, user_id),
    )

    if existing:
        await execute(
            "DELETE FROM giveaway_entries WHERE giveaway_id = ? AND user_id = ?",
            (giveaway_id, user_id),
        )
        await interaction.response.send_message("✅ You have left the giveaway.", ephemeral=True)
    else:
        await execute(
            "INSERT INTO giveaway_entries (giveaway_id, user_id) VALUES (?, ?)",
            (giveaway_id, user_id),
        )
        await interaction.response.send_message(
            f"🎉 You have entered the **{row['prize']}** giveaway!", ephemeral=True
        )


async def end_giveaway(giveaway_id: int, guild: discord.Guild, *, reroll: bool = False) -> None:
    row = await fetchone("SELECT * FROM giveaways WHERE id = ?", (giveaway_id,))
    if not row:
        return

    entries = await fetchall(
        "SELECT user_id FROM giveaway_entries WHERE giveaway_id = ?",
        (giveaway_id,),
    )
    user_ids = [e["user_id"] for e in entries]

    channel = guild.get_channel(row["channel_id"])
    num_winners = row["winners"]

    # Pick winners
    winners: list[discord.Member] = []
    pool = user_ids.copy()
    random.shuffle(pool)
    for uid in pool:
        member = guild.get_member(uid)
        if member:
            winners.append(member)
        if len(winners) >= num_winners:
            break

    # Update embed
    if channel and isinstance(channel, discord.TextChannel):
        try:
            msg = await channel.fetch_message(row["message_id"])
        except (discord.NotFound, discord.HTTPException):
            msg = None

        if winners:
            winner_str = ", ".join(w.mention for w in winners)
            embed = discord.Embed(
                title="🎉 Giveaway Ended!",
                description=f"**Prize:** {row['prize']}\n**Winners:** {winner_str}",
                color=0xFF73FA,
            )
            embed.set_footer(text=f"{'Rerolled' if reroll else 'Ended'}")
        else:
            embed = discord.Embed(
                title="🎉 Giveaway Ended",
                description=f"**Prize:** {row['prize']}\n\nNo valid entries — no winners.",
                color=0xED4245,
            )

        if msg:
            await msg.edit(embed=embed, view=None)

        if winners:
            winner_str = ", ".join(w.mention for w in winners)
            await channel.send(
                f"🎊 Congratulations {winner_str}! You won **{row['prize']}**!\n"
                f"Use `/giveaway reroll {giveaway_id}` to reroll if a winner doesn't claim."
            )
        else:
            await channel.send("😔 No valid entries for the giveaway.")

    await execute("UPDATE giveaways SET ended = 1 WHERE id = ?", (giveaway_id,))
    log.info("Giveaway #%d ended. Winners: %s", giveaway_id, [str(w) for w in winners])


async def _schedule_end(giveaway_id: int, delay: float, guild: discord.Guild) -> None:
    await asyncio.sleep(delay)
    await end_giveaway(giveaway_id, guild)


async def get_active_giveaways(guild_id: int) -> list:
    return await fetchall(
        "SELECT * FROM giveaways WHERE guild_id = ? AND ended = 0 ORDER BY ends_at ASC",
        (guild_id,),
    )


async def restore_giveaways(bot: discord.Bot) -> None:
    """Called on bot ready to reschedule pending giveaways."""
    rows = await fetchall("SELECT * FROM giveaways WHERE ended = 0")

    now = utcnow()
    for row in rows:
        guild = bot.get_guild(row["guild_id"])
        if not guild:
            continue
        ends_at = datetime.fromisoformat(row["ends_at"]).replace(tzinfo=timezone.utc)
        delay = (ends_at - now).total_seconds()
        if delay <= 0:
            asyncio.create_task(end_giveaway(row["id"], guild))
        else:
            asyncio.create_task(_schedule_end(row["id"], delay, guild))
    log.info("Restored %d active giveaways", len(rows))
