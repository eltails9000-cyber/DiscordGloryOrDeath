"""
Events cog — handles all gateway events: welcome, leave, security checks, logging.
"""

from __future__ import annotations

import discord
from discord.ext import commands

import config
import services.security_service as sec_svc
from utils import embeds
from utils.helpers import safe_send
from utils.logger import get_logger

log = get_logger("cogs.events")


class EventsCog(commands.Cog, name="Events"):
    def __init__(self, bot: discord.Bot) -> None:
        self.bot = bot

    # ── Member join ───────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        guild = member.guild

        # Anti-raid check
        await sec_svc.check_raid(member)

        # Alt detection (account too new)
        if sec_svc.is_alt_account(member):
            log.info("Possible alt account joined: %s (guild %d)", member, guild.id)
            await self._log_event(guild, "🚨 Possible Alt Account", f"{member.mention} joined with a new account.", color=embeds.ERROR)

        # Assign unverified role if configured
        if config.ROLE_UNVERIFIED:
            role = guild.get_role(config.ROLE_UNVERIFIED)
            if role:
                try:
                    await member.add_roles(role, reason="Auto: unverified on join")
                except discord.Forbidden:
                    pass

        # Welcome message
        if config.CHANNEL_WELCOME:
            ch = guild.get_channel(config.CHANNEL_WELCOME)
            if ch and isinstance(ch, discord.TextChannel):
                embed = embeds.welcome(member, guild.member_count or 0)
                await safe_send(ch, embed=embed)

        await self._log_event(
            guild,
            "📥 Member Joined",
            f"{member.mention} (`{member}`) joined.\n"
            f"Account created: <t:{int(member.created_at.timestamp())}:R>",
            color=embeds.SUCCESS,
        )

    # ── Member leave ──────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        guild = member.guild

        if config.CHANNEL_LEAVE:
            ch = guild.get_channel(config.CHANNEL_LEAVE)
            if ch and isinstance(ch, discord.TextChannel):
                embed = embeds.leave(member, guild.member_count or 0)
                await safe_send(ch, embed=embed)

        await self._log_event(
            guild,
            "📤 Member Left",
            f"{member.mention} (`{member}`) left the server.",
            color=embeds.NEUTRAL,
        )

    # ── Message events (security) ─────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or not message.guild:
            return

        # Run all security checks
        if await sec_svc.check_spam(message):
            await self._log_security(message.guild, "Anti-Spam", message.author, "Spamming — timed out")
            return
        if await sec_svc.check_scam_links(message):
            await self._log_security(message.guild, "Anti-Scam", message.author, "Posted scam link")
            return
        if await sec_svc.check_invite(message):
            await self._log_security(message.guild, "Anti-Invite", message.author, "Posted invite link")
            return
        if await sec_svc.check_mass_mention(message):
            await self._log_security(message.guild, "Anti-Mass Mention", message.author, "Mass mention")
            return

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        if message.author.bot or not message.guild:
            return
        ch_id = config.CHANNEL_LOGS
        if not ch_id:
            return
        ch = message.guild.get_channel(ch_id)
        if not ch or not isinstance(ch, discord.TextChannel):
            return
        embed = embeds.base(
            title="🗑️ Message Deleted",
            description=f"**Author:** {message.author.mention}\n**Channel:** {message.channel.mention}\n**Content:**\n{message.content[:1000] or '*no text*'}",
            color=embeds.ERROR,
        )
        await safe_send(ch, embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        if before.author.bot or not before.guild:
            return
        if before.content == after.content:
            return
        ch_id = config.CHANNEL_LOGS
        if not ch_id:
            return
        ch = before.guild.get_channel(ch_id)
        if not ch or not isinstance(ch, discord.TextChannel):
            return
        embed = embeds.base(
            title="✏️ Message Edited",
            description=f"**Author:** {before.author.mention}\n**Channel:** {before.channel.mention}",
            color=embeds.WARNING,
        )
        embed.add_field(name="Before", value=before.content[:512] or "*empty*", inline=False)
        embed.add_field(name="After", value=after.content[:512] or "*empty*", inline=False)
        await safe_send(ch, embed=embed)

    # ── Member updates ────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User) -> None:
        await self._log_event(guild, "🔨 Member Banned", f"{user.mention} (`{user}`) was banned.", color=embeds.ERROR)

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User) -> None:
        await self._log_event(guild, "🔓 Member Unbanned", f"{user.mention} (`{user}`) was unbanned.", color=embeds.SUCCESS)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        # Log role changes
        added_roles = [r for r in after.roles if r not in before.roles]
        removed_roles = [r for r in before.roles if r not in after.roles]
        if added_roles or removed_roles:
            parts = []
            if added_roles:
                parts.append("**Roles added:** " + ", ".join(r.mention for r in added_roles))
            if removed_roles:
                parts.append("**Roles removed:** " + ", ".join(r.mention for r in removed_roles))
            await self._log_event(
                before.guild,
                "👤 Member Updated",
                f"{after.mention}\n" + "\n".join(parts),
                color=embeds.INFO,
            )

    # ── Voice events ──────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        if before.channel == after.channel:
            return
        if after.channel:
            msg = f"{member.mention} joined **{after.channel.name}**"
        else:
            msg = f"{member.mention} left **{before.channel.name}**"
        await self._log_event(member.guild, "🔊 Voice Update", msg, color=embeds.NEUTRAL)

    # ── Guild events ──────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel) -> None:
        await self._log_event(channel.guild, "📁 Channel Created", f"{channel.mention} (`{channel.name}`) was created.")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel) -> None:
        await self._log_event(channel.guild, "🗑️ Channel Deleted", f"`{channel.name}` was deleted.")

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role) -> None:
        await self._log_event(role.guild, "🔵 Role Created", f"{role.mention} (`{role.name}`) was created.")

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role) -> None:
        await self._log_event(role.guild, "🔴 Role Deleted", f"`{role.name}` was deleted.")

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _log_event(
        self,
        guild: discord.Guild,
        title: str,
        description: str,
        color: int = embeds.NEUTRAL,
    ) -> None:
        ch_id = config.CHANNEL_LOGS
        if not ch_id:
            return
        ch = guild.get_channel(ch_id)
        if ch and isinstance(ch, discord.TextChannel):
            embed = embeds.base(title=title, description=description, color=color)
            await safe_send(ch, embed=embed)

    async def _log_security(
        self,
        guild: discord.Guild,
        event: str,
        user: discord.Member | discord.User,
        detail: str,
    ) -> None:
        ch_id = config.CHANNEL_SECURITY_LOGS
        if not ch_id:
            return
        ch = guild.get_channel(ch_id)
        if ch and isinstance(ch, discord.TextChannel):
            embed = embeds.base(
                title=f"🛡️ {event}",
                description=f"**User:** {user.mention} (`{user}`)\n**Action:** {detail}",
                color=embeds.WARNING,
            )
            await safe_send(ch, embed=embed)


def setup(bot: discord.Bot) -> None:
    bot.add_cog(EventsCog(bot))
