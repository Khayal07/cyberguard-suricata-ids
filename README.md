# CyberGuard

### Suricata-Powered Network Intrusion Detection and Monitoring System

CyberGuard is a university Information Security project. **Suricata IDS is the
central, indispensable detection engine.** It inspects network traffic (live or
authorized PCAP), evaluates it against detection rules, generates genuine
security events, and writes them to **EVE JSON**. Python only reads, stores,
serves, and displays those events — it never performs detection itself. If
Suricata is stopped, new genuine detections stop.

## Objective

Provide a clear, beginner-friendly network security monitoring application where
the detection work is done by Suricata and Python provides ingestion, storage, a
small API, and a dashboard.

## Planned architecture

```
Traffic/PCAP → Suricata (rules) → EVE JSON → Python (read → SQLite → Flask API) → Dashboard
```

See [`docs/architecture.md`](docs/architecture.md) for details.

## Technology stack

- **Suricata IDS 8.x** (the detection engine) on Kali Linux (Debian-based)
- **Python 3**, **Flask**
- **SQLite**
- **HTML / CSS / vanilla JavaScript**
- **EVE JSON** data format
- **Telegram Bot API** (optional, final phase)

The standard library handles JSON, SQLite, and file processing. No React,
Next.js, Docker, Redis, Elasticsearch, or cloud infrastructure.

## Project structure

```
app/            Flask application
  config.py       environment-based configuration
  __init__.py     app factory + routes
  main.py         entry point
  services/       eve_reader, database, alert_service
  templates/      index, alerts, rule_lab
  static/         css + js
suricata/       rules/ and config/ for the Suricata engine
lab/            authorized local lab notes
tests/          pytest tests
data/           runtime SQLite DB / EVE JSON (git-ignored)
docs/           architecture notes
```

## Setup (local development, Windows/Linux)

1. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # Windows (PowerShell):
   .venv\Scripts\Activate.ps1
   # Linux/macOS:
   source .venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. (Optional) copy the environment template and edit values:
   ```bash
   cp .env.example .env
   ```
4. Run the application:
   ```bash
   python -m app.main
   ```
   Then open http://127.0.0.1:5000/

5. Run tests:
   ```bash
   pytest
   ```

## Current development status

**Phase 4 complete (Windows unit tests pass; Kali end-to-end validated manually).**
Suricata (8.0.7, Kali VM) is installed, configured, and its custom rules verified
against live lab traffic. The Python backend now incrementally reads Suricata's
real EVE JSON, stores genuine alerts in SQLite (with dedup), and serves them via
`/api/status`, `/api/alerts`, and `/api/stats`. The app runs even when Suricata is
absent and reports the engine honestly (never a fake active state). The full
dashboard UI is a later phase. See
[`docs/phase4-integration.md`](docs/phase4-integration.md).

See [`PROJECT_MEMORY.md`](PROJECT_MEMORY.md) for detailed project state.

## Security

Experiments run only in an authorized local lab using harmless markers and
controlled traffic. The Flask app stays bound to `localhost`. Secrets live in a
local `.env` (never committed); see [`.env.example`](.env.example).
