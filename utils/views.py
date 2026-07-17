"""
Persistent and ephemeral Discord UI views (buttons, selects, modals).
"""

from __future__ import annotations

import random
import discord
from typing import Optional, Callable, Awaitable

from utils.helpers import generate_captcha
import config


# ── Confirmation view ─────────────────────────────────────────────────────────

class ConfirmView(discord.ui.View):
    """A simple Yes/No confirmation prompt."""

    def __init__(self, author: discord.Member | discord.User, timeout: float = 30.0) -> None:
        super().__init__(timeout=timeout)
        self.author = author
        self.value: Optional[bool] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("This is not your confirmation.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        self.value = True
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        self.value = False
        self.stop()
        await interaction.response.defer()


# ── Verification view ─────────────────────────────────────────────────────────

class VerifyButton(discord.ui.View):
    """Persistent verify button shown in the verification channel."""

    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Verify",
        style=discord.ButtonStyle.green,
        custom_id="verify:start",
        emoji="🔐",
    )
    async def verify(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        from services.verification_service import VerificationService
        await VerificationService.start_verification(interaction)


class CaptchaModal(discord.ui.Modal):
    def __init__(self, captcha: str, on_submit: Callable[[discord.Interaction, str], Awaitable[None]]) -> None:
        super().__init__(title="Complete Verification")
        self._captcha = captcha
        self._on_submit = on_submit
        self.answer = discord.ui.InputText(
            label=f"Enter the code: {captcha}",
            placeholder="Type the captcha exactly...",
            min_length=len(captcha),
            max_length=len(captcha),
        )
        self.add_item(self.answer)

    async def callback(self, interaction: discord.Interaction) -> None:
        await self._on_submit(interaction, self.answer.value or "")


# ── Giveaway view ─────────────────────────────────────────────────────────────

class GiveawayView(discord.ui.View):
    """Persistent giveaway enter/leave button."""

    def __init__(self, giveaway_id: int) -> None:
        super().__init__(timeout=None)
        self.giveaway_id = giveaway_id
        # Encode giveaway_id in custom_id for persistence
        self.enter_button.custom_id = f"giveaway:enter:{giveaway_id}"

    @discord.ui.button(
        label="🎉 Enter",
        style=discord.ButtonStyle.primary,
        custom_id="giveaway:enter:0",  # overridden in __init__
    )
    async def enter_button(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        from services.giveaway_service import GiveawayService
        await GiveawayService.toggle_entry(interaction, self.giveaway_id)


# ── Poll view ─────────────────────────────────────────────────────────────────

class PollView(discord.ui.View):
    """Dynamic poll vote buttons."""

    def __init__(self, poll_id: int, options: list[str]) -> None:
        super().__init__(timeout=None)
        for idx, option in enumerate(options):
            btn = discord.ui.Button(
                label=option[:80],
                custom_id=f"poll:{poll_id}:{idx}",
                style=discord.ButtonStyle.secondary,
            )
            btn.callback = self._make_callback(poll_id, idx)
            self.add_item(btn)

    def _make_callback(self, poll_id: int, idx: int) -> Callable:
        async def callback(interaction: discord.Interaction) -> None:
            from services.announcement_service import AnnouncementService
            await AnnouncementService.record_vote(interaction, poll_id, idx)
        return callback


# ── Suggestion view ───────────────────────────────────────────────────────────

class SuggestionModal(discord.ui.Modal):
    def __init__(self) -> None:
        super().__init__(title="Submit a Suggestion")
        self.suggestion = discord.ui.InputText(
            label="Your Suggestion",
            style=discord.InputTextStyle.long,
            placeholder="Describe your suggestion in detail...",
            min_length=10,
            max_length=1000,
        )
        self.add_item(self.suggestion)

    async def callback(self, interaction: discord.Interaction) -> None:
        from services.announcement_service import AnnouncementService
        content = self.suggestion.value or ""
        await AnnouncementService.submit_suggestion(interaction, content)
