"""
Security cog — slash commands for security management and manual overrides.
The actual detection runs in events.py which calls the security service.
"""

from __future__ import annotations

import discord
from discord.ext import commands

import config
import services.security_service as sec_svc
from utils import embeds
from utils.checks import admin_only, guild_only
from utils.logger import get_logger

log = get_logger("cogs.security")


class SecurityCog(commands.Cog, name="Security"):
    def __init__(self, bot: discord.Bot) -> None:
        self.bot = bot

    # ── /lockdown ─────────────────────────────────────────────────────────────

    @discord.slash_command(name="lockdown", description="Manually activate server lockdown")
    @guild_only()
    @admin_only()
    async def lockdown(
        self,
        ctx: discord.ApplicationContext,
        reason: discord.Option(str, "Reason for lockdown", default="Manual lockdown"),
    ):
        if sec_svc.is_locked_down(ctx.guild.id):
            return await ctx.respond(embed=embeds.warning("Already Locked", "Server is already in lockdown."), ephemeral=True)

        await ctx.defer()
        await sec_svc._activate_lockdown(ctx.guild)
        embed = embeds.error("🔒 Server Lockdown", f"All channels have been locked.\n**Reason:** {reason}")
        await ctx.respond(embed=embed)
        await self._send_security_log(ctx.guild, embed)

    # ── /unlockdown ───────────────────────────────────────────────────────────

    @discord.slash_command(name="unlockdown", description="Deactivate server lockdown")
    @guild_only()
    @admin_only()
    async def unlockdown(self, ctx: discord.ApplicationContext):
        if not sec_svc.is_locked_down(ctx.guild.id):
            return await ctx.respond(embed=embeds.warning("Not Locked", "Server is not in lockdown."), ephemeral=True)

        await ctx.defer()
        await sec_svc.deactivate_lockdown(ctx.guild)
        embed = embeds.success("🔓 Lockdown Lifted", "All channels have been unlocked.")
        await ctx.respond(embed=embed)
        await self._send_security_log(ctx.guild, embed)

    # ── /security status ──────────────────────────────────────────────────────

    @discord.slash_command(name="security", description="View security module status")
    @guild_only()
    @admin_only()
    async def security_status(self, ctx: discord.ApplicationContext):
        locked = sec_svc.is_locked_down(ctx.guild.id)
        embed = embeds.base(title="🛡️ Security Status", color=embeds.INFO)
        embed.add_field(name="Anti-Spam", value=_toggle(config.SECURITY_ANTI_SPAM_ENABLED), inline=True)
        embed.add_field(name="Anti-Raid", value=_toggle(config.SECURITY_ANTI_RAID_ENABLED), inline=True)
        embed.add_field(name="Anti-Scam", value=_toggle(config.SECURITY_ANTI_SCAM_ENABLED), inline=True)
        embed.add_field(name="Anti-Invite", value=_toggle(config.SECURITY_ANTI_INVITE_ENABLED), inline=True)
        embed.add_field(name="Anti-Mass Mention", value=_toggle(config.SECURITY_ANTI_MASS_MENTION_ENABLED), inline=True)
        embed.add_field(name="Lockdown Active", value="🔒 Yes" if locked else "🔓 No", inline=True)
        embed.add_field(name="Spam Threshold", value=f"{config.SECURITY_SPAM_THRESHOLD} msgs / {config.SECURITY_SPAM_INTERVAL}s", inline=False)
        embed.add_field(name="Raid Threshold", value=f"{config.SECURITY_RAID_JOIN_THRESHOLD} joins / {config.SECURITY_RAID_INTERVAL}s", inline=False)
        embed.add_field(name="Min Account Age", value=f"{config.SECURITY_MIN_ACCOUNT_AGE} days", inline=True)
        await ctx.respond(embed=embed)

    # ── /reload-scam-list ─────────────────────────────────────────────────────

    @discord.slash_command(name="reloadscamlist", description="Reload the scam domain list")
    @guild_only()
    @admin_only()
    async def reload_scam_list(self, ctx: discord.ApplicationContext):
        await ctx.defer(ephemeral=True)
        await sec_svc.load_scam_domains()
        await ctx.respond(
            embed=embeds.success("Scam List Reloaded", f"Loaded {len(sec_svc._scam_domains)} scam domains."),
            ephemeral=True,
        )

    async def _send_security_log(self, guild: discord.Guild, embed: discord.Embed) -> None:
        ch_id = config.CHANNEL_SECURITY_LOGS
        if not ch_id:
            return
        ch = guild.get_channel(ch_id)
        if ch and isinstance(ch, discord.TextChannel):
            try:
                await ch.send(embed=embed)
            except discord.Forbidden:
                pass


def _toggle(val: bool) -> str:
    return "✅ Enabled" if val else "❌ Disabled"


def setup(bot: discord.Bot) -> None:
    bot.add_cog(SecurityCog(bot))
