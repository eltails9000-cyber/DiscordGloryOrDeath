import discord
from discord import app_commands
from discord.ext import commands
from api import RobloxAPI
import database as db
from utils.messages import success_embed, error_embed, info_embed
from utils.permissions import owner_check
import logging

logger = logging.getLogger(__name__)


class Roblox(commands.Cog):
    """Commands for managing Roblox bans via the external API."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.roblox_api = RobloxAPI()

    @app_commands.command(name="robloxban", description="Ban a Roblox user and record it in the database.")
    @app_commands.describe(userid="The Roblox user ID to ban", reason="Reason for the ban")
    @app_commands.default_permissions(ban_members=True)
    async def robloxban(
        self,
        interaction: discord.Interaction,
        userid: str,
        reason: str,
    ) -> None:
        await interaction.response.defer()

        if db.is_banned(userid):
            await interaction.followup.send(
                embed=error_embed("Ya baneado", f"El usuario `{userid}` ya tiene un ban registrado."),
                ephemeral=True,
            )
            return

        # 1. Save to database
        saved = db.add_ban(userid, reason, str(interaction.user))
        if not saved:
            await interaction.followup.send(
                embed=error_embed("Error de base de datos", "No se pudo guardar el ban en la base de datos."),
                ephemeral=True,
            )
            return

        # 2. Send ban to Roblox API
        api_result = await self.roblox_api.ban(int(userid), reason)

        if api_result is None:
            # API failed but local ban was saved
            logger.warning("Roblox API ban call failed for userid %s", userid)
            await interaction.followup.send(
                embed=info_embed(
                    "Ban parcial",
                    (
                        f"El usuario `{userid}` fue baneado localmente, "
                        "pero la petición a la API de Roblox falló.\n"
                        f"**Razón:** {reason}"
                    ),
                )
            )
            return

        # 3. Success embed
        logger.info("%s roblox-banned userid %s — Reason: %s", interaction.user, userid, reason)
        embed = success_embed(
            "Ban de Roblox aplicado",
            (
                f"**Usuario ID:** `{userid}`\n"
                f"**Razón:** {reason}\n"
                f"**Staff:** {interaction.user.mention}\n"
                "**Estado API:** ✅ Enviado correctamente"
            ),
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="robloxcheck", description="Check if a Roblox user is banned.")
    @app_commands.describe(userid="The Roblox user ID to check")
    async def robloxcheck(
        self,
        interaction: discord.Interaction,
        userid: str,
    ) -> None:
        await interaction.response.defer()

        ban_record = db.get_ban(userid)

        if ban_record is None:
            await interaction.followup.send(
                embed=info_embed(
                    "Sin ban registrado",
                    f"El usuario `{userid}` no tiene ningún ban en la base de datos local.",
                )
            )
            return

        embed = info_embed(
            "Información de ban",
            (
                f"**Usuario ID:** `{ban_record['userid']}`\n"
                f"**Baneado:** ✅ Sí\n"
                f"**Razón:** {ban_record['reason']}\n"
                f"**Staff:** {ban_record['staff']}\n"
                f"**Fecha:** {ban_record['created_at']}"
            ),
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="robloxunban", description="Remove a Roblox ban locally and via the API.")
    @app_commands.describe(userid="The Roblox user ID to unban")
    @app_commands.default_permissions(ban_members=True)
    async def robloxunban(
        self,
        interaction: discord.Interaction,
        userid: str,
    ) -> None:
        await interaction.response.defer()

        if not db.is_banned(userid):
            await interaction.followup.send(
                embed=error_embed("Sin ban", f"El usuario `{userid}` no tiene un ban registrado."),
                ephemeral=True,
            )
            return

        # 1. Remove from local database
        removed = db.remove_ban(userid)
        if not removed:
            await interaction.followup.send(
                embed=error_embed("Error de base de datos", "No se pudo eliminar el ban de la base de datos."),
                ephemeral=True,
            )
            return

        # 2. Send unban to Roblox API
        api_result = await self.roblox_api.unban(int(userid))

        if api_result is None:
            logger.warning("Roblox API unban call failed for userid %s", userid)
            await interaction.followup.send(
                embed=info_embed(
                    "Unban parcial",
                    (
                        f"El ban local del usuario `{userid}` fue eliminado, "
                        "pero la petición a la API de Roblox falló."
                    ),
                )
            )
            return

        logger.info("%s roblox-unbanned userid %s", interaction.user, userid)
        await interaction.followup.send(
            embed=success_embed(
                "Unban de Roblox aplicado",
                (
                    f"**Usuario ID:** `{userid}`\n"
                    f"**Staff:** {interaction.user.mention}\n"
                    "**Estado API:** ✅ Enviado correctamente"
                ),
            )
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Roblox(bot))
