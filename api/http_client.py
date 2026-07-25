"""Shared JSON HTTP helpers for desktop (urllib) and web (pygbag fetch)."""

import json
import sys
import urllib.error
import urllib.request

DEFAULT_TIMEOUT_SECONDS = 10

_IS_WEB = sys.platform == "emscripten"
_WEB_FETCH_READY = False

_WEB_FETCH_JS = """
window.GameApiFetch = {
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


def _ensure_web_fetch() -> None:
    global _WEB_FETCH_READY
    if _WEB_FETCH_READY:
        return
    import platform

    platform.window.eval(_WEB_FETCH_JS)
    _WEB_FETCH_READY = True


async def web_http(method: str, url: str, body: str | None = None) -> tuple[int, str]:
    import platform

    _ensure_web_fetch()
    if method == "GET":
        raw = await platform.jsiter(platform.window.GameApiFetch.GET(url))
    else:
        raw = await platform.jsiter(platform.window.GameApiFetch.POST(url, body or "{}"))
    data = json.loads(raw)
    return int(data.get("status") or 0), str(data.get("body") or "")


def get_urllib(url: str, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> tuple[int, str]:
    request = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return exc.code, detail or str(exc.reason)
    except urllib.error.URLError as exc:
        return 0, f"Network error: {exc.reason}"
    except TimeoutError:
        return 0, "Request timed out"


def post_urllib(
    url: str,
    body: bytes,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> tuple[int, str]:
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return exc.code, detail or str(exc.reason)
    except urllib.error.URLError as exc:
        return 0, f"Network error: {exc.reason}"
    except TimeoutError:
        return 0, "Request timed out"


async def get_json(
    url: str,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> tuple[bool, dict | list | str]:
    """GET JSON. Returns (ok, parsed_data_or_error_message)."""
    if _IS_WEB:
        try:
            status, raw = await web_http("GET", url)
        except Exception as exc:
            return False, f"Network error: {exc}"
    else:
        status, raw = get_urllib(url, timeout)

    if status <= 0:
        return False, raw or "request failed"
    if not (200 <= status < 300):
        return False, f"Fetch failed ({status}): {raw or 'unknown'}"

    try:
        return True, json.loads(raw)
    except json.JSONDecodeError:
        return False, "Invalid JSON from API"
