"""Alert service: normalize, store, and serve genuine Suricata alerts.

This module orchestrates ingestion (read EVE JSON -> normalize -> store),
answers API queries/stats, and reports honest status. It performs NO detection:
every alert originates from Suricata; Python only processes what Suricata wrote.
"""

import logging
import os
import re
import threading
from datetime import datetime, timedelta, timezone

from app.services import database, eve_reader, telegram_notifier

logger = logging.getLogger("cyberguard.alert_service")

# Fixed-width UTC string so lexical comparison works for date-range filters.
_UTC_SUFFIX = "+00:00"
_TZ_NO_COLON = re.compile(r"([+-]\d{2})(\d{2})$")


# --- Timestamp normalization ----------------------------------------------

def normalize_timestamp(raw):
    """Return (raw, utc_string) for a Suricata timestamp.

    Suricata emits offsets without a colon (e.g. ``-0500``); we normalize to
    ``-05:00`` so ``datetime.fromisoformat`` works on any Python 3.x. Returns
    ``(raw, None)`` if parsing fails — never raises.
    """
    if not raw:
        return raw, None
    candidate = _TZ_NO_COLON.sub(r"\1:\2", raw)
    try:
        dt = datetime.fromisoformat(candidate)
    except ValueError:
        return raw, None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    utc = dt.astimezone(timezone.utc)
    return raw, utc.strftime("%Y-%m-%dT%H:%M:%S.%f") + _UTC_SUFFIX


def _now_utc_string(now=None):
    now = now or datetime.now(timezone.utc)
    return now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f") + _UTC_SUFFIX


def to_db_record(extracted):
    """Add raw/UTC timestamp fields to an extracted alert dict for storage."""
    raw_ts, utc_ts = normalize_timestamp(extracted.get("timestamp"))
    record = dict(extracted)
    record["timestamp_raw"] = raw_ts
    record["timestamp_utc"] = utc_ts
    return record


# --- Ingestion ------------------------------------------------------------

def ingest(config, on_inserted=None):
    """Read new EVE alerts and store them. Returns a summary dict.

    Deduplication is twofold: the persisted read offset avoids re-reading old
    bytes, and the DB UNIQUE constraint ignores duplicate alert rows. Re-reading
    the same file therefore never creates duplicates.

    ``on_inserted``, if given, is called once AFTER commit with the list of
    records that were genuinely inserted this cycle (never duplicates). The
    one-shot CLI passes nothing, so it never notifies; only the background
    worker wires this to Telegram.
    """
    result = eve_reader.read_new_alerts(config.DB_PATH, config.EVE_PATH)

    if result["status"] == "eve_missing":
        return {
            "status": "eve_missing",
            "read": 0,
            "inserted": 0,
            "duplicates": 0,
            "invalid_lines": result["invalid_lines"],
        }

    inserted = 0
    duplicates = 0
    inserted_records = []
    conn = database.get_connection(config.DB_PATH)
    try:
        for extracted in result["alerts"]:
            record = to_db_record(extracted)
            if database.insert_alert(conn, record):
                inserted += 1
                inserted_records.append(record)
            else:
                duplicates += 1
        conn.commit()
    finally:
        conn.close()

    if inserted:
        database.update_ingest_state(
            config.DB_PATH, last_alert_ingested_at=_now_utc_string()
        )

    if on_inserted and inserted_records:
        on_inserted(inserted_records)

    return {
        "status": "ok",
        "read": len(result["alerts"]),
        "inserted": inserted,
        "duplicates": duplicates,
        "invalid_lines": result["invalid_lines"],
        "rotated": result["rotated"],
    }


# --- Queries / stats for the API ------------------------------------------

def _format_alert(row):
    """Shape a DB row for the API. Empty category is shown as 'uncategorized'
    (the raw empty value remains stored in the DB)."""
    out = dict(row)
    out.pop("raw_json", None)  # keep API responses lean; raw stays in the DB
    if not out.get("category"):
        out["category"] = "uncategorized"
    return out


def list_alerts(config, filters=None, limit=50, offset=0):
    """Return formatted alerts (newest first) for the API."""
    limit = max(1, min(int(limit), 500))
    offset = max(0, int(offset))
    rows = database.query_alerts(config.DB_PATH, filters, limit, offset)
    return {
        "alerts": [_format_alert(r) for r in rows],
        "count": len(rows),
        "limit": limit,
        "offset": offset,
    }


def build_filters(args):
    """Build a validated filter dict from request args (a mapping).

    Dates (from/to) are normalized to the stored UTC format so comparisons are
    correct. Unparseable values are ignored rather than raising.
    """
    filters = {}
    if args.get("severity") not in (None, ""):
        try:
            filters["severity"] = int(args.get("severity"))
        except (TypeError, ValueError):
            pass
    if args.get("signature_id") not in (None, ""):
        try:
            filters["signature_id"] = int(args.get("signature_id"))
        except (TypeError, ValueError):
            pass
    if args.get("signature"):
        filters["signature"] = args.get("signature")
    if args.get("src_ip"):
        filters["src_ip"] = args.get("src_ip")
    if args.get("q"):
        filters["q"] = args.get("q")
    if args.get("from"):
        _, utc = normalize_timestamp(args.get("from"))
        if utc:
            filters["date_from"] = utc
    if args.get("to"):
        _, utc = normalize_timestamp(args.get("to"))
        if utc:
            filters["date_to"] = utc
    return filters


def get_stats(config, now=None):
    """Return alert statistics, including a last-24h count."""
    since = _now_utc_string((now or datetime.now(timezone.utc)) - timedelta(hours=24))
    return database.get_stats(config.DB_PATH, since_utc=since)


# --- Suricata process status (no shell, no subprocess) --------------------

def check_suricata_process(pid_path, proc_base="/proc"):
    """Verify whether Suricata is running by reading the pidfile and
    ``/proc/<pid>/comm`` — no shell, no subprocess.

    Returns "verified_running", "verified_not_running", or "unverified".
    On a host without /proc (e.g. Windows) returns "unverified". Never reports
    running based on eve.json existence.
    """
    if not os.path.isdir(proc_base):
        return "unverified"
    try:
        with open(pid_path, "r", encoding="utf-8") as handle:
            pid = int(handle.read().strip())
    except (OSError, ValueError):
        return "verified_not_running"

    comm_path = os.path.join(proc_base, str(pid), "comm")
    try:
        with open(comm_path, "r", encoding="utf-8") as handle:
            comm = handle.read().strip()
    except OSError:
        return "verified_not_running"

    return "verified_running" if "Suricata" in comm else "verified_not_running"


def get_status(config, proc_base=None):
    """Return an honest status report (see /api/status)."""
    state = database.get_ingest_state(config.DB_PATH)
    eve_exists = os.path.exists(config.EVE_PATH)
    suricata_process = check_suricata_process(
        config.SURICATA_PID_PATH, proc_base or getattr(config, "PROC_BASE", "/proc")
    )
    status = {
        "backend_running": True,
        "detection_engine": "suricata",
        "eve_path": config.EVE_PATH,
        "eve_file_exists": eve_exists,
        "suricata_process": suricata_process,
        "last_event_timestamp": state.get("last_event_timestamp"),
        "last_alert_ingested_at": state.get("last_alert_ingested_at"),
        "invalid_lines_count": state.get("invalid_lines_count") or 0,
        "total_alerts": database.count_alerts(config.DB_PATH),
    }
    # Telegram fields never include the token or chat id.
    status.update(telegram_notifier.status_fields(config))
    return status


# --- Background ingestion worker ------------------------------------------

class IngestionWorker:
    """Daemon thread that polls EVE JSON every ``POLL_SECONDS`` and ingests.

    Guards against being started twice and shuts down cleanly via an Event.
    An optional ``notifier`` (Telegram) is fed ONLY the alerts inserted in each
    cycle. The FIRST cycle is treated as a baseline: any alerts already present
    in eve.json at startup are recorded for dedup but NOT sent, so starting the
    worker never floods Telegram with historical alerts.
    """

    def __init__(self, config, notifier=None):
        self.config = config
        self.notifier = notifier
        self._stop = threading.Event()
        self._thread = None
        self._lock = threading.Lock()
        self._baseline_done = False

    def start(self):
        with self._lock:
            if self._thread and self._thread.is_alive():
                return  # already running — never start a second thread
            self._stop.clear()
            self._thread = threading.Thread(
                target=self._run, name="cyberguard-ingest", daemon=True
            )
            self._thread.start()
            logger.info("Ingestion worker started (poll=%ss)", self.config.POLL_SECONDS)

    def poll_once(self):
        """Run one ingest cycle and notify for genuinely new alerts.

        On the first invocation, newly-read alerts are a baseline: their dedup
        keys are recorded but no Telegram message is sent (no startup flood).
        """
        inserted = []
        ingest(self.config, on_inserted=inserted.extend)
        if self.notifier is not None:
            if self._baseline_done:
                self.notifier.notify_new_alerts(inserted)
            else:
                self.notifier.mark_seen(inserted)
        self._baseline_done = True

    def _run(self):
        while not self._stop.is_set():
            try:
                self.poll_once()
            except Exception:  # never let the worker die on a bad cycle
                logger.exception("Ingestion cycle failed")
            self._stop.wait(self.config.POLL_SECONDS)

    def stop(self):
        self._stop.set()
        thread = self._thread
        if thread:
            thread.join(timeout=5)
        if self.notifier is not None:
            self.notifier.stop()
        logger.info("Ingestion worker stopped")
