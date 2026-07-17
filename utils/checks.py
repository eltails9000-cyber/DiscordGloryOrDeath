"""
Custom command checks for application commands (slash commands).
"""

from __future__ import annotations

import discord
from discord.ext import commands

import config
from utils import permissions as perms


def owner_only():
    async def predicate(ctx: discord.ApplicationContext) -> bool:
        if perms.is_owner(ctx.author):
            return True
        await ctx.respond(embed=_no_perm("Only bot owners can use this command."), ephemeral=True)
        return False
    return commands.check(predicate)


def admin_only():
    async def predicate(ctx: discord.ApplicationContext) -> bool:
        if isinstance(ctx.author, discord.Member) and perms.is_admin(ctx.author):
            return True
        await ctx.respond(embed=_no_perm("You need Administrator permissions."), ephemeral=True)
        return False
    return commands.check(predicate)


def moderator_only():
    async def predicate(ctx: discord.ApplicationContext) -> bool:
        if isinstance(ctx.author, discord.Member) and perms.is_moderator(ctx.author):
            return True
        await ctx.respond(embed=_no_perm("You need Moderator permissions."), ephemeral=True)
        return False
    return commands.check(predicate)


def guild_only():
    async def predicate(ctx: discord.ApplicationContext) -> bool:
        if ctx.guild is not None:
            return True
        await ctx.respond(embed=_no_perm("This command can only be used in a server."), ephemeral=True)
        return False
    return commands.check(predicate)


def _no_perm(msg: str) -> discord.Embed:
    return discord.Embed(
        title="❌ Permission Denied",
        description=msg,
        color=0xED4245,
    )
