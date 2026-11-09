"""SQLite storage for CyberGuard.

Stores genuine Suricata alert events (read from EVE JSON) and the incremental
ingestion state (file inode + byte offset). All SQL is parameterized. Python
never decides what is an alert — it only persists what Suricata reported.
"""

import sqlite3
from pathlib import Path

# --- Schema ---------------------------------------------------------------

ALERTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS alerts (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp_raw     TEXT,
    timestamp_utc     TEXT,
    flow_id           INTEGER,
    src_ip            TEXT,
    src_port          INTEGER,
    dest_ip           TEXT,
    dest_port         INTEGER,
    proto             TEXT,
    app_proto         TEXT,
    signature         TEXT,
    signature_id      INTEGER,
    severity          INTEGER,
    category          TEXT,
    action            TEXT,
    http_url          TEXT,
    http_method       TEXT,
    http_hostname     TEXT,
    http_status       INTEGER,
    http_user_agent   TEXT,
    in_iface          TEXT,
    raw_json          TEXT,
    ingested_at       TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (flow_id, timestamp_raw, signature_id)
);
"""

# Single-row table (id = 1) tracking incremental EVE JSON read position.
INGEST_STATE_SCHEMA = """
CREATE TABLE IF NOT EXISTS ingest_state (
    id                     INTEGER PRIMARY KEY CHECK (id = 1),
    inode                  INTEGER DEFAULT 0,
    byte_offset            INTEGER DEFAULT 0,
    invalid_lines_count    INTEGER DEFAULT 0,
    last_event_timestamp   TEXT,
    last_alert_ingested_at TEXT
);
"""

INDEXES = (
    "CREATE INDEX IF NOT EXISTS idx_alerts_timestamp_utc ON alerts (timestamp_utc);",
    "CREATE INDEX IF NOT EXISTS idx_alerts_signature_id ON alerts (signature_id);",
    "CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts (severity);",
    "CREATE INDEX IF NOT EXISTS idx_alerts_src_ip ON alerts (src_ip);",
)

# Columns accepted by insert_alert (parameterized, fixed order).
_ALERT_COLUMNS = (
    "timestamp_raw", "timestamp_utc", "flow_id",
    "src_ip", "src_port", "dest_ip", "dest_port",
    "proto", "app_proto", "signature", "signature_id",
    "severity", "category", "action",
    "http_url", "http_method", "http_hostname", "http_status", "http_user_agent",
    "in_iface", "raw_json",
)

_INGEST_STATE_COLUMNS = (
    "inode", "byte_offset", "invalid_lines_count",
    "last_event_timestamp", "last_alert_ingested_at",
)


# --- Connection / init ----------------------------------------------------

def get_connection(db_path):
    """Open a SQLite connection, creating parent directories if needed."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path):
    """Create tables, indexes, and the single ingest_state row if missing."""
    conn = get_connection(db_path)
    try:
        conn.execute(ALERTS_SCHEMA)
        conn.execute(INGEST_STATE_SCHEMA)
        for stmt in INDEXES:
            conn.execute(stmt)
        conn.execute("INSERT OR IGNORE INTO ingest_state (id) VALUES (1);")
        conn.commit()
    finally:
        conn.close()


# --- Alerts ---------------------------------------------------------------

def insert_alert(conn, record):
    """INSERT OR IGNORE a single alert record (dict). Returns rows inserted
    (1 if new, 0 if a duplicate was ignored). Caller commits."""
    placeholders = ", ".join("?" for _ in _ALERT_COLUMNS)
    columns = ", ".join(_ALERT_COLUMNS)
    values = [record.get(col) for col in _ALERT_COLUMNS]
    cur = conn.execute(
        f"INSERT OR IGNORE INTO alerts ({columns}) VALUES ({placeholders})",
        values,
    )
    return cur.rowcount


def count_alerts(db_path):
    """Return the total number of stored alerts."""
    conn = get_connection(db_path)
    try:
        cur = conn.execute("SELECT COUNT(*) AS c FROM alerts")
        return cur.fetchone()["c"]
    finally:
        conn.close()


def query_alerts(db_path, filters=None, limit=50, offset=0):
    """Return alert rows (newest first) matching ``filters``.

    Supported filter keys: severity, signature_id, signature (substring),
    src_ip (exact), q (substring across signature/url/ips), date_from,
    date_to (both UTC strings compared against timestamp_utc). All SQL is
    parameterized.
    """
    filters = filters or {}
    where = []
    params = []

    if filters.get("severity") is not None:
        where.append("severity = ?")
        params.append(int(filters["severity"]))
    if filters.get("signature_id") is not None:
        where.append("signature_id = ?")
        params.append(int(filters["signature_id"]))
    if filters.get("signature"):
        where.append("signature LIKE ?")
        params.append(f"%{filters['signature']}%")
    if filters.get("src_ip"):
        where.append("src_ip = ?")
        params.append(filters["src_ip"])
    if filters.get("q"):
        like = f"%{filters['q']}%"
        where.append(
            "(signature LIKE ? OR http_url LIKE ? OR src_ip LIKE ? OR dest_ip LIKE ?)"
        )
        params.extend([like, like, like, like])
    if filters.get("date_from"):
        where.append("timestamp_utc >= ?")
        params.append(filters["date_from"])
    if filters.get("date_to"):
        where.append("timestamp_utc <= ?")
        params.append(filters["date_to"])

    sql = "SELECT * FROM alerts"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY timestamp_utc DESC, id DESC LIMIT ? OFFSET ?"
    params.extend([int(limit), int(offset)])

    conn = get_connection(db_path)
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_stats(db_path, since_utc=None):
    """Return aggregate statistics. ``since_utc`` (a UTC string) bounds the
    last-24h count; if None it is reported as None."""
    conn = get_connection(db_path)
    try:
        total = conn.execute("SELECT COUNT(*) AS c FROM alerts").fetchone()["c"]

        by_severity = {
            str(r["severity"]): r["c"]
            for r in conn.execute(
                "SELECT severity, COUNT(*) AS c FROM alerts GROUP BY severity"
            )
        }
        by_signature = {
            r["signature"]: r["c"]
            for r in conn.execute(
                "SELECT signature, COUNT(*) AS c FROM alerts "
                "GROUP BY signature ORDER BY c DESC"
            )
        }
        by_src_ip = {
            r["src_ip"]: r["c"]
            for r in conn.execute(
                "SELECT src_ip, COUNT(*) AS c FROM alerts "
                "GROUP BY src_ip ORDER BY c DESC"
            )
        }

        last_24h = None
        if since_utc is not None:
            last_24h = conn.execute(
                "SELECT COUNT(*) AS c FROM alerts WHERE timestamp_utc >= ?",
                [since_utc],
            ).fetchone()["c"]

        return {
            "total": total,
            "by_severity": by_severity,
            "by_signature": by_signature,
            "by_src_ip": by_src_ip,
            "last_24h": last_24h,
        }
    finally:
        conn.close()


# --- Ingest state ---------------------------------------------------------

def get_ingest_state(db_path):
    """Return the single ingest_state row as a dict (creates it if missing)."""
    conn = get_connection(db_path)
    try:
        conn.execute("INSERT OR IGNORE INTO ingest_state (id) VALUES (1);")
        conn.commit()
        row = conn.execute("SELECT * FROM ingest_state WHERE id = 1").fetchone()
        return dict(row)
    finally:
        conn.close()


def update_ingest_state(db_path, **fields):
    """Update whitelisted ingest_state columns (parameterized)."""
    updates = {k: v for k, v in fields.items() if k in _INGEST_STATE_COLUMNS}
    if not updates:
        return
    set_clause = ", ".join(f"{col} = ?" for col in updates)
    params = list(updates.values())
    conn = get_connection(db_path)
    try:
        conn.execute("INSERT OR IGNORE INTO ingest_state (id) VALUES (1);")
        conn.execute(f"UPDATE ingest_state SET {set_clause} WHERE id = 1", params)
        conn.commit()
    finally:
        conn.close()
