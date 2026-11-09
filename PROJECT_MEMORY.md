# PROJECT_MEMORY.md — CyberGuard Persistent Memory

> Single source of truth for project state. Update after every meaningful change
> and before completing each phase. Be specific — record *what*, *where*, *how it
> works*, and *how it was verified*.

**Last updated:** 2026-11-09
**Current phase:** Phase 4 — Python Backend & EVE JSON Integration (COMPLETE; Windows tests pass; Kali end-to-end validated manually)

---

## 1. Project Objective

CyberGuard is a network security monitoring application powered by **Suricata IDS**.
Suricata inspects real or authorized recorded (PCAP) network traffic, evaluates
packets against detection rules, generates genuine security events, and writes them
to **EVE JSON**. Python reads those events and presents them; it is never an
alternative detection engine. If Suricata stops, new genuine detections stop.

---

## 2. Project Architecture

```
            ┌──────────────────────────────────────────────┐
            │                  SURICATA IDS                 │
            │  (THE detection engine — live NIC or PCAP)    │
            │  packets → rules → genuine events → EVE JSON  │
            └───────────────────────┬──────────────────────┘
                                     │ writes
                                     ▼
                              eve.json (append)
                                     │ tailed/read by
                                     ▼
            ┌──────────────────────────────────────────────┐
            │                 PYTHON (Flask)                │
            │  reader  → parse EVE JSON events              │
            │  store   → insert into SQLite                 │
            │  api     → Flask endpoints serve events       │
            │  notify  → optional Telegram alerts (final)   │
            └───────────────────────┬──────────────────────┘
                                     │ serves
                                     ▼
            ┌──────────────────────────────────────────────┐
            │     DASHBOARD (HTML + CSS + vanilla JS)       │
            │     fetches API, renders events/metrics       │
            └──────────────────────────────────────────────┘
```

**Boundary rule:** detection logic lives ONLY in Suricata rules. Python never
decides what is or isn't an intrusion — it only processes what Suricata reports.

---

## 3. Technology Stack

| Layer            | Technology                                   |
|------------------|----------------------------------------------|
| Detection engine | Suricata IDS 8.x (or compatible stable)      |
| OS (engine host) | Kali Linux 2026.3 (Debian-based), VirtualBox |
| Backend          | Python 3, Flask                              |
| Storage          | SQLite                                        |
| Frontend         | HTML, CSS, vanilla JavaScript                 |
| Data format      | EVE JSON                                       |
| Notifications    | Telegram Bot API (optional, final phase)      |

Explicitly **excluded** unless approved: React, Next.js, Docker, Redis,
Elasticsearch, cloud infra.

---

## 4. Current Repository Structure

```
cyberguard-suricata-ids/
├── app/
│   ├── __init__.py            # Flask app factory + route registration
│   ├── main.py                # entry point: python -m app.main
│   ├── config.py              # environment-based configuration
│   ├── services/
│   │   ├── __init__.py
│   │   ├── eve_reader.py      # incremental EVE JSON reader (inode+offset; alerts only)
│   │   ├── alert_service.py   # normalize/ingest/query/stats/status + ingestion worker
│   │   └── database.py        # SQLite alerts + ingest_state, parameterized queries
│   ├── templates/
│   │   ├── index.html         # dashboard
│   │   ├── alerts.html        # alerts page (empty until ingestion phase)
│   │   └── rule_lab.html      # rule lab page
│   └── static/
│       ├── css/style.css
│       └── js/dashboard.js    # fetches /api/status + /api/health
├── suricata/
│   ├── config/.gitkeep        # future suricata.yaml / threshold config
│   └── rules/
│       ├── cyberguard.rules   # source-of-truth rules (sid 1000001/1000002); active on VM
│       └── local.rules        # placeholder/scratch (not referenced by VM config)
├── lab/
│   ├── README.md              # authorized local lab rules of engagement + server usage
│   └── server.py              # harmless localhost HTTP test server (stdlib; Windows-only so far)
├── tests/
│   ├── conftest.py            # shared config/fixtures helpers
│   ├── fixtures/eve_alerts_sample.jsonl  # REAL Suricata alert fixtures (2 lines)
│   ├── test_eve_reader.py     # reader behaviors
│   ├── test_alert_service.py  # normalization, ingest, status
│   ├── test_database.py       # persistence, dedup, queries, stats
│   └── test_api.py            # /api/health /status /alerts /stats
├── data/.gitkeep              # runtime DB/EVE dir (contents git-ignored)
├── docs/
│   ├── architecture.md        # architecture explanation
│   ├── suricata-setup.md      # Phase 2 Suricata install/config (manual, Kali VM)
│   ├── phase3-detection-tests.md  # Phase 3 detection test results (manual, Kali VM)
│   └── phase4-integration.md  # Phase 4 backend/EVE integration (Windows tests pass)
├── conftest.py                # makes project root importable for pytest
├── requirements.txt           # Flask, python-dotenv, pytest
├── README.md
├── .env.example               # placeholder env vars (no real secrets)
├── .gitignore
├── CLAUDE.md
└── PROJECT_MEMORY.md           # this file
```

**Architectural adjustments (documented):**
- Added root `conftest.py` so pytest puts the project root on `sys.path` and the
  `app` package imports without installation.
- Added page routes `/alerts` and `/rule-lab` to serve the two extra templates
  required by the structure (in addition to the required `/`).
- Local dev defaults `EVE_JSON_PATH` and `SQLITE_DB_PATH` to the project-local
  `data/` directory (cross-platform); overridden via `.env` on the Linux engine
  host. The virtual environment lives in `.venv/` (git-ignored).

---

## 5. Development Environment

- **Main workstation:** Windows 11 + VS Code.
- **Python:** 3.12.10 on Windows (`python`). Virtual environment at `.venv/`.
- **Linux environment for Suricata:** Kali Linux 2026.3 (Debian-based) running
  in an Oracle VirtualBox VM.
- **Windows ↔ Kali workflow:** code is written on **Windows** (VS Code) and
  **pushed to GitHub**; the repo is then **cloned on the Kali VM**, where
  Suricata and (later) the Python backend run together. Backend+Suricata
  integration on the VM is planned for **Phase 4**. Runtime artifacts
  (`eve.json`, Suricata logs, SQLite DB) stay on the VM and are git-ignored.
- **Fallback plan:** if live traffic capture is unreliable, use Suricata offline
  PCAP analysis against controlled lab traffic. Never fabricate detections.

---

## 6. Suricata Installation Details

*Performed and verified manually on the Kali Linux 2026.3 VM (VirtualBox). Not
run on Windows.* Full write-up: [`docs/suricata-setup.md`](docs/suricata-setup.md).

- **OS/host:** Kali GNU/Linux Rolling 2026.3 (Debian-based), kernel
  7.1.5+kali-amd64, Oracle VirtualBox NAT, `eth0 = 10.0.2.15/24`.
- **Suricata:** 8.0.7 RELEASE, installed via `sudo apt install -y suricata`
  (Kali repo).
- **Mode:** IDS (default "IDS mode by default") — detection only, no IPS/blocking.
- **Service:** not auto-started on Kali; started manually.
- **Capture:** live on interface `lo` (loopback) for local tests.

---

## 7. Suricata Configuration Paths

*(On the Kali VM — verified manually.)*

- Main config: `/etc/suricata/suricata.yaml`
- Original backup: `/etc/suricata/suricata.yaml.orig`
- **Only change:** `rule-files` entry changed from `suricata.rules` to
  `cyberguard.rules`.
- Default rule path: `/var/lib/suricata/rules` → active file
  `/var/lib/suricata/rules/cyberguard.rules`.

---

## 8. Custom Rule Definitions and Signature IDs

Source-of-truth copy in the repo: `suricata/rules/cyberguard.rules`. On the VM
these are deployed to `/var/lib/suricata/rules/cyberguard.rules`.

| sid     | message                 | protocol | direction               | match (http.uri contains) |
|---------|-------------------------|----------|-------------------------|---------------------------|
| 1000001 | CyberGuard Test Alert   | http     | to_server, established  | `/cyberguard-test`        |
| 1000002 | CyberGuard Warning Alert| http     | to_server, established  | `/cyberguard-warning`     |

**Status:** both rules load successfully (0 failed) **and are now verified
against live lab traffic in Phase 3** — `/cyberguard-test` → sid 1000001,
`/cyberguard-warning` → sid 1000002, both produced genuine EVE JSON alerts
(see section 16 and `docs/phase3-detection-tests.md`). Local custom SID range is
≥ 1000000 to avoid clashing with shipped rules.

---

## 9. EVE JSON Location

On the Kali VM: `/var/log/suricata/eve.json` (enabled by default). Confirmed
**growing** (stats events appended) while Suricata ran. EVE JSON is runtime
output and is **git-ignored** — never committed. In local Windows dev the Flask
app's default `EVE_JSON_PATH` is the project-local `data/eve.json` (overridden on
the VM via `.env`).

---

## 10. Python Modules and Responsibilities

- `app/config.py` — `Config` reads env vars: Flask host/port/env/secret plus the
  Phase 4 vars `CYBERGUARD_EVE_PATH`, `CYBERGUARD_SURICATA_PID`,
  `CYBERGUARD_PROC_BASE`, `CYBERGUARD_DB_PATH`, `CYBERGUARD_POLL_SECONDS`. Loads
  `.env` if present; no hardcoded secrets.
- `app/__init__.py` — `create_app(config)` factory: configures Flask, calls
  `database.init_db()`, registers routes. Does **not** start the worker (so tests
  never spawn threads).
- `app/main.py` — CLI entry point. `serve` (default) runs the API + ingestion
  worker; `ingest-once` runs a single cycle. Worker-double-start guarded via
  `WERKZEUG_RUN_MAIN` + an internal lock; clean shutdown via `atexit`.
- `app/services/eve_reader.py` — `read_new_alerts(db_path, eve_path)` incremental
  reader using a persisted (inode, byte offset) in SQLite. Surfaces ONLY
  `event_type == "alert"`; skips invalid/partial lines; handles missing file
  (`eve_missing`), truncation/rotation, and Suricata stopped. `extract_alert_fields`
  maps EVE fields (incl. http + in_iface) and keeps the raw line.
- `app/services/database.py` — `get_connection`, `init_db` (alerts + ingest_state
  tables, indexes), `insert_alert` (INSERT OR IGNORE), `count_alerts`,
  `query_alerts` (parameterized filters, newest first), `get_stats`,
  `get_ingest_state`, `update_ingest_state`.
- `app/services/alert_service.py` — `normalize_timestamp` (−0500→UTC),
  `to_db_record`, `ingest(config)` (read→normalize→store, dedup summary),
  `list_alerts`, `build_filters`, `get_stats`, `check_suricata_process`
  (pidfile + `/proc/<pid>/comm`, no shell), `get_status`, and `IngestionWorker`
  (daemon poll thread).
- `notify` — optional Telegram notifications (final phase; not created yet).

---

## 11. API Endpoints

Pages:
- `GET /` → `index.html` (dashboard).
- `GET /alerts` → `alerts.html`.
- `GET /rule-lab` → `rule_lab.html`.

API (JSON):
- `GET /api/health` → `{"status":"ok","service":"cyberguard","component":"flask-api"}`.
  Liveness of the Flask API itself, NOT the detection engine.
- `GET /api/status` → `{backend_running, detection_engine, eve_path,
  eve_file_exists, suricata_process (verified_running|verified_not_running|
  unverified), last_event_timestamp, last_alert_ingested_at, invalid_lines_count,
  total_alerts}`. Never reports running just because eve.json exists.
- `GET /api/alerts` → `{alerts:[...], count, limit, offset}`, newest first.
  Params: `limit`, `offset`, `severity`, `signature_id`, `signature`, `src_ip`,
  `q`, `from`, `to` (ISO). Empty category shown as `uncategorized`.
- `GET /api/stats` → `{total, by_severity, by_signature, by_src_ip, last_24h}`.
- No endpoint executes commands or accepts filesystem paths.

---

## 12. Database Schema

SQLite file at `CYBERGUARD_DB_PATH` (default `data/cyberguard.db`, git-ignored).

**Table `alerts`** — `UNIQUE(flow_id, timestamp_raw, signature_id)` with
`INSERT OR IGNORE`; indexes on `timestamp_utc`, `signature_id`, `severity`,
`src_ip`:

| column | type | notes |
|--------|------|-------|
| id | INTEGER | PK AUTOINCREMENT |
| timestamp_raw | TEXT | original Suricata timestamp (e.g. `…-0500`) |
| timestamp_utc | TEXT | normalized UTC (`…+00:00`) |
| flow_id | INTEGER | Suricata flow id |
| src_ip/src_port/dest_ip/dest_port | TEXT/INT | endpoints |
| proto | TEXT | e.g. TCP |
| app_proto | TEXT | e.g. http |
| signature | TEXT | rule message |
| signature_id | INTEGER | Suricata SID |
| severity | INTEGER | alert severity (priority) |
| category | TEXT | raw (may be empty "") |
| action | TEXT | e.g. allowed |
| http_url/http_method/http_hostname/http_status/http_user_agent | mixed | HTTP fields |
| in_iface | TEXT | capture interface (e.g. lo) |
| raw_json | TEXT | original EVE JSON line (preserved) |
| ingested_at | TEXT | DEFAULT CURRENT_TIMESTAMP |

**Table `ingest_state`** — single row (id=1): `inode`, `byte_offset`,
`invalid_lines_count`, `last_event_timestamp`, `last_alert_ingested_at`.

No migration framework: the DB only caches re-ingestable alerts, so a schema
change means deleting the old `data/cyberguard.db` (it is recreated on startup).

---

## 13. Dashboard Components

- `index.html` — Detection Engine Status card, API Health card, About card.
  `dashboard.js` fetches `/api/status` and `/api/health` on load and renders the
  honest state (shows "NOT CONFIGURED" in red when Suricata is unconfigured;
  never a fake active state).
- `alerts.html` — alerts table placeholder ("No alerts yet").
- `rule_lab.html` — rule lab placeholder.
- `static/css/style.css` — dark theme styling.

---

## 14. Implemented Functionality

**Phase 0 (complete):**
- Initialized repository documentation and guardrails.
- Created `.gitignore`, `CLAUDE.md`, `PROJECT_MEMORY.md`, `.env.example`.
- Verified Git identity, remote, and branch.

**Phase 1 (complete):**
- Full project structure (`app/`, `suricata/`, `lab/`, `tests/`, `data/`,
  `docs/`) created.
- Python venv (`.venv/`) with Flask, python-dotenv, pytest installed.
- Environment-based config (`app/config.py`), no hardcoded secrets/paths.
- Minimal working Flask app (factory + entry point) with `/`, `/alerts`,
  `/rule-lab`, `/api/health`, `/api/status`.
- Service layer: EVE JSON reader, SQLite storage, honest alert/engine status.
- Dashboard (HTML/CSS/vanilla JS) showing honest engine status.
- Runs without Suricata and reports the engine as NOT CONFIGURED (no fake state).

**Phase 2 (complete — performed manually on the Kali VM; documentation only in
this repo):**
- Suricata 8.0.7 installed and configured on the Kali Linux 2026.3 VM (IDS mode).
- `rule-files` pointed at `cyberguard.rules`; two custom rules (sid 1000001/
  1000002) load successfully (2 loaded, 0 failed).
- EVE JSON confirmed writing/growing at `/var/log/suricata/eve.json`.
- Added `suricata/rules/cyberguard.rules` (source of truth) and
  `docs/suricata-setup.md` to the repo.
- Rules not yet tested against live traffic (Phase 3).

**Phase 3 (complete — executed manually on the Kali VM; repo gains lab files +
docs):**
- Verified genuine detections on loopback: `/cyberguard-test` → "CyberGuard Test
  Alert" (sid 1000001), `/cyberguard-warning` → "CyberGuard Warning Alert" (sid
  1000002); `/index.html` → no alert. All PASS.
- Disable/restore experiment proved detection depends on the Suricata rule:
  commenting out the Test Alert rule stopped new Test Alerts (count unchanged
  while Warning kept firing); restoring it resumed detection.
- Confirmed the real EVE alert field set the Python reader will ingest.
- Added `lab/server.py` (harmless localhost test server; later validated manually
  on the Kali VM in Phase 4), updated `lab/README.md`, added
  `docs/phase3-detection-tests.md`, and commented `cyberguard.rules`
  (rule lines kept byte-identical).

**Phase 4 (COMPLETE — Windows tests pass; Kali end-to-end validated manually):**
- Python backend now ingests **real** Suricata EVE JSON into SQLite and serves it.
- **EVE processing logic:** incremental read resuming from persisted
  (inode, byte offset); only `event_type == "alert"` kept; invalid JSON counted +
  skipped; partial last line not consumed; truncation/inode-change restart from 0;
  missing file → `eve_missing`; Suricata stopped → no new lines, no crash.
- Timestamps normalized `−0500`→UTC; both raw + UTC stored. Empty category kept in
  DB, shown as `uncategorized` in API.
- Dedup via persisted offset **and** `UNIQUE(flow_id, timestamp_raw, signature_id)`.
- New API: `/api/status`, `/api/alerts` (filters incl. date, pagination),
  `/api/stats`; `/api/health` retained.
- Suricata process verified via pidfile + `/proc/<pid>/comm` (no shell/subprocess);
  `unverified` on Windows.
- Background daemon worker polls every `CYBERGUARD_POLL_SECONDS`; `ingest-once` CLI.
- 34 pytest tests pass on Windows with no Suricata (see section 16).

---

## 15. Commands Used to Run the Application

```bash
# Create venv + install deps (Windows path to venv python shown)
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt   # Windows
# source .venv/bin/activate && pip install -r requirements.txt # Linux/macOS

# Run the Flask app (serves http://127.0.0.1:5000/)
.venv/Scripts/python.exe -m app.main

# Run tests
.venv/Scripts/python.exe -m pytest -q
```

**Suricata (on the Kali VM — verified manually):**

```bash
# Install (Kali repo)
sudo apt install -y suricata

# Validate config + load rules (no capture)
sudo suricata -T -c /etc/suricata/suricata.yaml -v
#   → "successfully loaded"; 2 rules successfully loaded, 0 failed

# Live capture on loopback for local tests (daemon)
sudo suricata -c /etc/suricata/suricata.yaml -i lo -D --pidfile /tmp/suricata.pid
```

**Phase 3 detection tests (on the Kali VM — verified manually):**

```bash
# Harmless local test server (manual tests used the stdlib server)
python3 -m http.server 8000 --bind 127.0.0.1
# Repo equivalent (validated on Kali VM): python lab/server.py --port 8000

# Trigger requests
curl http://127.0.0.1:8000/index.html          # no alert
curl http://127.0.0.1:8000/cyberguard-test     # -> sid 1000001
curl http://127.0.0.1:8000/cyberguard-warning  # -> sid 1000002

# Count alerts by signature (eve.json is cumulative across runs)
grep '"event_type":"alert"' eve.json \
  | grep -o '"signature":"[^"]*"' | sort | uniq -c

# Disable / restore the Test Alert rule (sed), verify with:
grep -c '^#alert' /var/lib/suricata/rules/cyberguard.rules   # 1 disabled, 0 restored
```

**Phase 4 backend (Windows dev):**

```bash
.venv/Scripts/python.exe -m app.main ingest-once   # one ingestion cycle
.venv/Scripts/python.exe -m app.main               # API + worker (localhost:5000)
.venv/Scripts/python.exe -m pytest -q              # 34 tests
```

**Env vars (defaults):** `CYBERGUARD_EVE_PATH=/var/log/suricata/eve.json`,
`CYBERGUARD_SURICATA_PID=/tmp/suricata.pid`, `CYBERGUARD_DB_PATH=data/cyberguard.db`,
`CYBERGUARD_POLL_SECONDS=2`, `CYBERGUARD_PROC_BASE=/proc`.

---

## 16. Tests Performed and Actual Results

**Phase 0:**
- `git status` → fresh repo, branch `main`, no commits yet. ✅
- `git remote -v` → `origin` = `https://github.com/Khayal07/cyberguard-suricata-ids.git`. ✅
- `git config user.name` / `user.email` → `Khayal07` / `khayal.izada39@gmail.com`. ✅
- `git ls-remote origin` → exit 0 (remote reachable, auth OK; empty remote). ✅
- Commit hash for Phase 0: `0fba761`.

**Phase 1 (actual results):**
- Folders/files: all expected paths created (verified via `git add --dry-run`:
  21 source files, no secrets/venv/db). ✅
- Dependencies install: `pip install -r requirements.txt` → Flask 3.1.3,
  python-dotenv 1.2.4, pytest 8.4.2 (+ Werkzeug/Jinja2/click). ✅
- Tests: `pytest -q` → **8 passed in 0.45s**. ✅
- Flask starts: `python -m app.main` → "Running on http://127.0.0.1:5000". ✅
- `GET /api/health` → HTTP 200, `{"status":"ok",...}`. ✅
- `GET /api/status` → HTTP 200, `suricata_configured:false`, `eve_json_exists:false`,
  `alert_count:0`, "NOT configured" message. ✅ (honest unconfigured state)
- `GET /` → HTTP 200, dashboard renders. ✅
- No secret files staged: `.env`, `.venv/`, `data/cyberguard.db` confirmed
  git-ignored. ✅

**Phase 2 (verified manually on the Kali VM — NOT on Windows):**
- `suricata -V` / install → Suricata 8.0.7 RELEASE (Kali repo). ✅
- `suricata -T -c /etc/suricata/suricata.yaml -v` → "successfully loaded";
  **2 rules successfully loaded, 0 failed.** ✅
- Live capture on `lo` started as daemon; `/var/log/suricata/eve.json` confirmed
  **growing** (stats events). ✅
- Harmless warning observed: `lo does not support SIOCETHTOOL ioctl` (expected on
  loopback; no impact).
- Rules **not yet tested against real traffic** (Phase 3). ⏳

**Phase 3 (verified manually on the Kali VM — NOT on Windows):**
- Scenario A: `GET /index.html` → no alert. **PASS** ✅
- Scenario B: `GET /cyberguard-test` → "CyberGuard Test Alert" (sid 1000001).
  **PASS** ✅
- Scenario C: `GET /cyberguard-warning` → "CyberGuard Warning Alert" (sid
  1000002). **PASS** ✅
- Scenario D (disable Test Alert rule, repeat): Test Alert count `1` (unchanged),
  Warning Alert `2`. **PASS** ✅ (detection depends on the rule)
- Scenario E (restore rule, send `/cyberguard-test`): Test Alert `2`, Warning
  Alert `2`. **PASS** ✅
- Real EVE alert fields seen: `event_type=alert`, src/dest `127.0.0.1`,
  `dest_port 8000`, `app_proto http`, `http.url`, `http_method GET`,
  `status 404`, `http_user_agent curl/8.21.0`, `flow` section; timestamps `-0500`.

**Phase 4 (actual, Windows, no Suricata):**
- `pytest -v` → **34 passed in ~1.8s**. ✅ Covers: real-fixture parsing; invalid
  JSON line; partial/incomplete line; non-alert events ignored; alert
  normalization; empty category accepted; `-0500` timestamp parsing; duplicate /
  re-ingest dedup (incl. offset-reset still dedupes); missing file; truncation +
  inode-change rotation; DB persistence; parameterized-SQL injection-as-data;
  `/api/alerts` filters incl. date + pagination; `/api/stats`; `/api/status`
  unverified (no /proc) and verified_not_running (proc present, pid missing).
- `python -m app.main ingest-once` (no Suricata) → `{'status': 'eve_missing', ...}`
  (honest no-op). ✅
- Fixtures: `tests/fixtures/eve_alerts_sample.jsonl` holds the two REAL Suricata
  8.0.7 alert lines from the VM.

**Phase 4 end-to-end on the Kali VM (verified manually — live Suricata 8.0.7):**
- `git pull`, created venv, `pip install -r requirements.txt`. ✅
- `python -m app.main ingest-once` → **read 6, inserted 6, duplicates 0,
  invalid 0** (6 genuine alerts from `/var/log/suricata/eve.json`). ✅
- `python -m app.main` served on `127.0.0.1:5000`. ✅
- `GET /api/status` → `suricata_process = "verified_running"`. ✅
- `GET /api/alerts` and `GET /api/stats` returned **real** Suricata alerts. ✅
- Dashboard in Kali Firefox showed **"SURICATA RUNNING (verified)"**. ✅
- Background worker ingested live traffic: stored count grew **6 → 8**. ✅
- `lab/server.py` validated on the VM: `python3 lab/server.py --port 8000` returned
  200 for `/`, `/cyberguard-test`, `/cyberguard-warning`; Suricata raised sid
  1000001 and 1000002 (http status 200). ✅
- Full chain validated: Suricata → eve.json → reader → SQLite → Flask → dashboard,
  Python performing no detection of its own.

---

## 17. Errors Encountered and How They Were Fixed

- Phase 1: pytest needed the project root on `sys.path` to import `app` — fixed
  with a root `conftest.py`.
- Phase 4: Windows text-mode writes translated `\n`→`\r\n`, leaving a stray `\r`
  on EVE lines in tests. Fixed by (a) having the reader tolerate a trailing `\r`
  and (b) writing test EVE files as raw LF bytes (mirrors real Suricata output).
- Phase 4: a stale Phase 1 `data/cyberguard.db` (old schema) made `init_db` fail
  creating the `timestamp_utc` index. The DB is a disposable, git-ignored cache;
  removed it and it was recreated with the new schema.

---

## 18. Known Limitations

- Suricata runs as **root** and captures on **`lo` only**; `eth0` is **not**
  monitored in this setup, so only local (loopback) traffic is inspected.
- Suricata service is started **manually** (not enabled on boot).
- Custom rules are now validated against live lab traffic (Phase 3), but only on
  the **`lo`** interface; `eth0` traffic is not monitored.
- `eve.json` is **cumulative** across Suricata runs (alert counts are running
  totals, not per-run).
- During the Phase 3 disable step, a separate `suricata -T` re-validation was not
  run after commenting the rule (Suricata still started successfully).
- SQLite has **no migrations**; a schema change requires deleting the disposable
  `data/cyberguard.db` (it only caches re-ingestable Suricata alerts).
- Reading `/var/log/suricata/eve.json` on the VM requires the backend to have read
  access (file is root-owned, world-readable in this setup).
- Dashboard not secured for public exposure (localhost-only by design).

---

## 19. Current Development Phase

**Phase 4 — Python Backend & EVE JSON Integration: COMPLETE.** Windows unit tests
pass (34) **and end-to-end validation on the Kali VM is complete (verified
manually)** — see section 16. Awaiting the user's explicit **Phase 5** prompt.

---

## 20. Exact Next Steps

Wait for the user's explicit **Phase 5** prompt (expected: full dashboard UI
consuming `/api/alerts` and `/api/stats`). Phase 4 is fully validated on the Kali
VM; nothing further is required there.

Do **not** begin Phase 5 until the user explicitly provides it.

---

## Phase Plan (indicative only — the user drives the exact phase each time)

- **Phase 0 — Initialization:** repo docs, `.gitignore`, memory files, Git/remote
  verification. ✅ (`0fba761`)
- **Phase 1 — Project structure & Python environment:** full folder layout, venv,
  minimal Flask app, honest status endpoints, dashboard shell. ✅
- **Phase 2 — Suricata IDS setup:** Suricata 8.0.7 installed & configured on the
  Kali VM (IDS mode); custom rules load (0 failed); EVE JSON confirmed writing.
  Documented in the repo. ✅ (manual on VM)
- **Phase 3 — Detection tests:** genuine alerts verified on loopback for sid
  1000001/1000002; disable/restore experiment proved detection depends on the
  rule; lab server + test docs added. ✅ (manual on VM)
- **Phase 4 — Backend & EVE integration:** incremental EVE reader, SQLite storage
  with dedup, Flask API (status/alerts/stats), background worker, 34 Windows
  tests. ✅ code complete; ✅ Kali end-to-end validated manually.
- **Later phases (order set by the user):** full dashboard UI over the API
  (Phase 5); optional Telegram notifications.

Each phase: implement → test → review → update this file → commit/push → report →
STOP.
