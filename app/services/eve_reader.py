"""Incremental reader for Suricata EVE JSON.

Reads newline-delimited JSON from Suricata's EVE output, resuming from a
persisted position (file inode + byte offset stored in SQLite). It ONLY surfaces
``event_type == "alert"`` events; stats/flow/http and other event types are
ignored and never treated as threats. This module reads and extracts — it never
inspects packets, classifies traffic, or generates alerts.

Robustness guarantees:
- Missing file            -> status "eve_missing", no crash.
- Invalid JSON line       -> counted, warned, skipped (never crashes).
- Partial last line       -> not consumed (offset stops before it).
- Truncation / rotation   -> inode change or size < offset restarts from 0.
- Suricata stopped        -> file present, no new lines, returns no alerts.
"""

import json
import logging
import os

from app.services import database

logger = logging.getLogger("cyberguard.eve_reader")


def extract_alert_fields(event, raw_line):
    """Map a Suricata alert event dict to the fields CyberGuard stores.

    Keeps the original line as ``raw_json`` to preserve the genuine detection.
    Uses ``.get`` throughout so missing optional fields never raise.
    """
    alert = event.get("alert") or {}
    http = event.get("http") or {}
    return {
        "timestamp": event.get("timestamp"),
        "event_type": event.get("event_type"),
        "flow_id": event.get("flow_id"),
        "src_ip": event.get("src_ip"),
        "src_port": event.get("src_port"),
        "dest_ip": event.get("dest_ip"),
        "dest_port": event.get("dest_port"),
        "proto": event.get("proto"),
        "app_proto": event.get("app_proto"),
        "signature": alert.get("signature"),
        "signature_id": alert.get("signature_id"),
        "severity": alert.get("severity"),
        "category": alert.get("category"),
        "action": alert.get("action"),
        "http_url": http.get("url"),
        "http_method": http.get("http_method"),
        "http_hostname": http.get("hostname"),
        "http_status": http.get("status"),
        "http_user_agent": http.get("http_user_agent"),
        "in_iface": event.get("in_iface"),
        "raw_json": raw_line,
    }


def read_new_alerts(db_path, eve_path):
    """Read new EVE JSON lines since the last persisted position.

    Returns a dict:
        status                -> "ok" | "eve_missing"
        alerts                -> list of extracted alert dicts (event_type=alert)
        invalid_lines         -> invalid JSON lines seen in THIS read
        total_invalid_lines   -> cumulative invalid lines
        rotated               -> True if the file was truncated/rotated
        last_event_timestamp  -> timestamp of the last complete event seen
    The persisted position (inode, byte offset, invalid count,
    last_event_timestamp) is updated in SQLite.
    """
    state = database.get_ingest_state(db_path)

    if not os.path.exists(eve_path):
        return {
            "status": "eve_missing",
            "alerts": [],
            "invalid_lines": 0,
            "total_invalid_lines": state.get("invalid_lines_count") or 0,
            "rotated": False,
            "last_event_timestamp": state.get("last_event_timestamp"),
        }

    stat = os.stat(eve_path)
    inode = stat.st_ino
    size = stat.st_size

    offset = state.get("byte_offset") or 0
    stored_inode = state.get("inode") or 0

    # Detect rotation (inode changed) or truncation (file shorter than offset).
    rotated = False
    if stored_inode and inode and inode != stored_inode:
        rotated = True
        offset = 0
    if size < offset:
        rotated = True
        offset = 0

    # Read raw bytes from the offset so we can track byte position precisely and
    # avoid consuming a partial (not-yet-newline-terminated) final line.
    with open(eve_path, "rb") as handle:
        handle.seek(offset)
        chunk = handle.read()

    alerts = []
    invalid_new = 0
    last_ts = state.get("last_event_timestamp")

    if chunk:
        newline = chunk.rfind(b"\n")
        complete = chunk[: newline + 1] if newline != -1 else b""
        consumed = len(complete)

        for raw_bytes in complete.split(b"\n"):
            # Tolerate CRLF line endings (real Suricata uses LF; be robust).
            raw_bytes = raw_bytes.rstrip(b"\r")
            if not raw_bytes.strip():
                continue
            try:
                text = raw_bytes.decode("utf-8")
            except UnicodeDecodeError:
                invalid_new += 1
                logger.warning("Skipping EVE line with invalid UTF-8")
                continue
            try:
                event = json.loads(text)
            except (json.JSONDecodeError, ValueError):
                invalid_new += 1
                logger.warning("Skipping invalid EVE JSON line")
                continue

            ts = event.get("timestamp")
            if ts:
                last_ts = ts
            # Only alerts are surfaced. Everything else is intentionally ignored.
            if event.get("event_type") == "alert":
                alerts.append(extract_alert_fields(event, text))

        new_offset = offset + consumed
    else:
        new_offset = offset

    total_invalid = (state.get("invalid_lines_count") or 0) + invalid_new
    database.update_ingest_state(
        db_path,
        inode=inode,
        byte_offset=new_offset,
        invalid_lines_count=total_invalid,
        last_event_timestamp=last_ts,
    )

    return {
        "status": "ok",
        "alerts": alerts,
        "invalid_lines": invalid_new,
        "total_invalid_lines": total_invalid,
        "rotated": rotated,
        "last_event_timestamp": last_ts,
    }
