"""
AI cog — FAQ commands, automatic answers, knowledge base management.
"""

from __future__ import annotations

import discord
from discord.ext import commands

from services.ai_service import ask, add_knowledge, remove_knowledge, list_knowledge
from utils import embeds
from utils.checks import admin_only, moderator_only, guild_only
from utils.cooldowns import slash_cooldown
from utils.helpers import truncate
from utils.logger import get_logger

log = get_logger("cogs.ai")


class AICog(commands.Cog, name="AI"):
    def __init__(self, bot: discord.Bot) -> None:
        self.bot = bot

    # ── /ask ──────────────────────────────────────────────────────────────────

    @discord.slash_command(name="ask", description="Ask the AI a question")
    @guild_only()
    @slash_cooldown(1, 10)
    async def ask_ai(
        self,
        ctx: discord.ApplicationContext,
        question: discord.Option(str, "Your question"),
    ):
        await ctx.defer()
        answer = await ask(ctx.guild.id, question)
        embed = embeds.base(
            title="🤖 AI Answer",
            description=truncate(answer, 4096),
            color=0x5865F2,
            author=ctx.author,
            footer="Powered by AI",
        )
        embed.add_field(name="Question", value=truncate(question, 512), inline=False)
        await ctx.respond(embed=embed)

    # ── Knowledge base management ─────────────────────────────────────────────

    ai_group = discord.SlashCommandGroup("ai", "AI knowledge base management")

    @ai_group.command(name="addknowledge", description="Add a keyword/answer to the knowledge base")
    @guild_only()
    @moderator_only()
    async def add_knowledge_cmd(
        self,
        ctx: discord.ApplicationContext,
        keyword: discord.Option(str, "Trigger keyword"),
        answer: discord.Option(str, "Answer to return"),
    ):
        row_id = await add_knowledge(ctx.guild.id, keyword, answer, ctx.author.id)
        embed = embeds.success(
            "Knowledge Added",
            f"**Keyword:** `{keyword}`\n**Answer:** {truncate(answer, 200)}\n**ID:** {row_id}",
        )
        await ctx.respond(embed=embed, ephemeral=True)

    @ai_group.command(name="removeknowledge", description="Remove a knowledge base entry")
    @guild_only()
    @moderator_only()
    async def remove_knowledge_cmd(
        self,
        ctx: discord.ApplicationContext,
        knowledge_id: discord.Option(int, "Knowledge entry ID"),
    ):
        removed = await remove_knowledge(ctx.guild.id, knowledge_id)
        if not removed:
            return await ctx.respond(embed=embeds.error("Not Found", "Knowledge entry not found."), ephemeral=True)
        await ctx.respond(embed=embeds.success("Removed", f"Knowledge entry #{knowledge_id} removed."), ephemeral=True)

    @ai_group.command(name="listknowledge", description="List all knowledge base entries")
    @guild_only()
    @admin_only()
    async def list_knowledge_cmd(self, ctx: discord.ApplicationContext):
        rows = await list_knowledge(ctx.guild.id)
        if not rows:
            return await ctx.respond(embed=embeds.info("Empty", "No knowledge base entries."), ephemeral=True)

        desc = "\n".join(
            f"**#{r['id']}** `{r['keyword']}` → {truncate(r['answer'], 80)}"
            for r in rows[:25]
        )
        embed = embeds.base(
            title="🧠 Knowledge Base",
            description=desc,
            color=0x5865F2,
            footer=f"Total: {len(rows)}",
        )
        await ctx.respond(embed=embed, ephemeral=True)


def setup(bot: discord.Bot) -> None:
    bot.add_cog(AICog(bot))
