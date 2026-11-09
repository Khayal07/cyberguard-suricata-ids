"""Shared pytest fixtures/helpers for CyberGuard backend tests.

All tests run on Windows with no Suricata installed: they use temporary SQLite
databases and temporary EVE files, and inject a fake /proc for process checks.
"""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

FIXTURE_FILE = Path(__file__).parent / "fixtures" / "eve_alerts_sample.jsonl"
# The two REAL Suricata alert lines (raw, no trailing newline), in order.
RAW_LINES = FIXTURE_FILE.read_text(encoding="utf-8").splitlines()
LINE1, LINE2 = RAW_LINES[0], RAW_LINES[1]

# A non-alert EVE event (must be ignored by the reader — never a "threat").
STATS_EVENT = json.dumps(
    {
        "timestamp": "2026-11-09T09:46:30.000000-0500",
        "event_type": "stats",
        "stats": {"uptime": 10},
    }
)


def make_config(tmp_path, **overrides):
    """Build a lightweight config object for tests."""
    cfg = SimpleNamespace(
        DB_PATH=str(tmp_path / "cyberguard.db"),
        EVE_PATH=str(tmp_path / "eve.json"),
        SURICATA_PID_PATH=str(tmp_path / "suricata.pid"),
        PROC_BASE=str(tmp_path / "no_proc"),  # does not exist -> "unverified"
        POLL_SECONDS=0.01,
        SECRET_KEY="test",
        DEBUG=False,
        TESTING=True,
    )
    for key, value in overrides.items():
        setattr(cfg, key, value)
    return cfg


@pytest.fixture
def config(tmp_path):
    from app.services import database

    cfg = make_config(tmp_path)
    database.init_db(cfg.DB_PATH)
    return cfg


def write_eve(cfg, *lines, trailing_newline=True):
    """Write EVE lines to the config's EVE_PATH using real LF endings.

    Uses write_bytes so Windows text-mode translation never turns \\n into
    \\r\\n — this mirrors the LF-only output real Suricata writes on Linux.
    """
    data = "\n".join(lines)
    if trailing_newline and lines:
        data += "\n"
    Path(cfg.EVE_PATH).write_bytes(data.encode("utf-8"))
