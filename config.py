"""Public game configuration (safe to commit)."""

import importlib.util
from pathlib import Path

HIGHSCORE_API_BASE = "https://joakim.lt"

# Real secret lives in gitignored config.local.py (see config.local.example.py).
HIGHSCORE_HMAC_SECRET = ""

_local_path = Path(__file__).with_name("config.local.py")
if _local_path.is_file():
    _spec = importlib.util.spec_from_file_location("game_config_local", _local_path)
    if _spec and _spec.loader:
        _module = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_module)
        HIGHSCORE_HMAC_SECRET = getattr(
            _module, "HIGHSCORE_HMAC_SECRET", HIGHSCORE_HMAC_SECRET
        )
        HIGHSCORE_API_BASE = getattr(_module, "HIGHSCORE_API_BASE", HIGHSCORE_API_BASE)
