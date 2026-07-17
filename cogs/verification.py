"""
Verification cog — setup verification panel, admin commands.
"""

from __future__ import annotations

import discord
from discord.ext import commands

import config
from utils import embeds
from utils.checks import admin_only, guild_only
from utils.logger import get_logger
from utils.views import VerifyButton

log = get_logger("cogs.verification")


class VerificationCog(commands.Cog, name="Verification"):
    def __init__(self, bot: discord.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        # Re-register persistent view
        self.bot.add_view(VerifyButton())

    @discord.slash_command(name="setupverification", description="Post the verification panel in a channel")
    @guild_only()
    @admin_only()
    async def setup_verification(
        self,
        ctx: discord.ApplicationContext,
        channel: discord.Option(discord.TextChannel, "Channel to post the panel", required=False),
    ):
        ch = channel or ctx.channel
        embed = embeds.verification_embed()
        view = VerifyButton()
        await ch.send(embed=embed, view=view)
        await ctx.respond(
            embed=embeds.success("Verification Panel Posted", f"Panel posted in {ch.mention}."),
            ephemeral=True,
        )

    @discord.slash_command(name="verificationstatus", description="Check verification status of a member")
    @guild_only()
    @admin_only()
    async def verification_status(
        self,
        ctx: discord.ApplicationContext,
        member: discord.Option(discord.Member, "Member to check"),
    ):
        from services.verification_service import get_verification_status
        data = await get_verification_status(ctx.guild.id, member.id)
        if not data:
            return await ctx.respond(
                embed=embeds.info("No Record", f"{member.mention} has no verification record."),
                ephemeral=True,
            )

        embed = embeds.base(
            title=f"🔐 Verification: {member}",
            color=embeds.SUCCESS if data["verified"] else embeds.WARNING,
            footer=f"User ID: {member.id}",
        )
        embed.add_field(name="Verified", value="✅ Yes" if data["verified"] else "❌ No", inline=True)
        embed.add_field(name="Attempts", value=str(data["attempts"]), inline=True)
        if data.get("verified_at"):
            embed.add_field(name="Verified At", value=data["verified_at"][:19], inline=True)
        await ctx.respond(embed=embed, ephemeral=True)

    @discord.slash_command(name="forceunverify", description="Reset a member's verification")
    @guild_only()
    @admin_only()
    async def force_unverify(
        self,
        ctx: discord.ApplicationContext,
        member: discord.Option(discord.Member, "Member to unverify"),
    ):
        from services.database_service import execute
        await execute(
            "DELETE FROM verification_attempts WHERE guild_id = ? AND user_id = ?",
            (ctx.guild.id, member.id),
        )
        if config.ROLE_VERIFIED:
            role = ctx.guild.get_role(config.ROLE_VERIFIED)
            if role and role in member.roles:
                try:
                    await member.remove_roles(role, reason="Force unverified by admin")
                except discord.Forbidden:
                    pass

        await ctx.respond(
            embed=embeds.success("Unverified", f"{member.mention} has been unverified."),
            ephemeral=True,
        )


def setup(bot: discord.Bot) -> None:
    bot.add_cog(VerificationCog(bot))
