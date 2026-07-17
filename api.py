import aiohttp
import logging
from typing import Optional
from config import ROBLOX_API_URL, ROBLOX_API_KEY

logger = logging.getLogger(__name__)

TIMEOUT = aiohttp.ClientTimeout(total=10)


class RobloxAPI:
    """Async wrapper for the Roblox ban API."""

    def __init__(self) -> None:
        self._headers = {"x-api-key": ROBLOX_API_KEY}

    async def ban(self, userid: int, reason: str) -> Optional[dict]:
        """Send a ban request to the Roblox API."""
        if not ROBLOX_API_URL or not ROBLOX_API_KEY:
            logger.warning("Roblox API URL or key is not configured.")
            return None
        url = f"{ROBLOX_API_URL}/ban"
        payload = {"userId": userid, "reason": reason}
        try:
            async with aiohttp.ClientSession(headers=self._headers, timeout=TIMEOUT) as session:
                async with session.post(url, json=payload) as response:
                    response.raise_for_status()
                    return await response.json()
        except aiohttp.ClientResponseError as exc:
            logger.error("HTTP error banning userid %s: %s %s", userid, exc.status, exc.message)
        except aiohttp.ClientError as exc:
            logger.error("Request error banning userid %s: %s", userid, exc)
        except Exception as exc:
            logger.error("Unexpected error banning userid %s: %s", userid, exc)
        return None

    async def unban(self, userid: int) -> Optional[dict]:
        """Send an unban request to the Roblox API."""
        if not ROBLOX_API_URL or not ROBLOX_API_KEY:
            logger.warning("Roblox API URL or key is not configured.")
            return None
        url = f"{ROBLOX_API_URL}/unban"
        payload = {"userId": userid}
        try:
            async with aiohttp.ClientSession(headers=self._headers, timeout=TIMEOUT) as session:
                async with session.post(url, json=payload) as response:
                    response.raise_for_status()
                    return await response.json()
        except aiohttp.ClientResponseError as exc:
            logger.error("HTTP error unbanning userid %s: %s %s", userid, exc.status, exc.message)
        except aiohttp.ClientError as exc:
            logger.error("Request error unbanning userid %s: %s", userid, exc)
        except Exception as exc:
            logger.error("Unexpected error unbanning userid %s: %s", userid, exc)
        return None

    async def check(self, userid: int) -> Optional[dict]:
        """Check the ban status of a user via the Roblox API."""
        if not ROBLOX_API_URL or not ROBLOX_API_KEY:
            logger.warning("Roblox API URL or key is not configured.")
            return None
        url = f"{ROBLOX_API_URL}/check/{userid}"
        try:
            async with aiohttp.ClientSession(headers=self._headers, timeout=TIMEOUT) as session:
                async with session.get(url) as response:
                    response.raise_for_status()
                    return await response.json()
        except aiohttp.ClientResponseError as exc:
            logger.error("HTTP error checking userid %s: %s %s", userid, exc.status, exc.message)
        except aiohttp.ClientError as exc:
            logger.error("Request error checking userid %s: %s", userid, exc)
        except Exception as exc:
            logger.error("Unexpected error checking userid %s: %s", userid, exc)
        return None
