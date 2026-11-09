# PROJECT_MEMORY.md — CyberGuard Persistent Memory

> Single source of truth for project state. Update after every meaningful change
> and before completing each phase. Be specific — record *what*, *where*, *how it
> works*, and *how it was verified*.

**Last updated:** 2026-11-09
**Current phase:** Phase 2 — Suricata IDS Setup (COMPLETE — performed manually on the Kali VM)

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
│   └── rules/
│       ├── cyberguard.rules   # source-of-truth rules (sid 1000001/1000002); active on VM
│       └── local.rules        # placeholder/scratch (not referenced by VM config)
├── lab/README.md              # authorized local lab rules of engagement
├── tests/test_eve_reader.py   # pytest suite (8 tests)
├── data/.gitkeep              # runtime DB/EVE dir (contents git-ignored)
├── docs/
│   ├── architecture.md        # architecture explanation
│   └── suricata-setup.md      # Phase 2 Suricata install/config (manual, Kali VM)
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

**Status:** both rules **LOAD successfully** (config test: 2 rules loaded, 0
failed) but have **NOT yet been tested against real traffic** — that is Phase 3.
Local custom SID range is ≥ 1000000 to avoid clashing with shipped rules.

---

## 9. EVE JSON Location

On the Kali VM: `/var/log/suricata/eve.json` (enabled by default). Confirmed
**growing** (stats events appended) while Suricata ran. EVE JSON is runtime
output and is **git-ignored** — never committed. In local Windows dev the Flask
app's default `EVE_JSON_PATH` is the project-local `data/eve.json` (overridden on
the VM via `.env`).

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

**Phase 2 (complete — performed manually on the Kali VM; documentation only in
this repo):**
- Suricata 8.0.7 installed and configured on the Kali Linux 2026.3 VM (IDS mode).
- `rule-files` pointed at `cyberguard.rules`; two custom rules (sid 1000001/
  1000002) load successfully (2 loaded, 0 failed).
- EVE JSON confirmed writing/growing at `/var/log/suricata/eve.json`.
- Added `suricata/rules/cyberguard.rules` (source of truth) and
  `docs/suricata-setup.md` to the repo.
- Rules not yet tested against live traffic (Phase 3).

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

---

## 17. Errors Encountered and How They Were Fixed

None in Phase 0 or Phase 1. (Note: pytest needed the project root on `sys.path`
to import the `app` package — handled by adding a root `conftest.py`.)

---

## 18. Known Limitations

- Suricata runs as **root** and captures on **`lo` only**; `eth0` is **not**
  monitored in this setup, so only local (loopback) traffic is inspected.
- Suricata service is started **manually** (not enabled on boot).
- Custom rules load successfully but are **not yet validated against live
  traffic** (Phase 3).
- Backend and Suricata do not yet run together; integration on the VM is Phase 4.
- Dashboard not secured for public exposure (localhost-only by design).

---

## 19. Current Development Phase

**Phase 2 — Suricata IDS Setup: COMPLETE** (performed manually on the Kali VM;
documented and committed here). Awaiting the user's explicit **Phase 3** prompt.

---

## 20. Exact Next Steps

Wait for the user's next phase prompt (**Phase 3**). Expected focus (not started
until explicitly requested):
1. Generate controlled lab HTTP traffic on the VM containing `/cyberguard-test`
   and `/cyberguard-warning`.
2. Confirm Suricata emits genuine alert events (sid 1000001/1000002) to
   `/var/log/suricata/eve.json`.
3. Verify the EVE JSON alert structure that the Python reader will later ingest.

Do **not** begin any of these until the user explicitly provides the phase.

---

## Phase Plan (indicative only — the user drives the exact phase each time)

- **Phase 0 — Initialization:** repo docs, `.gitignore`, memory files, Git/remote
  verification. ✅ (`0fba761`)
- **Phase 1 — Project structure & Python environment:** full folder layout, venv,
  minimal Flask app, honest status endpoints, dashboard shell. ✅
- **Phase 2 — Suricata IDS setup:** Suricata 8.0.7 installed & configured on the
  Kali VM (IDS mode); custom rules load (0 failed); EVE JSON confirmed writing.
  Documented in the repo. ✅ (manual on VM)
- **Later phases (order set by the user):** test rules against live lab traffic +
  verify genuine EVE JSON alerts (Phase 3); Python ingestion into SQLite; backend
  +Suricata integration on the VM (Phase 4); full Flask API over stored events;
  full dashboard; optional Telegram notifications.

Each phase: implement → test → review → update this file → commit/push → report →
STOP.
