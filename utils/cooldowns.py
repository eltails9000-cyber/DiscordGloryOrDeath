"""
Custom cooldown buckets and helpers.
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Callable

import discord
from discord.ext import commands

import config


class CooldownManager:
    """Simple per-user, per-command cooldown tracker."""

    def __init__(self) -> None:
        # {command_name: {user_id: last_used_timestamp}}
        self._buckets: dict[str, dict[int, float]] = defaultdict(dict)

    def check(self, command: str, user_id: int, rate: float = config.DEFAULT_COOLDOWN_PER) -> float:
        """Return remaining cooldown in seconds (0 if ready)."""
        now = time.monotonic()
        last = self._buckets[command].get(user_id, 0.0)
        remaining = rate - (now - last)
        return max(0.0, remaining)

    def update(self, command: str, user_id: int) -> None:
        self._buckets[command][user_id] = time.monotonic()

    def reset(self, command: str, user_id: int) -> None:
        self._buckets[command].pop(user_id, None)


# Global singleton
cooldown_manager = CooldownManager()


def slash_cooldown(rate: int = config.DEFAULT_COOLDOWN_RATE, per: float = config.DEFAULT_COOLDOWN_PER):
    """Decorator applying per-user cooldowns to slash commands."""
    def decorator(func: Callable) -> Callable:
        return commands.cooldown(rate, per, commands.BucketType.user)(func)
    return decorator
