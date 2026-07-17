import discord
from discord import app_commands
from discord.ext import commands
import utils.maintenance_state as state
from utils.messages import success_embed, info_embed
from utils.permissions import owner_check
import logging

logger = logging.getLogger(__name__)


class Maintenance(commands.Cog):
    """Commands for toggling bot maintenance mode."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    maintenance_group = app_commands.Group(
        name="maintenance",
        description="Control the bot maintenance mode.",
    )

    @maintenance_group.command(name="on", description="Enable maintenance mode.")
    @owner_check()
    async def maintenance_on(self, interaction: discord.Interaction) -> None:
        if state.maintenance_mode:
            await interaction.response.send_message(
                embed=info_embed("Mantenimiento", "El modo de mantenimiento ya está activo."),
                ephemeral=True,
            )
            return
        state.maintenance_mode = True
        logger.info("Maintenance mode ENABLED by %s", interaction.user)
        await interaction.response.send_message(
            embed=success_embed("Mantenimiento activado", "El bot está ahora en modo de mantenimiento.")
        )

    @maintenance_group.command(name="off", description="Disable maintenance mode.")
    @owner_check()
    async def maintenance_off(self, interaction: discord.Interaction) -> None:
        if not state.maintenance_mode:
            await interaction.response.send_message(
                embed=info_embed("Mantenimiento", "El modo de mantenimiento ya está desactivado."),
                ephemeral=True,
            )
            return
        state.maintenance_mode = False
        logger.info("Maintenance mode DISABLED by %s", interaction.user)
        await interaction.response.send_message(
            embed=success_embed("Mantenimiento desactivado", "El bot ha vuelto a su estado normal.")
        )

    @app_commands.command(name="botstatus", description="Show the current bot status.")
    @owner_check()
    async def botstatus(self, interaction: discord.Interaction) -> None:
        mode_str = "🔴 En mantenimiento" if state.maintenance_mode else "🟢 Operativo"
        guilds = len(self.bot.guilds)
        latency = round(self.bot.latency * 1000, 2)
        embed = info_embed(
            "Estado del bot",
            (
                f"**Estado:** {mode_str}\n"
                f"**Servidores:** {guilds}\n"
                f"**Latencia:** {latency} ms"
            ),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Maintenance(bot))
