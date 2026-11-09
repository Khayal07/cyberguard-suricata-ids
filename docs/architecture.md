# CyberGuard Architecture

## Principle

**Suricata is the only detection engine.** It inspects network traffic (live or
authorized PCAP), evaluates packets against rules, and writes genuine security
events to **EVE JSON**. Python never decides what is or isn't an intrusion — it
only reads, stores, serves, and displays what Suricata reports. If Suricata is
stopped, new genuine detections stop.

## Data flow

```
 Network traffic / PCAP
          │
          ▼
   ┌──────────────┐     writes      ┌───────────────┐
   │  SURICATA IDS │ ───────────────▶│   eve.json    │  (JSON Lines)
   │ rules engine  │                 │ (EVE output)  │
   └──────────────┘                 └───────┬───────┘
                                            │ read (never generated)
                                            ▼
   ┌──────────────────────────────────────────────────┐
   │                 PYTHON / FLASK                     │
   │  eve_reader   → parse EVE JSON lines               │
   │  database     → store events in SQLite (alerts)    │
   │  alert_service→ status + queries for the API       │
   │  app (routes) → serve pages and JSON API           │
   └───────────────────────┬──────────────────────────┘
                            │ HTTP (localhost)
                            ▼
   ┌──────────────────────────────────────────────────┐
   │   Dashboard (HTML + CSS + vanilla JS)             │
   │   fetches /api/status, /api/health; renders state │
   └──────────────────────────────────────────────────┘
```

## Components (current)

| Component                     | Responsibility                                    |
|-------------------------------|---------------------------------------------------|
| `app/config.py`               | Environment-based configuration (no secrets).     |
| `app/__init__.py`             | App factory; registers pages + API routes.        |
| `app/main.py`                 | Entry point (`python -m app.main`).               |
| `app/services/eve_reader.py`  | Read/parse Suricata EVE JSON (safe when missing). |
| `app/services/database.py`    | SQLite connection + `alerts` schema.              |
| `app/services/alert_service.py`| Honest engine status + alert count for the API.  |
| `app/templates/*.html`        | Dashboard, Alerts, Rule Lab pages.                |
| `app/static/*`                | CSS + vanilla JS front-end.                       |
| `suricata/rules/local.rules`  | Custom lab rules (SID ≥ 1000000).                 |

## API routes (current)

- `GET /` — dashboard page.
- `GET /alerts` — alerts page (empty until ingestion phase).
- `GET /rule-lab` — rule lab page.
- `GET /api/health` — Flask API liveness (NOT the detection engine).
- `GET /api/status` — honest Suricata engine status + stored alert count.

## Honesty guarantees

- `/api/status` reports `suricata_configured: false` until Suricata's EVE JSON
  output actually exists. No fake "active" status is ever shown.
- The `alerts` table is empty until genuine Suricata events are ingested in a
  later phase. No events are fabricated.
