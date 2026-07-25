"""Fetch rocket parts and pilots catalogs from the game API."""

from config import HIGHSCORE_API_BASE
from api.http_client import DEFAULT_TIMEOUT_SECONDS, get_json

API_BASE = HIGHSCORE_API_BASE.rstrip("/")
PARTS_URL = f"{API_BASE}/api/parts"
PILOTS_URL = f"{API_BASE}/api/pilots"


async def fetch_parts(
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> tuple[bool, dict | str]:
    """GET parts catalog. Returns (ok, payload_or_error)."""
    ok, result = await get_json(PARTS_URL, timeout=timeout)
    if not ok:
        return False, str(result)
    if not isinstance(result, dict) or not isinstance(result.get("parts"), list):
        return False, "Invalid parts payload from API"
    return True, result


async def fetch_pilots(
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> tuple[bool, dict | str]:
    """GET pilots catalog. Returns (ok, payload_or_error)."""
    ok, result = await get_json(PILOTS_URL, timeout=timeout)
    if not ok:
        return False, str(result)
    if not isinstance(result, dict) or not isinstance(result.get("pilots"), list):
        return False, "Invalid pilots payload from API"
    return True, result
