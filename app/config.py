"""Environment-based configuration for CyberGuard.

Values are read from environment variables (optionally loaded from a local
``.env`` file). Nothing machine-specific or secret is hardcoded — defaults are
project-relative and safe for local development.
"""

import os
from pathlib import Path

# Load variables from a local .env file if python-dotenv is available.
# The app still runs if python-dotenv is not installed.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover - optional dependency
    pass

# Project root (two levels up from this file: app/config.py -> project root).
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


def _env(key, default):
    """Return an environment variable or a default."""
    value = os.environ.get(key)
    return value if value not in (None, "") else default


class Config:
    """Runtime configuration, sourced from the environment."""

    # --- Flask ---
    FLASK_ENV = _env("FLASK_ENV", "development")
    HOST = _env("FLASK_HOST", "127.0.0.1")
    PORT = int(_env("FLASK_PORT", "5000"))
    SECRET_KEY = _env("FLASK_SECRET_KEY", "dev-insecure-change-me")
    DEBUG = FLASK_ENV == "development"

    # --- Suricata / data paths ---
    # Default EVE JSON path is project-local for cross-platform dev. On the
    # Linux engine host this is overridden via .env, e.g.
    # /var/log/suricata/eve.json
    EVE_JSON_PATH = _env("EVE_JSON_PATH", str(DATA_DIR / "eve.json"))
    SQLITE_DB_PATH = _env("SQLITE_DB_PATH", str(DATA_DIR / "cyberguard.db"))

    # --- Telegram (optional, final phase) ---
    TELEGRAM_BOT_TOKEN = _env("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = _env("TELEGRAM_CHAT_ID", "")
