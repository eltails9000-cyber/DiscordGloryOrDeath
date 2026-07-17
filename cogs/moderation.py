"""
Moderation cog — ban, kick, mute/timeout, warn, purge, slowmode.
"""

from __future__ import annotations

import discord
from discord.ext import commands
from datetime import timezone

import config
import services.moderation_service as mod_svc
from utils import embeds, permissions as perms
from utils.checks import moderator_only, guild_only
from utils.cooldowns import slash_cooldown
from utils.helpers import parse_duration, duration_str, utcnow
from utils.logger import get_logger

log = get_logger("cogs.moderation")


class ModerationCog(commands.Cog, name="Moderation"):
    def __init__(self, bot: discord.Bot) -> None:
        self.bot = bot

    # ── /ban ──────────────────────────────────────────────────────────────────

    @discord.slash_command(name="ban", description="Ban a member from the server")
    @guild_only()
    @moderator_only()
    @slash_cooldown(1, 3)
    async def ban(
        self,
        ctx: discord.ApplicationContext,
        member: discord.Option(discord.Member, "Member to ban"),
        reason: discord.Option(str, "Reason for the ban", default="No reason provided"),
        delete_days: discord.Option(int, "Days of messages to delete (0-7)", default=0, min_value=0, max_value=7),
    ):
        if not perms.can_moderate(ctx.author, member):
            return await ctx.respond(embed=embeds.error("Cannot Ban", "You cannot ban this member."), ephemeral=True)
        if not perms.bot_can_moderate(ctx.guild, member):
            return await ctx.respond(embed=embeds.error("Cannot Ban", "I cannot ban this member."), ephemeral=True)

        await discord.utils.send_message_to_user(
            member, embeds.error("You Were Banned", f"**Server:** {ctx.guild.name}\n**Reason:** {reason}")
        ) if False else None  # noqa — replaced below
        try:
            await member.send(embed=embeds.error("You Were Banned", f"**Server:** {ctx.guild.name}\n**Reason:** {reason}"))
        except Exception:
            pass

        await member.ban(reason=f"{ctx.author}: {reason}", delete_message_days=delete_days)
        await mod_svc.log_ban(ctx.guild.id, member.id, ctx.author.id, reason)
        embed = embeds.mod_action("Ban", member, ctx.author, reason)
        await ctx.respond(embed=embed)
        await self._send_mod_log(ctx.guild, embed)
        log.info("%s banned %s | reason: %s", ctx.author, member, reason)

    # ── /unban ────────────────────────────────────────────────────────────────

    @discord.slash_command(name="unban", description="Unban a user by ID")
    @guild_only()
    @moderator_only()
    async def unban(
        self,
        ctx: discord.ApplicationContext,
        user_id: discord.Option(str, "User ID to unban"),
        reason: discord.Option(str, "Reason", default="No reason provided"),
    ):
        try:
            uid = int(user_id)
        except ValueError:
            return await ctx.respond(embed=embeds.error("Invalid ID", "Provide a valid user ID."), ephemeral=True)

        try:
            await ctx.guild.unban(discord.Object(id=uid), reason=reason)
        except discord.NotFound:
            return await ctx.respond(embed=embeds.error("Not Found", "That user is not banned."), ephemeral=True)

        embed = embeds.success("Unbanned", f"User `{uid}` has been unbanned.\n**Reason:** {reason}")
        await ctx.respond(embed=embed)

    # ── /kick ─────────────────────────────────────────────────────────────────

    @discord.slash_command(name="kick", description="Kick a member from the server")
    @guild_only()
    @moderator_only()
    @slash_cooldown(1, 3)
    async def kick(
        self,
        ctx: discord.ApplicationContext,
        member: discord.Option(discord.Member, "Member to kick"),
        reason: discord.Option(str, "Reason", default="No reason provided"),
    ):
        if not perms.can_moderate(ctx.author, member):
            return await ctx.respond(embed=embeds.error("Cannot Kick", "You cannot kick this member."), ephemeral=True)
        if not perms.bot_can_moderate(ctx.guild, member):
            return await ctx.respond(embed=embeds.error("Cannot Kick", "I cannot kick this member."), ephemeral=True)

        try:
            await member.send(embed=embeds.warning("You Were Kicked", f"**Server:** {ctx.guild.name}\n**Reason:** {reason}"))
        except Exception:
            pass

        await member.kick(reason=f"{ctx.author}: {reason}")
        embed = embeds.mod_action("Kick", member, ctx.author, reason)
        await ctx.respond(embed=embed)
        await self._send_mod_log(ctx.guild, embed)

    # ── /timeout ──────────────────────────────────────────────────────────────

    @discord.slash_command(name="timeout", description="Timeout (mute) a member")
    @guild_only()
    @moderator_only()
    async def timeout(
        self,
        ctx: discord.ApplicationContext,
        member: discord.Option(discord.Member, "Member to timeout"),
        duration: discord.Option(str, "Duration e.g. 10m, 1h, 2d", default="10m"),
        reason: discord.Option(str, "Reason", default="No reason provided"),
    ):
        delta = parse_duration(duration)
        if not delta:
            return await ctx.respond(embed=embeds.error("Invalid Duration", "Use formats like `10m`, `1h`, `2d30m`."), ephemeral=True)

        if not perms.can_moderate(ctx.author, member):
            return await ctx.respond(embed=embeds.error("Cannot Timeout", "You cannot timeout this member."), ephemeral=True)

        until = utcnow() + delta
        await member.timeout(until, reason=f"{ctx.author}: {reason}")
        await mod_svc.log_mute(ctx.guild.id, member.id, ctx.author.id, reason, until.isoformat())

        embed = embeds.mod_action(
            "Timeout",
            member,
            ctx.author,
            reason,
            extra_fields=[("Duration", duration_str(int(delta.total_seconds())), True),
                          ("Expires", f"<t:{int(until.timestamp())}:R>", True)],
        )
        await ctx.respond(embed=embed)
        await self._send_mod_log(ctx.guild, embed)

    # ── /untimeout ────────────────────────────────────────────────────────────

    @discord.slash_command(name="untimeout", description="Remove a timeout from a member")
    @guild_only()
    @moderator_only()
    async def untimeout(
        self,
        ctx: discord.ApplicationContext,
        member: discord.Option(discord.Member, "Member to untimeout"),
        reason: discord.Option(str, "Reason", default="No reason provided"),
    ):
        await member.remove_timeout(reason=f"{ctx.author}: {reason}")
        embed = embeds.success("Timeout Removed", f"{member.mention}'s timeout has been removed.")
        await ctx.respond(embed=embed)

    # ── /warn ─────────────────────────────────────────────────────────────────

    @discord.slash_command(name="warn", description="Warn a member")
    @guild_only()
    @moderator_only()
    async def warn(
        self,
        ctx: discord.ApplicationContext,
        member: discord.Option(discord.Member, "Member to warn"),
        reason: discord.Option(str, "Reason for warning"),
    ):
        warn_id = await mod_svc.add_warning(ctx.guild.id, member.id, ctx.author.id, reason)
        warn_count = await mod_svc.count_warnings(ctx.guild.id, member.id)

        try:
            await member.send(embed=embeds.warning(
                "You Received a Warning",
                f"**Server:** {ctx.guild.name}\n**Reason:** {reason}\n**Total warnings:** {warn_count}",
            ))
        except Exception:
            pass

        embed = embeds.mod_action(
            f"Warning #{warn_id}",
            member,
            ctx.author,
            reason,
            extra_fields=[("Total Warnings", str(warn_count), True)],
        )
        await ctx.respond(embed=embed)

        # Auto-escalation
        if warn_count >= config.MOD_WARN_THRESHOLD_BAN:
            await member.ban(reason="Auto-ban: warning threshold exceeded")
        elif warn_count >= config.MOD_WARN_THRESHOLD_KICK:
            await member.kick(reason="Auto-kick: warning threshold exceeded")
        elif warn_count >= config.MOD_WARN_THRESHOLD_MUTE:
            from datetime import timedelta
            await member.timeout(
                utcnow() + timedelta(seconds=config.MOD_DEFAULT_MUTE_DURATION),
                reason="Auto-timeout: warning threshold exceeded",
            )

        await self._send_mod_log(ctx.guild, embed)

    # ── /warnings ─────────────────────────────────────────────────────────────

    @discord.slash_command(name="warnings", description="View warnings for a member")
    @guild_only()
    @moderator_only()
    async def warnings(
        self,
        ctx: discord.ApplicationContext,
        member: discord.Option(discord.Member, "Member to check"),
    ):
        warns = await mod_svc.get_warnings(ctx.guild.id, member.id)
        if not warns:
            return await ctx.respond(embed=embeds.info("No Warnings", f"{member.mention} has no warnings."))

        desc = "\n".join(
            f"**#{w['id']}** — {w['reason']} *(by <@{w['moderator_id']}> on {w['created_at'][:10]})*"
            for w in warns[:20]
        )
        embed = embeds.base(
            title=f"⚠️ Warnings for {member}",
            description=desc,
            color=embeds.WARNING,
            footer=f"Total: {len(warns)}",
        )
        await ctx.respond(embed=embed)

    # ── /clearwarnings ────────────────────────────────────────────────────────

    @discord.slash_command(name="clearwarnings", description="Clear all warnings for a member")
    @guild_only()
    @moderator_only()
    async def clearwarnings(
        self,
        ctx: discord.ApplicationContext,
        member: discord.Option(discord.Member, "Member to clear"),
    ):
        count = await mod_svc.clear_warnings(ctx.guild.id, member.id)
        await ctx.respond(embed=embeds.success("Warnings Cleared", f"Cleared **{count}** warning(s) for {member.mention}."))

    # ── /purge ────────────────────────────────────────────────────────────────

    @discord.slash_command(name="purge", description="Delete multiple messages")
    @guild_only()
    @moderator_only()
    async def purge(
        self,
        ctx: discord.ApplicationContext,
        amount: discord.Option(int, "Number of messages to delete (1-100)", min_value=1, max_value=100),
        member: discord.Option(discord.Member, "Only delete messages from this member", required=False),
    ):
        await ctx.defer(ephemeral=True)
        check = (lambda m: m.author == member) if member else None
        deleted = await ctx.channel.purge(limit=amount, check=check)
        await ctx.respond(
            embed=embeds.success("Purge Complete", f"Deleted **{len(deleted)}** message(s)."),
            ephemeral=True,
        )

    # ── /slowmode ─────────────────────────────────────────────────────────────

    @discord.slash_command(name="slowmode", description="Set channel slowmode")
    @guild_only()
    @moderator_only()
    async def slowmode(
        self,
        ctx: discord.ApplicationContext,
        seconds: discord.Option(int, "Slowmode seconds (0 to disable)", min_value=0, max_value=21600),
    ):
        await ctx.channel.edit(slowmode_delay=seconds)
        if seconds == 0:
            await ctx.respond(embed=embeds.success("Slowmode Disabled", "Slowmode has been turned off."))
        else:
            await ctx.respond(embed=embeds.success("Slowmode Set", f"Slowmode set to **{seconds}s**."))

    # ── /lock / /unlock ───────────────────────────────────────────────────────

    @discord.slash_command(name="lock", description="Lock a channel")
    @guild_only()
    @moderator_only()
    async def lock(
        self,
        ctx: discord.ApplicationContext,
        channel: discord.Option(discord.TextChannel, "Channel to lock", required=False),
        reason: discord.Option(str, "Reason", default="Locked by moderator"),
    ):
        ch = channel or ctx.channel
        await ch.set_permissions(ctx.guild.default_role, send_messages=False, reason=reason)
        await ctx.respond(embed=embeds.success("Channel Locked", f"{ch.mention} has been locked.\n**Reason:** {reason}"))

    @discord.slash_command(name="unlock", description="Unlock a channel")
    @guild_only()
    @moderator_only()
    async def unlock(
        self,
        ctx: discord.ApplicationContext,
        channel: discord.Option(discord.TextChannel, "Channel to unlock", required=False),
    ):
        ch = channel or ctx.channel
        await ch.set_permissions(ctx.guild.default_role, send_messages=None)
        await ctx.respond(embed=embeds.success("Channel Unlocked", f"{ch.mention} has been unlocked."))

    # ── /userinfo ─────────────────────────────────────────────────────────────

    @discord.slash_command(name="userinfo", description="Show info about a member")
    @guild_only()
    async def userinfo(
        self,
        ctx: discord.ApplicationContext,
        member: discord.Option(discord.Member, "Member to inspect", required=False),
    ):
        member = member or ctx.author
        warn_count = await mod_svc.count_warnings(ctx.guild.id, member.id)
        joined = f"<t:{int(member.joined_at.timestamp())}:R>" if member.joined_at else "Unknown"
        created = f"<t:{int(member.created_at.timestamp())}:R>"
        roles = [r.mention for r in member.roles[1:]][:10]

        embed = embeds.base(
            title=f"👤 {member}",
            color=member.color.value or embeds.INFO,
            thumbnail=str(member.display_avatar.url),
            footer=f"ID: {member.id}",
        )
        embed.add_field(name="Joined", value=joined, inline=True)
        embed.add_field(name="Created", value=created, inline=True)
        embed.add_field(name="Warnings", value=str(warn_count), inline=True)
        embed.add_field(name="Roles", value=" ".join(roles) or "None", inline=False)
        await ctx.respond(embed=embed)

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _send_mod_log(self, guild: discord.Guild, embed: discord.Embed) -> None:
        channel_id = config.CHANNEL_MOD_LOGS
        if not channel_id:
            return
        channel = guild.get_channel(channel_id)
        if channel and isinstance(channel, discord.TextChannel):
            try:
                await channel.send(embed=embed)
            except discord.Forbidden:
                pass


def setup(bot: discord.Bot) -> None:
    bot.add_cog(ModerationCog(bot))
