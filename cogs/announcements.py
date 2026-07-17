"""
Announcements cog — announcements, polls, suggestions, scheduled messages.
"""

from __future__ import annotations

import discord
from discord.ext import commands

import config
from services.announcement_service import (
    schedule_announcement,
    create_poll,
    restore_announcements,
)
from utils import embeds
from utils.checks import moderator_only, guild_only
from utils.helpers import parse_duration, resolve_color, utcnow
from utils.logger import get_logger
from utils.views import SuggestionModal

log = get_logger("cogs.announcements")


class AnnouncementsCog(commands.Cog, name="Announcements"):
    def __init__(self, bot: discord.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        await restore_announcements(self.bot)

    # ── /announce ─────────────────────────────────────────────────────────────

    @discord.slash_command(name="announce", description="Send an announcement embed")
    @guild_only()
    @moderator_only()
    async def announce(
        self,
        ctx: discord.ApplicationContext,
        content: discord.Option(str, "Announcement content"),
        channel: discord.Option(discord.TextChannel, "Target channel", required=False),
        title: discord.Option(str, "Embed title", default="📢 Announcement"),
        color: discord.Option(str, "Hex color e.g. #FF0000", default="#5865F2"),
        ping_role: discord.Option(discord.Role, "Role to ping", required=False),
    ):
        ch = channel or ctx.channel
        col = resolve_color(color)
        embed = embeds.base(title=title, description=content, color=col, author=ctx.author)
        msg_content = ping_role.mention if ping_role else None
        await ch.send(content=msg_content, embed=embed)
        await ctx.respond(embed=embeds.success("Announced", f"Announcement sent to {ch.mention}."), ephemeral=True)

    # ── /scheduleannounce ─────────────────────────────────────────────────────

    @discord.slash_command(name="scheduleannounce", description="Schedule an announcement for later")
    @guild_only()
    @moderator_only()
    async def schedule_announce(
        self,
        ctx: discord.ApplicationContext,
        content: discord.Option(str, "Announcement content"),
        delay: discord.Option(str, "Delay e.g. 2h, 1d30m"),
        channel: discord.Option(discord.TextChannel, "Target channel", required=False),
        title: discord.Option(str, "Title", default="📢 Announcement"),
        color: discord.Option(str, "Hex color", default="#5865F2"),
    ):
        delta = parse_duration(delay)
        if not delta:
            return await ctx.respond(
                embed=embeds.error("Invalid Delay", "Use formats like `2h`, `1d`, `30m`."),
                ephemeral=True,
            )

        ch = channel or ctx.channel
        scheduled_at = utcnow() + delta
        ann_id = await schedule_announcement(
            ctx.guild.id,
            ch.id,
            ctx.author.id,
            content,
            scheduled_at,
            title=title,
            color=resolve_color(color),
        )

        await ctx.respond(
            embed=embeds.success(
                "Announcement Scheduled",
                f"Announcement **#{ann_id}** scheduled for <t:{int(scheduled_at.timestamp())}:R> in {ch.mention}.",
            ),
            ephemeral=True,
        )

    # ── /poll ─────────────────────────────────────────────────────────────────

    @discord.slash_command(name="poll", description="Create a poll")
    @guild_only()
    @moderator_only()
    async def poll(
        self,
        ctx: discord.ApplicationContext,
        question: discord.Option(str, "Poll question"),
        options: discord.Option(str, "Options separated by | e.g. Option A | Option B | Option C"),
        duration: discord.Option(str, "Duration e.g. 1h, 2d (leave blank for no end)", required=False),
        channel: discord.Option(discord.TextChannel, "Channel to post in", required=False),
    ):
        opt_list = [o.strip() for o in options.split("|") if o.strip()]
        if len(opt_list) < 2:
            return await ctx.respond(
                embed=embeds.error("Too Few Options", "Provide at least 2 options separated by `|`."),
                ephemeral=True,
            )
        if len(opt_list) > 10:
            return await ctx.respond(
                embed=embeds.error("Too Many Options", "Maximum 10 options allowed."),
                ephemeral=True,
            )

        ch = channel or ctx.channel
        ends_at = (utcnow() + parse_duration(duration)) if duration and parse_duration(duration) else None
        poll_id = await create_poll(ch, ctx.author, question, opt_list, ends_at)

        await ctx.respond(
            embed=embeds.success("Poll Created", f"Poll **#{poll_id}** posted in {ch.mention}."),
            ephemeral=True,
        )

    # ── /suggest ──────────────────────────────────────────────────────────────

    @discord.slash_command(name="suggest", description="Submit a suggestion")
    @guild_only()
    async def suggest(self, ctx: discord.ApplicationContext):
        modal = SuggestionModal()
        await ctx.send_modal(modal)

    # ── /reviewsuggestion ─────────────────────────────────────────────────────

    @discord.slash_command(name="reviewsuggestion", description="Approve or deny a suggestion")
    @guild_only()
    @moderator_only()
    async def review_suggestion(
        self,
        ctx: discord.ApplicationContext,
        suggestion_id: discord.Option(int, "Suggestion ID"),
        status: discord.Option(str, "Status", choices=["approved", "denied", "pending"]),
        note: discord.Option(str, "Review note", default=""),
    ):
        from services.database_service import execute, fetchone
        row = await fetchone(
            "SELECT * FROM suggestions WHERE id = ? AND guild_id = ?",
            (suggestion_id, ctx.guild.id),
        )
        if not row:
            return await ctx.respond(embed=embeds.error("Not Found", "Suggestion not found."), ephemeral=True)

        await execute(
            "UPDATE suggestions SET status = ?, reviewed_by = ?, review_note = ? WHERE id = ?",
            (status, ctx.author.id, note, suggestion_id),
        )

        # Update the message embed
        if row["message_id"] and config.CHANNEL_SUGGESTIONS:
            ch = ctx.guild.get_channel(config.CHANNEL_SUGGESTIONS)
            if ch and isinstance(ch, discord.TextChannel):
                try:
                    msg = await ch.fetch_message(row["message_id"])
                    for embed in msg.embeds:
                        embed.color = (
                            embeds.SUCCESS if status == "approved" else
                            embeds.ERROR if status == "denied" else
                            embeds.WARNING
                        )
                        embed.set_field_at(
                            0,
                            name=f"Status: {status.title()}",
                            value=note or "No note provided",
                            inline=False,
                        ) if embed.fields else embed.add_field(
                            name=f"Status: {status.title()}",
                            value=note or "No note provided",
                        )
                        await msg.edit(embed=embed)
                        break
                except Exception:
                    pass

        await ctx.respond(
            embed=embeds.success("Suggestion Reviewed", f"Suggestion #{suggestion_id} marked as **{status}**."),
            ephemeral=True,
        )


def setup(bot: discord.Bot) -> None:
    bot.add_cog(AnnouncementsCog(bot))
