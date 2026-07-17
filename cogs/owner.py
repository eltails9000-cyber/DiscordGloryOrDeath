"""
Owner cog — bot owner-only management commands.
"""

from __future__ import annotations

import discord

from utils import embeds
from utils.checks import owner_only
from utils.logger import get_logger

log = get_logger("cogs.owner")


class OwnerCog(discord.Cog, name="Owner"):
    def __init__(self, bot: discord.Bot) -> None:
        self.bot = bot

    # ── /reload ───────────────────────────────────────────────────────────────

    @discord.slash_command(name="reload", description="Reload a cog")
    @owner_only()
    async def reload(
        self,
        ctx: discord.ApplicationContext,
        cog: discord.Option(str, "Cog name to reload e.g. moderation"),
    ):
        ext = f"cogs.{cog.lower()}"
        try:
            self.bot.reload_extension(ext)
            await ctx.respond(embed=embeds.success("Reloaded", f"Cog `{ext}` reloaded."), ephemeral=True)
            log.info("Reloaded cog: %s", ext)
        except Exception as exc:
            await ctx.respond(embed=embeds.error("Reload Failed", str(exc)), ephemeral=True)

    # ── /loadcog / /unloadcog ─────────────────────────────────────────────────

    @discord.slash_command(name="loadcog", description="Load a cog")
    @owner_only()
    async def load_cog(
        self,
        ctx: discord.ApplicationContext,
        cog: discord.Option(str, "Cog name to load"),
    ):
        ext = f"cogs.{cog.lower()}"
        try:
            self.bot.load_extension(ext)
            await ctx.respond(embed=embeds.success("Loaded", f"Cog `{ext}` loaded."), ephemeral=True)
        except Exception as exc:
            await ctx.respond(embed=embeds.error("Load Failed", str(exc)), ephemeral=True)

    @discord.slash_command(name="unloadcog", description="Unload a cog")
    @owner_only()
    async def unload_cog(
        self,
        ctx: discord.ApplicationContext,
        cog: discord.Option(str, "Cog name to unload"),
    ):
        ext = f"cogs.{cog.lower()}"
        try:
            self.bot.unload_extension(ext)
            await ctx.respond(embed=embeds.success("Unloaded", f"Cog `{ext}` unloaded."), ephemeral=True)
        except Exception as exc:
            await ctx.respond(embed=embeds.error("Unload Failed", str(exc)), ephemeral=True)

    # ── /status ───────────────────────────────────────────────────────────────

    @discord.slash_command(name="botstatus", description="Change bot status")
    @owner_only()
    async def change_status(
        self,
        ctx: discord.ApplicationContext,
        status_type: discord.Option(str, "Type", choices=["playing", "watching", "listening", "streaming"]),
        text: discord.Option(str, "Status text"),
        url: discord.Option(str, "Stream URL (streaming only)", required=False),
    ):
        activity: discord.BaseActivity
        if status_type == "playing":
            activity = discord.Game(name=text)
        elif status_type == "watching":
            activity = discord.Activity(type=discord.ActivityType.watching, name=text)
        elif status_type == "listening":
            activity = discord.Activity(type=discord.ActivityType.listening, name=text)
        else:
            activity = discord.Streaming(name=text, url=url or "https://twitch.tv/placeholder")

        await self.bot.change_presence(activity=activity)
        await ctx.respond(embed=embeds.success("Status Updated", f"Bot is now `{status_type} {text}`."), ephemeral=True)

    # ── /shutdown ─────────────────────────────────────────────────────────────

    @discord.slash_command(name="shutdown", description="Shut down the bot")
    @owner_only()
    async def shutdown(self, ctx: discord.ApplicationContext):
        await ctx.respond(embed=embeds.warning("Shutting Down", "Goodbye!"), ephemeral=True)
        log.warning("Shutdown initiated by %s", ctx.author)
        await self.bot.close()

    # ── /botinfo ──────────────────────────────────────────────────────────────

    @discord.slash_command(name="botinfo", description="Show bot statistics")
    @owner_only()
    async def botinfo(self, ctx: discord.ApplicationContext):
        import sys, platform
        embed = embeds.base(title="🤖 Bot Info", color=embeds.INFO, thumbnail=str(self.bot.user.display_avatar.url))
        embed.add_field(name="Guilds", value=str(len(self.bot.guilds)), inline=True)
        embed.add_field(name="Users", value=str(sum(g.member_count or 0 for g in self.bot.guilds)), inline=True)
        embed.add_field(name="Python", value=sys.version[:6], inline=True)
        embed.add_field(name="Platform", value=platform.system(), inline=True)
        embed.add_field(name="Latency", value=f"{self.bot.latency * 1000:.1f}ms", inline=True)
        embed.add_field(name="Cogs", value=str(len(self.bot.cogs)), inline=True)
        await ctx.respond(embed=embed, ephemeral=True)

    # ── /dm ───────────────────────────────────────────────────────────────────

    @discord.slash_command(name="dm", description="DM a user (owner only)")
    @owner_only()
    async def dm_user(
        self,
        ctx: discord.ApplicationContext,
        user: discord.Option(discord.User, "User to DM"),
        message: discord.Option(str, "Message to send"),
    ):
        try:
            await user.send(message)
            await ctx.respond(embed=embeds.success("DM Sent", f"Message sent to {user.mention}."), ephemeral=True)
        except discord.Forbidden:
            await ctx.respond(embed=embeds.error("DM Failed", "Cannot DM this user."), ephemeral=True)

    # ── /eval (safe, no-exec) ─────────────────────────────────────────────────

    @discord.slash_command(name="servers", description="List all servers the bot is in")
    @owner_only()
    async def list_servers(self, ctx: discord.ApplicationContext):
        guilds = sorted(self.bot.guilds, key=lambda g: g.member_count or 0, reverse=True)
        desc = "\n".join(
            f"`{g.id}` **{g.name}** — {g.member_count} members"
            for g in guilds[:25]
        )
        embed = embeds.base(
            title=f"📋 Servers ({len(guilds)})",
            description=desc or "None",
            color=embeds.INFO,
        )
        await ctx.respond(embed=embed, ephemeral=True)

    # ── /sync ─────────────────────────────────────────────────────────────────

    @discord.slash_command(name="sync", description="Sync slash commands globally")
    @owner_only()
    async def sync_commands(self, ctx: discord.ApplicationContext):
        await ctx.defer(ephemeral=True)
        await self.bot.sync_commands()
        await ctx.respond(embed=embeds.success("Synced", "Slash commands synced globally."), ephemeral=True)
        log.info("Slash commands synced by %s", ctx.author)


def setup(bot: discord.Bot) -> None:
    bot.add_cog(OwnerCog(bot))
