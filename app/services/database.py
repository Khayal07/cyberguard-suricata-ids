"""SQLite storage for CyberGuard.

Provides a connection helper and schema initialisation. The ``alerts`` table
stores genuine Suricata alert events (populated in a later phase). It is empty
until Suricata-generated events are ingested.
"""

import sqlite3
from pathlib import Path

# Schema for genuine Suricata alert events. Columns mirror common EVE JSON
# alert fields so events can be stored faithfully in a later phase.
ALERTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS alerts (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp      TEXT,
    signature      TEXT,
    signature_id   INTEGER,
    category       TEXT,
    severity       INTEGER,
    src_ip         TEXT,
    src_port       INTEGER,
    dest_ip        TEXT,
    dest_port      INTEGER,
    protocol       TEXT,
    raw_json       TEXT,
    created_at     TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


def get_connection(db_path):
    """Open a SQLite connection, creating parent directories if needed."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path):
    """Create the schema if it does not already exist."""
    conn = get_connection(db_path)
    try:
        conn.execute(ALERTS_SCHEMA)
        conn.commit()
    finally:
        conn.close()


def count_alerts(db_path):
    """Return the number of stored alerts (0 if the table/file is new)."""
    conn = get_connection(db_path)
    try:
        cursor = conn.execute("SELECT COUNT(*) AS count FROM alerts")
        return cursor.fetchone()["count"]
    finally:
        conn.close()
