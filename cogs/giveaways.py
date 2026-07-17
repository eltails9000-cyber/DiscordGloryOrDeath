"""
Giveaways cog — create, end, reroll, list giveaways.
"""

from __future__ import annotations

from datetime import timezone

import discord
from discord.ext import commands

from services.giveaway_service import (
    create_giveaway,
    end_giveaway,
    get_active_giveaways,
    restore_giveaways,
)
from utils import embeds
from utils.checks import moderator_only, guild_only
from utils.helpers import parse_duration, utcnow
from utils.logger import get_logger
from utils.views import GiveawayView

log = get_logger("cogs.giveaways")


class GiveawayCog(commands.Cog, name="Giveaways"):
    def __init__(self, bot: discord.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        await restore_giveaways(self.bot)

    giveaway_group = discord.SlashCommandGroup("giveaway", "Giveaway commands")

    @giveaway_group.command(name="start", description="Start a new giveaway")
    @guild_only()
    @moderator_only()
    async def giveaway_start(
        self,
        ctx: discord.ApplicationContext,
        prize: discord.Option(str, "What to give away"),
        duration: discord.Option(str, "Duration e.g. 1h, 2d, 30m"),
        winners: discord.Option(int, "Number of winners", default=1, min_value=1, max_value=20),
        channel: discord.Option(discord.TextChannel, "Channel to post in", required=False),
        requirements: discord.Option(str, "Entry requirements", default=""),
    ):
        delta = parse_duration(duration)
        if not delta:
            return await ctx.respond(
                embed=embeds.error("Invalid Duration", "Use formats like `30m`, `1h`, `2d`."),
                ephemeral=True,
            )

        import config as cfg
        min_secs = cfg.GIVEAWAY_MIN_DURATION
        max_secs = cfg.GIVEAWAY_MAX_DURATION
        total = int(delta.total_seconds())
        if total < min_secs or total > max_secs:
            return await ctx.respond(
                embed=embeds.error(
                    "Invalid Duration",
                    f"Duration must be between {min_secs}s and {max_secs}s.",
                ),
                ephemeral=True,
            )

        ch = channel or ctx.channel
        ends_at = utcnow() + delta
        gid = await create_giveaway(ch, ctx.author, prize, winners, ends_at, requirements)

        await ctx.respond(
            embed=embeds.success("Giveaway Started", f"Giveaway **#{gid}** has started in {ch.mention}!"),
            ephemeral=True,
        )

    @giveaway_group.command(name="end", description="End a giveaway early")
    @guild_only()
    @moderator_only()
    async def giveaway_end(
        self,
        ctx: discord.ApplicationContext,
        giveaway_id: discord.Option(int, "Giveaway ID"),
    ):
        await ctx.defer(ephemeral=True)
        await end_giveaway(giveaway_id, ctx.guild)
        await ctx.respond(embed=embeds.success("Giveaway Ended", f"Giveaway #{giveaway_id} ended."), ephemeral=True)

    @giveaway_group.command(name="reroll", description="Reroll a giveaway winner")
    @guild_only()
    @moderator_only()
    async def giveaway_reroll(
        self,
        ctx: discord.ApplicationContext,
        giveaway_id: discord.Option(int, "Giveaway ID"),
    ):
        await ctx.defer(ephemeral=True)
        await end_giveaway(giveaway_id, ctx.guild, reroll=True)
        await ctx.respond(embed=embeds.success("Rerolled", f"Giveaway #{giveaway_id} has been rerolled."), ephemeral=True)

    @giveaway_group.command(name="list", description="List active giveaways")
    @guild_only()
    async def giveaway_list(self, ctx: discord.ApplicationContext):
        rows = await get_active_giveaways(ctx.guild.id)
        if not rows:
            return await ctx.respond(embed=embeds.info("No Giveaways", "No active giveaways."), ephemeral=True)

        desc = "\n".join(
            f"**#{r['id']}** — {r['prize']} | Winners: {r['winners']} | Ends: <t:{int(__import__('datetime').datetime.fromisoformat(r['ends_at']).timestamp())}:R>"
            for r in rows
        )
        embed = embeds.base(title="🎉 Active Giveaways", description=desc, color=0xFF73FA)
        await ctx.respond(embed=embed, ephemeral=True)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction) -> None:
        """Handle persistent giveaway buttons after restart."""
        cid = interaction.custom_id or ""
        if cid.startswith("giveaway:enter:"):
            try:
                gid = int(cid.split(":")[2])
            except (IndexError, ValueError):
                return
            from services.giveaway_service import toggle_entry
            await toggle_entry(interaction, gid)


def setup(bot: discord.Bot) -> None:
    bot.add_cog(GiveawayCog(bot))
