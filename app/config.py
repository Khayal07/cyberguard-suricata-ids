"""Environment-based configuration for CyberGuard.

Values are read from environment variables (optionally loaded from a local
``.env`` file). Nothing machine-specific or secret is hardcoded — defaults are
safe and the Suricata/EVE paths match the Kali VM layout.
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
    """Return an environment variable or a default (treats "" as unset)."""
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
    TESTING = False

    # --- Suricata EVE JSON integration ---
    # EVE path defaults to the Kali VM location; override via env on other hosts.
    EVE_PATH = _env("CYBERGUARD_EVE_PATH", "/var/log/suricata/eve.json")
    # Suricata pidfile + the /proc base used to verify the process (Linux only).
    SURICATA_PID_PATH = _env("CYBERGUARD_SURICATA_PID", "/tmp/suricata.pid")
    PROC_BASE = _env("CYBERGUARD_PROC_BASE", "/proc")
    # Suricata rules file shown (read-only) by the Rule Lab. Fixed path, never
    # taken from a request. Defaults to the Kali VM's deployed rules location.
    RULES_PATH = _env(
        "CYBERGUARD_RULES_PATH", "/var/lib/suricata/rules/cyberguard.rules"
    )
    # SQLite database (git-ignored). Default lives under the project data/ dir.
    DB_PATH = _env("CYBERGUARD_DB_PATH", str(DATA_DIR / "cyberguard.db"))
    # Background ingestion poll interval (seconds).
    POLL_SECONDS = float(_env("CYBERGUARD_POLL_SECONDS", "2"))

    # --- Telegram notifications (OPTIONAL) ---
    # No secret is ever hardcoded; everything comes from the environment. The
    # feature is ENABLED only when BOTH token and chat id are set (see below).
    TELEGRAM_TOKEN = _env("CYBERGUARD_TELEGRAM_TOKEN", "")
    TELEGRAM_CHAT_ID = _env("CYBERGUARD_TELEGRAM_CHAT_ID", "")
    # Notify only when an alert's severity is <= this threshold (1 = most severe,
    # so a smaller number means fewer, more serious alerts). Default 3.
    TELEGRAM_MIN_SEVERITY = int(_env("CYBERGUARD_TELEGRAM_MIN_SEVERITY", "3"))
    # Max Telegram messages per rolling minute; anything beyond this is collapsed
    # into ONE summary message instead of being sent individually. Default 5.
    TELEGRAM_RATE_PER_MIN = int(_env("CYBERGUARD_TELEGRAM_RATE_PER_MIN", "5"))
    # Derived: on only when both the token and the chat id are present.
    TELEGRAM_ENABLED = bool(TELEGRAM_TOKEN and TELEGRAM_CHAT_ID)
