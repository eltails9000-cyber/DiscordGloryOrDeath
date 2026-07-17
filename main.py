"""
Bot entry point — initialises database, loads all cogs, and starts the bot.
"""

from __future__ import annotations

import asyncio
import os
import sys

import discord
from discord.ext import commands

# Ensure bot/ is on the path when run from project root
sys.path.insert(0, os.path.dirname(__file__))

import config
from database import init_db
from services.security_service import load_scam_domains
from utils.logger import setup_logging, get_logger

# ── Logging setup (must happen before anything else) ──────────────────────────
setup_logging()
log = get_logger("main")

# ── Intents ───────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.presences = True

# ── Bot instance ──────────────────────────────────────────────────────────────
bot = discord.Bot(
    description=config.BOT_DESCRIPTION,
    intents=intents,
    owner_ids=set(config.OWNER_IDS) if config.OWNER_IDS else None,
)

# ── Cogs to load ──────────────────────────────────────────────────────────────
COGS: list[str] = [
    "cogs.events",
    "cogs.moderation",
    "cogs.security",
    "cogs.verification",
    "cogs.giveaways",
    "cogs.announcements",
    "cogs.ai",
    "cogs.owner",
    "cogs.config_cog",
]


# ── Bot events ────────────────────────────────────────────────────────────────

@bot.event
async def on_ready() -> None:
    log.info("Logged in as %s (ID: %s)", bot.user, bot.user.id)
    log.info("Serving %d guild(s)", len(bot.guilds))
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{len(bot.guilds)} servers | /help",
        )
    )


@bot.event
async def on_application_command_error(
    ctx: discord.ApplicationContext,
    error: discord.DiscordException,
) -> None:
    if isinstance(error, commands.CommandOnCooldown):
        embed = discord.Embed(
            title="⏳ Cooldown",
            description=f"Try again in **{error.retry_after:.1f}s**.",
            color=0xFEE75C,
        )
        await ctx.respond(embed=embed, ephemeral=True)
    elif isinstance(error, commands.CheckFailure):
        pass  # checks handle their own responses
    else:
        log.exception("Unhandled command error in /%s: %s", ctx.command, error)
        try:
            await ctx.respond(
                embed=discord.Embed(
                    title="❌ Unexpected Error",
                    description=str(error)[:500],
                    color=0xED4245,
                ),
                ephemeral=True,
            )
        except Exception:
            pass


@bot.event
async def on_error(event: str, *args, **kwargs) -> None:
    log.exception("Unhandled exception in event %s", event)


# ── Startup ───────────────────────────────────────────────────────────────────

async def main() -> None:
    if not config.BOT_TOKEN:
        log.critical("DISCORD_TOKEN is not set. Cannot start bot.")
        sys.exit(1)

    # Initialise database
    await init_db()

    # Load scam domain list
    await load_scam_domains()

    # Load all cogs
    for cog in COGS:
        try:
            bot.load_extension(cog)
            log.info("Loaded cog: %s", cog)
        except Exception as exc:
            log.error("Failed to load cog %s: %s", cog, exc)

    log.info("Starting bot…")
    await bot.start(config.BOT_TOKEN)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Bot stopped by user.")
