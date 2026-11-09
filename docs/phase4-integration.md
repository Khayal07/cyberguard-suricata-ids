# Phase 4 — Python Backend & Suricata EVE JSON Integration

> **Windows unit tests pass (34 passed); end-to-end validation on the Kali VM is
> pending.** This phase wires the Python backend to Suricata's real EVE JSON
> output. Suricata remains the only detection engine — Python only reads, stores,
> and serves what Suricata wrote.

---

## Data flow (beginner-friendly)

```
 Network traffic (lo)
        │
        ▼
 ┌──────────────┐  writes one JSON object per line
 │  SURICATA    │ ───────────────────────────────────►  /var/log/suricata/eve.json
 │ (detection)  │                                        (alerts + stats + flow + …)
 └──────────────┘
                                                               │  read incrementally
                                                               ▼
 ┌───────────────────────────────────────────────────────────────────────┐
 │ PYTHON BACKEND                                                          │
 │  eve_reader   → resume at saved (inode, byte offset); keep ONLY         │
 │                 event_type == "alert"; skip bad/partial lines safely    │
 │  alert_service→ normalize timestamp to UTC, dedupe, store, query, stats │
 │  database     → SQLite alerts table (UNIQUE flow_id,timestamp,sig_id)   │
 │  worker       → poll every CYBERGUARD_POLL_SECONDS (daemon thread)      │
 └───────────────────────────────────────────────────────────────────────┘
                                                               │  HTTP (localhost)
                                                               ▼
                                   Flask API  /api/health /api/status /api/alerts /api/stats
```

### Why Python does NOT detect
Detection logic lives entirely in Suricata rules. Python never inspects packets,
classifies traffic, or invents alerts. If Suricata is stopped, no new alerts are
produced — the backend simply has nothing new to read. Non-alert EVE events
(`stats`, `flow`, `http`, …) are intentionally ignored and can never become
"threats".

### How deduplication works
Two independent layers guarantee the same alert is never stored twice:
1. **Position tracking** — the reader stores the file inode + byte offset in
   SQLite and resumes from there, so old bytes are never re-read.
2. **UNIQUE constraint** — `UNIQUE(flow_id, timestamp_raw, signature_id)` with
   `INSERT OR IGNORE`. Even if the file is fully re-read, duplicates are ignored.

### How rotation / truncation is handled
- If the file's **inode changes** (log rotation) or its **size is smaller than
  the saved offset** (truncation), the reader restarts from offset 0.
- A **partial last line** (no trailing newline yet, because Suricata is mid-write)
  is never consumed; the offset stops before it and it is read once complete.
- **Missing file** → status `eve_missing` (no crash). **Suricata stopped** → the
  file is present but unchanged, so no new alerts and no crash.
- **Invalid JSON lines** are counted (`invalid_lines_count`), logged as a warning,
  and skipped.

### Real-world data notes
- `category` is an **empty string** and `severity` is `3` (the rules have no
  `classtype`). The empty value is **kept as-is in the DB**; the API/UI shows
  `"uncategorized"` for display only.
- Timestamps look like `2026-11-09T09:46:33.623977-0500` (offset **without** a
  colon). The backend normalizes `-0500` → `-05:00`, parses on any Python 3.x,
  and stores **both** the original string (`timestamp_raw`) and a UTC value
  (`timestamp_utc`).

---

## Suricata process status (no shell, no subprocess)

`/api/status` verifies Suricata by reading the pidfile (`/tmp/suricata.pid`) and
checking that `/proc/<pid>/comm` contains `Suricata`. It reports:

- `backend_running` — the Flask backend is up.
- `eve_file_exists` — whether the EVE file is present.
- `suricata_process` — `verified_running` | `verified_not_running` | `unverified`.
- `last_event_timestamp`, `last_alert_ingested_at`, `invalid_lines_count`,
  `total_alerts`.

It **never** reports Suricata as running just because `eve.json` exists. On a host
without `/proc` (e.g. Windows) it honestly reports `unverified`.

---

## API

| Method & path   | Purpose | Key query params |
|-----------------|---------|------------------|
| `GET /api/health` | Flask liveness (not the engine) | — |
| `GET /api/status` | Honest engine/backend status | — |
| `GET /api/alerts` | Stored alerts, newest first | `limit`, `offset`, `severity`, `signature_id`, `signature`, `src_ip`, `q`, `from`, `to` (ISO) |
| `GET /api/stats`  | Aggregates | — |

No endpoint executes commands or accepts filesystem paths.

### Example: `GET /api/alerts`
```json
{
  "alerts": [
    {
      "id": 2,
      "timestamp_raw": "2026-11-09T09:46:33.637590-0500",
      "timestamp_utc": "2026-11-09T14:46:33.637590+00:00",
      "flow_id": 483088496493388,
      "src_ip": "127.0.0.1", "src_port": 47000,
      "dest_ip": "127.0.0.1", "dest_port": 8000,
      "proto": "TCP", "app_proto": "http",
      "signature": "CyberGuard Warning Alert", "signature_id": 1000002,
      "severity": 3, "category": "uncategorized", "action": "allowed",
      "http_url": "/cyberguard-warning", "http_method": "GET",
      "http_hostname": "127.0.0.1", "http_status": 200,
      "http_user_agent": "curl/8.21.0", "in_iface": "lo"
    }
  ],
  "count": 1, "limit": 50, "offset": 0
}
```

### Example: `GET /api/stats`
```json
{
  "total": 2,
  "by_severity": {"3": 2},
  "by_signature": {"CyberGuard Test Alert": 1, "CyberGuard Warning Alert": 1},
  "by_src_ip": {"127.0.0.1": 2},
  "last_24h": 2
}
```

---

## Configuration (env vars)

| Variable | Default | Meaning |
|----------|---------|---------|
| `CYBERGUARD_EVE_PATH` | `/var/log/suricata/eve.json` | Suricata EVE JSON file |
| `CYBERGUARD_SURICATA_PID` | `/tmp/suricata.pid` | Suricata pidfile |
| `CYBERGUARD_DB_PATH` | `data/cyberguard.db` | SQLite DB (git-ignored) |
| `CYBERGUARD_POLL_SECONDS` | `2` | Background poll interval |
| `CYBERGUARD_PROC_BASE` | `/proc` | Process check base (injectable for tests) |

---

## Running

```bash
# One ingestion cycle (no server)
python -m app.main ingest-once

# API + background ingestion worker (localhost)
python -m app.main            # http://127.0.0.1:5000

# Tests (Windows, no Suricata)
pytest -q
```

On the Kali VM, set `CYBERGUARD_EVE_PATH=/var/log/suricata/eve.json` (the default)
and run the backend after Suricata is capturing, then trigger the lab requests to
see genuine alerts flow into SQLite and the API.

> **Note on the database:** there is no migration framework (kept simple for this
> project). The SQLite DB only caches re-ingestable Suricata alerts, so if the
> schema changes, delete the old `data/cyberguard.db` and let it be recreated.

---

## Test results (actual, Windows)

`pytest -v` → **34 passed**. Coverage includes: real-fixture parsing, invalid JSON
lines, partial/incomplete lines, non-alert events ignored, alert normalization,
empty category accepted, `-0500` timestamp parsing, duplicate/re-ingest dedup,
missing file, truncation and inode-change rotation, DB persistence, `/api/alerts`
filters (including date), `/api/stats`, and `/api/status` with injected
missing-pid / no-proc (not-running / unverified) cases.

**End-to-end validation on the Kali VM is pending** (to be run against live
Suricata + lab traffic).
