"""Increment and fetch the global flight counter."""

import hashlib
import hmac
import json
import secrets
import sys
import time

from config import HIGHSCORE_API_BASE, HIGHSCORE_HMAC_SECRET
from api.http_client import (
    DEFAULT_TIMEOUT_SECONDS,
    post_urllib,
    web_http,
)

API_BASE = HIGHSCORE_API_BASE.rstrip("/")
FLIGHTS_URL = f"{API_BASE}/api/flights"

_IS_WEB = sys.platform == "emscripten"


def get_hmac_secret() -> str:
    return (HIGHSCORE_HMAC_SECRET or "").strip()


def sign_flight_increment(end_reason: str, secret: str) -> dict:
    timestamp = int(time.time())
    nonce = secrets.token_hex(16)
    reason = str(end_reason)
    canonical = f"end_reason={reason}&timestamp={timestamp}&nonce={nonce}"
    signature = hmac.new(
        secret.encode("utf-8"),
        canonical.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return {
        "end_reason": reason,
        "timestamp": timestamp,
        "nonce": nonce,
        "signature": signature,
    }


def _parse_count_payload(raw: str) -> tuple[bool, int | str]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return False, "Invalid JSON from API"

    if isinstance(data, dict) and "count" in data:
        try:
            return True, int(data["count"])
        except (TypeError, ValueError):
            return False, "Invalid count from API"
    return False, "Missing count in API response"


def _increment_urllib(payload: dict, timeout: float) -> tuple[bool, int | str]:
    status, raw = post_urllib(FLIGHTS_URL, json.dumps(payload).encode("utf-8"), timeout)
    if status <= 0:
        return False, raw or "Network error"
    if not (200 <= status < 300):
        try:
            data = json.loads(raw) if raw else {}
            message = data.get("message") or data.get("error") or raw
        except json.JSONDecodeError:
            message = raw or "unknown"
        return False, f"Increment failed ({status}): {message}"
    return _parse_count_payload(raw)


async def increment_flight_count(
    end_reason: str,
    secret: str | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> tuple[bool, int | str]:
    """
    Sign and POST to increment the global flight counter.
    Returns (ok, count_or_error_message).
    """
    secret = (secret if secret is not None else get_hmac_secret()).strip()
    if not secret or secret == "replace-with-shared-secret":
        return False, "Set HIGHSCORE_HMAC_SECRET in config.local.py"

    payload = sign_flight_increment(end_reason, secret)

    if _IS_WEB:
        try:
            status, raw = await web_http("POST", FLIGHTS_URL, json.dumps(payload))
        except Exception as exc:
            return False, f"Network error: {exc}"
        if status <= 0:
            return False, f"Network error: {raw or 'request failed'}"
        if not (200 <= status < 300):
            try:
                data = json.loads(raw) if raw else {}
                message = data.get("message") or data.get("error") or raw
            except json.JSONDecodeError:
                message = raw or "unknown"
            return False, f"Increment failed ({status}): {message}"
        return _parse_count_payload(raw)

    return _increment_urllib(payload, timeout)
