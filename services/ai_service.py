"""
AI service — FAQ responses via OpenAI, custom knowledge base, auto-answers.
"""

from __future__ import annotations

import json
from typing import Optional

import config
from services.database_service import execute, fetchall, fetchone
from utils.logger import get_logger

log = get_logger("ai")

_client: Optional[object] = None


def _get_client():
    global _client
    if _client is None:
        if not config.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is not set")
        from openai import AsyncOpenAI
        _client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
    return _client


async def ask(guild_id: int, question: str) -> str:
    """Ask the AI a question, checking local knowledge base first."""
    # 1. Check local knowledge base
    local = await _check_knowledge_base(guild_id, question)
    if local:
        return local

    # 2. Fall back to OpenAI
    if not config.OPENAI_API_KEY:
        return "❌ AI features are not configured. Set the `OPENAI_API_KEY` environment variable."

    try:
        client = _get_client()
        messages = [
            {"role": "system", "content": config.AI_SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]
        response = await client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=messages,
            max_tokens=config.AI_MAX_TOKENS,
            temperature=config.AI_TEMPERATURE,
        )
        answer = response.choices[0].message.content or "I couldn't generate a response."
        log.debug("AI answered question in guild %d", guild_id)
        return answer
    except Exception as exc:
        log.error("OpenAI error: %s", exc)
        return f"❌ AI error: {exc}"


async def _check_knowledge_base(guild_id: int, question: str) -> Optional[str]:
    """Simple keyword match against the knowledge base."""
    rows = await fetchall(
        "SELECT keyword, answer FROM ai_knowledge WHERE guild_id = ?",
        (guild_id,),
    )
    q_lower = question.lower()
    for row in rows:
        if row["keyword"].lower() in q_lower:
            return row["answer"]
    return None


async def add_knowledge(
    guild_id: int,
    keyword: str,
    answer: str,
    added_by: int,
) -> int:
    row_id = await execute(
        "INSERT INTO ai_knowledge (guild_id, keyword, answer, added_by) VALUES (?, ?, ?, ?)",
        (guild_id, keyword, answer, added_by),
    )
    log.info("Knowledge base entry added: %r in guild %d", keyword, guild_id)
    return row_id


async def remove_knowledge(guild_id: int, knowledge_id: int) -> bool:
    row = await fetchone(
        "SELECT id FROM ai_knowledge WHERE id = ? AND guild_id = ?",
        (knowledge_id, guild_id),
    )
    if not row:
        return False
    await execute("DELETE FROM ai_knowledge WHERE id = ?", (knowledge_id,))
    return True


async def list_knowledge(guild_id: int) -> list:
    return await fetchall(
        "SELECT * FROM ai_knowledge WHERE guild_id = ? ORDER BY keyword",
        (guild_id,),
    )
