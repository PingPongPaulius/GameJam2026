"""Copy to config.local.py and fill in the real secret.

config.local.py is gitignored and should never be pushed.
Include it when packaging the game for distribution.
"""

HIGHSCORE_HMAC_SECRET = "replace-with-shared-secret"
