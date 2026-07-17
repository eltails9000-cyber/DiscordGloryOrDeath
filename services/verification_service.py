"""
Verification service — captcha flow, account age checks, alt detection.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import discord

import config
from services.database_service import execute, fetchone
from services.security_service import is_alt_account
from utils.helpers import generate_captcha, utcnow
from utils.logger import get_logger

log = get_logger("verification")


async def start_verification(interaction: discord.Interaction) -> None:
    """Triggered when a user clicks the Verify button."""
    member = interaction.user
    guild = interaction.guild
    if guild is None or not isinstance(member, discord.Member):
        await interaction.response.send_message("This only works in a server.", ephemeral=True)
        return

    # Account age check
    age_days = (utcnow() - member.created_at).days
    if age_days < config.VERIFICATION_MIN_ACCOUNT_AGE:
        await interaction.response.send_message(
            f"❌ Your account must be at least **{config.VERIFICATION_MIN_ACCOUNT_AGE} days** old to verify.\n"
            f"Your account is **{age_days} day(s)** old.",
            ephemeral=True,
        )
        log.info("Rejected alt/new account: %s (%d days)", member, age_days)
        return

    # Already verified?
    if config.ROLE_VERIFIED and discord.utils.get(member.roles, id=config.ROLE_VERIFIED):
        await interaction.response.send_message("✅ You are already verified!", ephemeral=True)
        return

    # Check attempt limit
    row = await fetchone(
        "SELECT * FROM verification_attempts WHERE guild_id = ? AND user_id = ?",
        (guild.id, member.id),
    )
    if row and row["attempts"] >= config.VERIFICATION_MAX_ATTEMPTS:
        await interaction.response.send_message(
            f"❌ You have exceeded the maximum verification attempts ({config.VERIFICATION_MAX_ATTEMPTS}).\n"
            "Please contact a moderator.",
            ephemeral=True,
        )
        return

    # Generate captcha
    captcha = generate_captcha(config.VERIFICATION_CAPTCHA_LENGTH)

    # Store attempt
    await execute(
        """
        INSERT INTO verification_attempts (guild_id, user_id, attempts, captcha)
        VALUES (?, ?, 0, ?)
        ON CONFLICT(guild_id, user_id) DO UPDATE SET
            captcha = excluded.captcha,
            attempts = attempts + 1
        """,
        (guild.id, member.id, captcha),
    )

    from utils.views import CaptchaModal

    async def on_submit(inter: discord.Interaction, answer: str) -> None:
        await _process_captcha(inter, member, guild, captcha, answer)

    await interaction.response.send_modal(CaptchaModal(captcha, on_submit))


async def _process_captcha(
    interaction: discord.Interaction,
    member: discord.Member,
    guild: discord.Guild,
    expected: str,
    provided: str,
) -> None:
    if provided.upper().strip() != expected.upper():
        await interaction.response.send_message(
            "❌ Incorrect captcha. Please try again by clicking Verify.",
            ephemeral=True,
        )
        log.info("Failed captcha from %s in guild %d", member, guild.id)
        return

    # Grant verified role
    if config.ROLE_VERIFIED:
        role = guild.get_role(config.ROLE_VERIFIED)
        if role:
            try:
                await member.add_roles(role, reason="Verified")
            except discord.Forbidden:
                log.warning("Cannot assign verified role to %s", member)

    # Remove unverified role if set
    if config.ROLE_UNVERIFIED:
        role = guild.get_role(config.ROLE_UNVERIFIED)
        if role:
            try:
                await member.remove_roles(role, reason="Verified")
            except discord.Forbidden:
                pass

    # Mark verified in DB
    await execute(
        "UPDATE verification_attempts SET verified = 1, verified_at = datetime('now') "
        "WHERE guild_id = ? AND user_id = ?",
        (guild.id, member.id),
    )

    await interaction.response.send_message(
        "✅ **Verification complete!** Welcome to the server.",
        ephemeral=True,
    )
    log.info("User %s verified in guild %d", member, guild.id)


async def get_verification_status(guild_id: int, user_id: int) -> Optional[dict]:
    row = await fetchone(
        "SELECT * FROM verification_attempts WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id),
    )
    if not row:
        return None
    return dict(row)
