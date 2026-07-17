"""
Config cog — server-side configuration commands (sets channel/role IDs in DB).
In-memory config is loaded from env; this cog persists overrides to the DB for
guild-specific settings.
"""

from __future__ import annotations

import discord
from discord.ext import commands

from services.database_service import upsert_guild_config, get_guild_config
from utils import embeds
from utils.checks import admin_only, guild_only
from utils.logger import get_logger

log = get_logger("cogs.config")


class ConfigCog(commands.Cog, name="Config"):
    def __init__(self, bot: discord.Bot) -> None:
        self.bot = bot

    config_group = discord.SlashCommandGroup("config", "Server configuration commands")

    @config_group.command(name="show", description="Show current server configuration")
    @guild_only()
    @admin_only()
    async def config_show(self, ctx: discord.ApplicationContext):
        row = await get_guild_config(ctx.guild.id)
        embed = embeds.base(title="⚙️ Server Configuration", color=embeds.INFO)

        def ch(cid): return f"<#{cid}>" if cid else "Not set"
        def role(rid): return f"<@&{rid}>" if rid else "Not set"

        if row:
            embed.add_field(name="Prefix", value=row["prefix"] or "!", inline=True)
            embed.add_field(name="Log Channel", value=ch(row["log_channel"]), inline=True)
            embed.add_field(name="Mod Log Channel", value=ch(row["mod_log_channel"]), inline=True)
            embed.add_field(name="Welcome Channel", value=ch(row["welcome_channel"]), inline=True)
            embed.add_field(name="Leave Channel", value=ch(row["leave_channel"]), inline=True)
            embed.add_field(name="Suggestion Channel", value=ch(row["suggestion_channel"]), inline=True)
            embed.add_field(name="Security Channel", value=ch(row["security_channel"]), inline=True)
        else:
            embed.description = "No configuration stored. Using environment defaults."

        await ctx.respond(embed=embed, ephemeral=True)

    @config_group.command(name="setlogchannel", description="Set the general log channel")
    @guild_only()
    @admin_only()
    async def set_log_channel(
        self,
        ctx: discord.ApplicationContext,
        channel: discord.Option(discord.TextChannel, "Log channel"),
    ):
        await upsert_guild_config(ctx.guild.id, log_channel=channel.id)
        await ctx.respond(embed=embeds.success("Log Channel Set", f"Log channel set to {channel.mention}."), ephemeral=True)

    @config_group.command(name="setmodlogchannel", description="Set the moderation log channel")
    @guild_only()
    @admin_only()
    async def set_mod_log_channel(
        self,
        ctx: discord.ApplicationContext,
        channel: discord.Option(discord.TextChannel, "Mod log channel"),
    ):
        await upsert_guild_config(ctx.guild.id, mod_log_channel=channel.id)
        await ctx.respond(embed=embeds.success("Mod Log Channel Set", f"Mod log set to {channel.mention}."), ephemeral=True)

    @config_group.command(name="setwelcomechannel", description="Set the welcome channel")
    @guild_only()
    @admin_only()
    async def set_welcome_channel(
        self,
        ctx: discord.ApplicationContext,
        channel: discord.Option(discord.TextChannel, "Welcome channel"),
    ):
        await upsert_guild_config(ctx.guild.id, welcome_channel=channel.id)
        await ctx.respond(embed=embeds.success("Welcome Channel Set", f"Welcome channel set to {channel.mention}."), ephemeral=True)

    @config_group.command(name="setleavechannel", description="Set the leave channel")
    @guild_only()
    @admin_only()
    async def set_leave_channel(
        self,
        ctx: discord.ApplicationContext,
        channel: discord.Option(discord.TextChannel, "Leave channel"),
    ):
        await upsert_guild_config(ctx.guild.id, leave_channel=channel.id)
        await ctx.respond(embed=embeds.success("Leave Channel Set", f"Leave channel set to {channel.mention}."), ephemeral=True)

    @config_group.command(name="setsuggestchannel", description="Set the suggestion channel")
    @guild_only()
    @admin_only()
    async def set_suggest_channel(
        self,
        ctx: discord.ApplicationContext,
        channel: discord.Option(discord.TextChannel, "Suggestion channel"),
    ):
        await upsert_guild_config(ctx.guild.id, suggestion_channel=channel.id)
        await ctx.respond(embed=embeds.success("Suggestion Channel Set", f"Suggestion channel set to {channel.mention}."), ephemeral=True)

    @config_group.command(name="setsecuritychannel", description="Set the security log channel")
    @guild_only()
    @admin_only()
    async def set_security_channel(
        self,
        ctx: discord.ApplicationContext,
        channel: discord.Option(discord.TextChannel, "Security log channel"),
    ):
        await upsert_guild_config(ctx.guild.id, security_channel=channel.id)
        await ctx.respond(embed=embeds.success("Security Channel Set", f"Security channel set to {channel.mention}."), ephemeral=True)

    @config_group.command(name="setprefix", description="Set the bot prefix for legacy commands")
    @guild_only()
    @admin_only()
    async def set_prefix(
        self,
        ctx: discord.ApplicationContext,
        prefix: discord.Option(str, "New command prefix (e.g. ! or ?)"),
    ):
        if len(prefix) > 5:
            return await ctx.respond(embed=embeds.error("Invalid Prefix", "Prefix must be 5 characters or less."), ephemeral=True)
        await upsert_guild_config(ctx.guild.id, prefix=prefix)
        await ctx.respond(embed=embeds.success("Prefix Updated", f"Prefix set to `{prefix}`."), ephemeral=True)


def setup(bot: discord.Bot) -> None:
    bot.add_cog(ConfigCog(bot))
