import hashlib
import hmac
import json
import secrets
import sys
import time
import urllib.error
import urllib.request

from config import HIGHSCORE_API_BASE, HIGHSCORE_HMAC_SECRET

API_BASE = HIGHSCORE_API_BASE.rstrip("/")
HIGHSCORES_URL = f"{API_BASE}/api/highscores"
DEFAULT_TIMEOUT_SECONDS = 10

_IS_WEB = sys.platform == "emscripten"
_WEB_FETCH_READY = False

_WEB_FETCH_JS = """
window.HighscoreFetch = {
  GET: function * GET(url) {
    var content = null;
    var error = null;
    var done = false;
    fetch(url, { method: 'GET', headers: { 'Accept': 'application/json' } })
      .then(function(resp) {
        return resp.text().then(function(text) {
          content = JSON.stringify({ status: resp.status, body: text });
          done = true;
        });
      })
      .catch(function(err) {
        error = String(err);
        done = true;
      });
    while (!done) { yield; }
    yield error ? JSON.stringify({ status: 0, body: error }) : content;
  },
  POST: function * POST(url, body) {
    var content = null;
    var error = null;
    var done = false;
    fetch(url, {
      method: 'POST',
      headers: { 'Accept': 'application/json', 'Content-Type': 'application/json' },
      body: body
    })
      .then(function(resp) {
        return resp.text().then(function(text) {
          content = JSON.stringify({ status: resp.status, body: text });
          done = true;
        });
      })
      .catch(function(err) {
        error = String(err);
        done = true;
      });
    while (!done) { yield; }
    yield error ? JSON.stringify({ status: 0, body: error }) : content;
  }
};
"""


def get_hmac_secret() -> str:
    return (HIGHSCORE_HMAC_SECRET or "").strip()


def format_number(value: float | int) -> str:
    formatted = f"{float(value):.6f}".rstrip("0").rstrip(".")
    return "0" if formatted == "-0" else formatted


def sign_highscore(
    name: str,
    height: float,
    secret: str,
    top_speed: float | None = None,
) -> dict:
    timestamp = int(time.time())
    nonce = secrets.token_hex(16)
    top = "" if top_speed is None else format_number(top_speed)
    canonical = (
        f"name={name}"
        f"&height={format_number(height)}"
        f"&top_speed={top}"
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
        "timestamp": timestamp,
        "nonce": nonce,
        "signature": signature,
    }
    if top_speed is not None:
        payload["top_speed"] = top_speed
    return payload


def _ensure_web_fetch() -> None:
    global _WEB_FETCH_READY
    if _WEB_FETCH_READY:
        return
    import platform

    platform.window.eval(_WEB_FETCH_JS)
    _WEB_FETCH_READY = True


async def _web_http(method: str, url: str, body: str | None = None) -> tuple[int, str]:
    import platform

    _ensure_web_fetch()
    if method == "GET":
        raw = await platform.jsiter(platform.window.HighscoreFetch.GET(url))
    else:
        raw = await platform.jsiter(platform.window.HighscoreFetch.POST(url, body or "{}"))
    data = json.loads(raw)
    return int(data.get("status") or 0), str(data.get("body") or "")


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
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        HIGHSCORES_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            if 200 <= response.status < 300:
                return True, "Score submitted!"
            return False, f"API error ({response.status}): {raw or 'unknown'}"
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(detail) if detail else {}
            message = data.get("message") or data.get("error") or detail
        except json.JSONDecodeError:
            message = detail or exc.reason
        return False, f"Submit failed ({exc.code}): {message}"
    except urllib.error.URLError as exc:
        return False, f"Network error: {exc.reason}"
    except TimeoutError:
        return False, "Request timed out"


def _fetch_urllib(url: str, timeout: float) -> tuple[bool, list | str]:
    request = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return _parse_leaderboard_payload(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return False, f"Fetch failed ({exc.code}): {detail or exc.reason}"
    except urllib.error.URLError as exc:
        return False, f"Network error: {exc.reason}"
    except TimeoutError:
        return False, "Request timed out"


async def submit_highscore(
    name: str,
    height: float,
    top_speed: float | None = None,
    secret: str | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> tuple[bool, str]:
    """
    Sign and POST a highscore.
    Returns (ok, message).
    """
    secret = (secret if secret is not None else get_hmac_secret()).strip()
    if not secret or secret == "replace-with-shared-secret":
        return False, "Set HIGHSCORE_HMAC_SECRET in config.local.py"

    payload = sign_highscore(name, height, secret, top_speed=top_speed)

    if _IS_WEB:
        try:
            status, raw = await _web_http("POST", HIGHSCORES_URL, json.dumps(payload))
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
            status, raw = await _web_http("GET", url)
        except Exception as exc:
            return False, f"Network error: {exc}"
        if status <= 0:
            return False, f"Network error: {raw or 'request failed'}"
        if not (200 <= status < 300):
            return False, f"Fetch failed ({status}): {raw or 'unknown'}"
        return _parse_leaderboard_payload(raw)

    return _fetch_urllib(url, timeout)
