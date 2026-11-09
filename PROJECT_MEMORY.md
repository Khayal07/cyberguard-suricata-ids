# PROJECT_MEMORY.md — CyberGuard Persistent Memory

> Single source of truth for project state. Update after every meaningful change
> and before completing each phase. Be specific — record *what*, *where*, *how it
> works*, and *how it was verified*.

**Last updated:** 2026-11-09
**Current phase:** Phase 1 — Project Structure & Python Environment (COMPLETE)

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
│   │   ├── eve_reader.py      # read/parse Suricata EVE JSON (safe if missing)
│   │   ├── alert_service.py   # honest engine status + alert count
│   │   └── database.py        # SQLite connection + alerts schema
│   ├── templates/
│   │   ├── index.html         # dashboard
│   │   ├── alerts.html        # alerts page (empty until ingestion phase)
│   │   └── rule_lab.html      # rule lab page
│   └── static/
│       ├── css/style.css
│       └── js/dashboard.js    # fetches /api/status + /api/health
├── suricata/
│   ├── config/.gitkeep        # future suricata.yaml / threshold config
│   └── rules/local.rules      # custom lab rules (SID >= 1000000; none active yet)
├── lab/README.md              # authorized local lab rules of engagement
├── tests/test_eve_reader.py   # pytest suite (8 tests)
├── data/.gitkeep              # runtime DB/EVE dir (contents git-ignored)
├── docs/architecture.md       # architecture explanation
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
- **Fallback plan:** if live traffic capture is unreliable, use Suricata offline
  PCAP analysis against controlled lab traffic. Never fabricate detections.

---

## 6. Suricata Installation Details

Not yet installed. To be documented here once a phase covers installation
(version, install method, service/run mode, interface or PCAP mode).

---

## 7. Suricata Configuration Paths

Not yet configured. Will record: `suricata.yaml` path, rule file paths, EVE JSON
output path, HOME_NET/EXTERNAL_NET settings, and run command.

---

## 8. Custom Rule Definitions and Signature IDs

None yet. Will record each custom rule: `sid`, message, protocol, direction,
matching logic, and the lab traffic that triggers it. Custom SIDs will use the
local range (≥ 1000000) to avoid clashing with shipped rules.

---

## 9. EVE JSON Location

Not yet defined. Will be the Suricata EVE output file (e.g.
`/var/log/suricata/eve.json` or a project-local path). EVE JSON is runtime output
and is **git-ignored**.

---

## 10. Python Modules and Responsibilities

- `app/config.py` — `Config` class reading env vars (Flask host/port/env/secret,
  `EVE_JSON_PATH`, `SQLITE_DB_PATH`, Telegram). Loads `.env` via python-dotenv if
  present; project-relative defaults, no hardcoded secrets.
- `app/__init__.py` — `create_app()` factory: configures Flask, calls
  `database.init_db()`, registers page + API routes.
- `app/main.py` — entry point; builds the app and runs it on the configured
  host/port (`python -m app.main`).
- `app/services/eve_reader.py` — `eve_file_exists()`, `parse_line()`,
  `read_events(path, limit)`, `count_events()`. Reads Suricata EVE JSON
  (JSON-Lines); returns empty/None safely when the file is missing or a line is
  malformed. Never generates events.
- `app/services/database.py` — `get_connection()`, `init_db()` (creates `alerts`
  table), `count_alerts()`.
- `app/services/alert_service.py` — `get_engine_status(config)` (honest engine
  state from EVE file presence), `get_alert_count(config)`.
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
- `GET /api/status` → `{"detection_engine":"suricata","suricata_configured":<bool>,
  "eve_json_path":"...","eve_json_exists":<bool>,"message":"...","alert_count":<int>}`.
  Honest engine state: `suricata_configured` is `false` until EVE JSON output
  exists. Verified returning `false` / `alert_count: 0` in Phase 1.

---

## 12. Database Schema

SQLite file at `SQLITE_DB_PATH` (default `data/cyberguard.db`, git-ignored).
Table `alerts` (created by `database.init_db()`, empty until ingestion phase):

| column        | type    | notes                     |
|---------------|---------|---------------------------|
| id            | INTEGER | PK AUTOINCREMENT          |
| timestamp     | TEXT    | event timestamp           |
| signature     | TEXT    | rule message              |
| signature_id  | INTEGER | Suricata SID              |
| category      | TEXT    | alert category            |
| severity      | INTEGER | alert severity            |
| src_ip        | TEXT    |                           |
| src_port      | INTEGER |                           |
| dest_ip       | TEXT    |                           |
| dest_port     | INTEGER |                           |
| protocol      | TEXT    |                           |
| raw_json      | TEXT    | original EVE JSON line    |
| created_at    | TEXT    | DEFAULT CURRENT_TIMESTAMP |

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

Suricata run commands will be added when the engine is installed (later phase).

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

---

## 17. Errors Encountered and How They Were Fixed

None in Phase 0 or Phase 1. (Note: pytest needed the project root on `sys.path`
to import the `app` package — handled by adding a root `conftest.py`.)

---

## 18. Known Limitations

- Linux/Suricata environment not yet selected or installed.
- No live traffic validated yet; PCAP fallback may be used.
- Dashboard not secured for public exposure (localhost-only by design).

---

## 19. Current Development Phase

**Phase 1 — Project Structure & Python Environment: COMPLETE.** Awaiting the
user's explicit Phase 2 prompt.

---

## 20. Exact Next Steps

Wait for the user's next phase prompt (Phase 2). Likely candidates (not started
until explicitly requested):
1. Prepare the Kali Linux 2026.3 VM (Oracle VirtualBox) for Suricata.
2. Install Suricata and document version + config paths.
3. Configure EVE JSON output and author a minimal custom lab rule.

Do **not** begin any of these until the user explicitly provides the phase.

---

## Phase Plan (indicative only — the user drives the exact phase each time)

- **Phase 0 — Initialization:** repo docs, `.gitignore`, memory files, Git/remote
  verification. ✅ (`0fba761`)
- **Phase 1 — Project structure & Python environment:** full folder layout, venv,
  minimal Flask app, honest status endpoints, dashboard shell. ✅
- **Later phases (order set by the user):** Linux + Suricata install & config;
  custom lab rules + verify genuine EVE JSON; Python ingestion into SQLite; full
  Flask API over stored events; full dashboard; optional Telegram notifications.

Each phase: implement → test → review → update this file → commit/push → report →
STOP.
