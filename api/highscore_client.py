import hashlib
import hmac
import json
import secrets
import sys
import time

from config import HIGHSCORE_API_BASE, HIGHSCORE_HMAC_SECRET
from api.http_client import (
    DEFAULT_TIMEOUT_SECONDS,
    get_urllib,
    post_urllib,
    web_http,
)

API_BASE = HIGHSCORE_API_BASE.rstrip("/")
HIGHSCORES_URL = f"{API_BASE}/api/highscores"

_IS_WEB = sys.platform == "emscripten"

ROCKET_SLOT_KEYS = (
    "nose_cone_id",
    "fuel_tank_id",
    "engine_id",
    "fin_id",
)


def get_hmac_secret() -> str:
    return (HIGHSCORE_HMAC_SECRET or "").strip()


def format_number(value: float | int) -> str:
    formatted = f"{float(value):.6f}".rstrip("0").rstrip(".")
    return "0" if formatted == "-0" else formatted


def normalize_rocket(rocket: dict) -> dict[str, str]:
    missing = [key for key in ROCKET_SLOT_KEYS if not rocket.get(key)]
    if missing:
        raise ValueError(f"Rocket missing required slots: {', '.join(missing)}")
    return {key: str(rocket[key]) for key in ROCKET_SLOT_KEYS}


def sign_highscore(
    name: str,
    height: float,
    secret: str,
    pilot_id: int | str,
    rocket: dict,
    top_speed: float | None = None,
) -> dict:
    rocket = normalize_rocket(rocket)
    timestamp = int(time.time())
    nonce = secrets.token_hex(16)
    top = "" if top_speed is None else format_number(top_speed)
    pilot = str(pilot_id)
    canonical = (
        f"name={name}"
        f"&height={format_number(height)}"
        f"&top_speed={top}"
        f"&pilot_id={pilot}"
        f"&nose_cone_id={rocket['nose_cone_id']}"
        f"&fuel_tank_id={rocket['fuel_tank_id']}"
        f"&engine_id={rocket['engine_id']}"
        f"&fin_id={rocket['fin_id']}"
        f"&timestamp={timestamp}"
        f"&nonce={nonce}"
    )
    signature = hmac.new(
        secret.encode("utf-8"),
        canonical.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    payload = {
        "name": name,
        "height": height,
        "pilot_id": int(pilot_id) if str(pilot_id).isdigit() else pilot_id,
        "rocket": rocket,
        "timestamp": timestamp,
        "nonce": nonce,
        "signature": signature,
    }
    if top_speed is not None:
        payload["top_speed"] = top_speed
    return payload


def _parse_leaderboard_payload(raw: str) -> tuple[bool, list | str]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return False, "Invalid JSON from API"

    if isinstance(data, list):
        return True, data
    if isinstance(data, dict) and isinstance(data.get("data"), list):
        return True, data["data"]
    return True, data if isinstance(data, list) else []


def _submit_urllib(payload: dict, timeout: float) -> tuple[bool, str]:
    status, raw = post_urllib(HIGHSCORES_URL, json.dumps(payload).encode("utf-8"), timeout)
    if 200 <= status < 300:
        return True, "Score submitted!"
    if status <= 0:
        return False, raw or "Network error"
    try:
        data = json.loads(raw) if raw else {}
        message = data.get("message") or data.get("error") or raw
    except json.JSONDecodeError:
        message = raw or "unknown"
    return False, f"Submit failed ({status}): {message}"


def _fetch_urllib(url: str, timeout: float) -> tuple[bool, list | str]:
    status, raw = get_urllib(url, timeout)
    if status <= 0:
        return False, raw or "Network error"
    if not (200 <= status < 300):
        return False, f"Fetch failed ({status}): {raw or 'unknown'}"
    return _parse_leaderboard_payload(raw)


async def submit_highscore(
    name: str,
    height: float,
    pilot_id: int | str,
    rocket: dict,
    top_speed: float | None = None,
    secret: str | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> tuple[bool, str]:
    """
    Sign and POST a highscore (with pilot + rocket composition).
    Returns (ok, message).
    """
    secret = (secret if secret is not None else get_hmac_secret()).strip()
    if not secret or secret == "replace-with-shared-secret":
        return False, "Set HIGHSCORE_HMAC_SECRET in config.local.py"

    try:
        payload = sign_highscore(
            name,
            height,
            secret,
            pilot_id=pilot_id,
            rocket=rocket,
            top_speed=top_speed,
        )
    except ValueError as exc:
        return False, str(exc)

    if _IS_WEB:
        try:
            status, raw = await web_http("POST", HIGHSCORES_URL, json.dumps(payload))
        except Exception as exc:
            return False, f"Network error: {exc}"
        if 200 <= status < 300:
            return True, "Score submitted!"
        try:
            data = json.loads(raw) if raw else {}
            message = data.get("message") or data.get("error") or raw
        except json.JSONDecodeError:
            message = raw or "unknown"
        if status <= 0:
            return False, f"Network error: {message}"
        return False, f"Submit failed ({status}): {message}"

    return _submit_urllib(payload, timeout)


async def fetch_highscores(
    limit: int = 10,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> tuple[bool, list | str]:
    """GET public leaderboard. Returns (ok, rows_or_error_message)."""
    url = f"{HIGHSCORES_URL}?limit={max(1, min(int(limit), 100))}"

    if _IS_WEB:
        try:
            status, raw = await web_http("GET", url)
        except Exception as exc:
            return False, f"Network error: {exc}"
        if status <= 0:
            return False, f"Network error: {raw or 'request failed'}"
        if not (200 <= status < 300):
            return False, f"Fetch failed ({status}): {raw or 'unknown'}"
        return _parse_leaderboard_payload(raw)

    return _fetch_urllib(url, timeout)
