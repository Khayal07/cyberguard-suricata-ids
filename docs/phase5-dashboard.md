# Phase 5 — SOC Dashboard

A dark-themed Security Operations Center dashboard built with **plain HTML, CSS,
and vanilla JavaScript** (no frameworks, no CDN). It displays **only** data
returned by the Flask API — it performs no detection and fabricates nothing.
Suricata remains the sole detection engine.

## Pages

- **`/` (Dashboard)** — summary cards (Total Alerts, Critical sev 1, High sev 2,
  Suricata Engine status), a hand-built inline-SVG severity distribution chart,
  Top Source IPs, Top Signatures, and a Recent Alerts table with search/filters,
  pagination, and a click-to-open alert detail panel.
- **`/alerts` (Alerts)** — the same alerts table (filters, pagination, detail
  panel) as a focused full-list view. Shares `dashboard.js`.
- **`/rule-lab` (Rule Lab)** — unchanged placeholder (Phase 6).

## Data source

| Endpoint | Used for |
|----------|----------|
| `GET /api/status` | Suricata Engine card + unavailable/unverified banners |
| `GET /api/stats`  | Summary cards, severity chart, top IPs, top signatures |
| `GET /api/alerts` | Recent alerts table (filters, pagination, detail) |

The rules were updated to add `priority` + `classtype` (rev:2) and **validated on
the Kali VM**: `suricata -T` loaded 2 rules (0 failed); after restart,
`/cyberguard-test` produced **severity 1** (sid 1000001) and `/cyberguard-warning`
produced **severity 2** (sid 1000002), populating the Critical/High cards. The
older 8 alerts (written under rev:1) remain **severity 3 / "uncategorized"** — EVE
records are historical and are not rewritten.

## Safety / correctness

- **XSS-safe:** every dynamic value is rendered with `textContent` or DOM nodes.
  There is **no `innerHTML`/`insertAdjacentHTML`/`document.write`** with data, so
  attacker-controlled fields (HTTP URL, user agent, hostname) cannot inject
  markup. Verified by `grep` and `node --check`.
- **No raw payload:** the API omits `raw_json`; the detail panel shows only the
  structured fields.
- **Honest status:** the Suricata card reflects the verified process state
  (`verified_running` / `verified_not_running` / `unverified`) — never a fake
  "active" state. On a host without `/proc` (Windows) it shows `UNVERIFIED`.
- **Polling:** every ~3s via `fetch`. Background refreshes do not show the loading
  row (no flicker) and keep the last rows if a poll fails; the initial load and
  filter/page changes do show a loading state.
- **States handled:** loading, empty ("No alerts match…"), API-failure banner,
  and Suricata unavailable/unverified banner.

## Automated tests

No backend Python changed in Phase 5 (dashboard is front-end + a rules-file edit),
so the existing suite still applies: `pytest -q` → **34 passed**. The API shapes
the dashboard depends on (`/api/status`, `/api/stats`, `/api/alerts` incl. filters
and pagination) are already covered by `tests/test_api.py`.

## Local verification performed (Windows, no Suricata)

Populated a scratch DB from the real fixtures and served the app:

```bash
CYBERGUARD_EVE_PATH=tests/fixtures/eve_alerts_sample.jsonl \
CYBERGUARD_DB_PATH=<scratch>/cg.db python -m app.main ingest-once   # read 2, inserted 2
FLASK_ENV=production FLASK_PORT=5099 CYBERGUARD_DB_PATH=<scratch>/cg.db python -m app.main
```

- `GET /` and `GET /alerts` → HTTP 200.
- `GET /api/stats` → `{total:2, by_severity:{"3":2}, by_signature:{…}, by_src_ip:{"127.0.0.1":2}, last_24h:2}`.
- `GET /api/alerts?severity=3` → count 2; `GET /api/alerts?from=2026-11-10` → count 0.
- `/api/alerts` response contains **no** `raw_json`.
- `GET /api/status` → `suricata_process = "unverified"` (honest on Windows).

## Manual test checklist (run in a browser — e.g. Kali Firefox)

- [ ] Dashboard loads at `http://127.0.0.1:5000/` with the dark SOC theme.
- [ ] Summary cards show Total / Critical / High and the Suricata Engine pill.
- [ ] With live Suricata running, the engine pill shows **"SURICATA RUNNING
      (verified)"**; stop Suricata → it shows **NOT RUNNING** and the warn banner
      appears.
- [ ] Severity distribution chart renders bars per severity with counts.
- [ ] Top Source IPs and Top Signatures lists populate with bars.
- [ ] Recent Alerts table lists alerts newest-first with severity badges.
- [ ] Clicking a row opens the detail panel with all fields; Esc / × closes it.
- [ ] Filters work: severity, signature, source IP, search (q), and From/To dates.
- [ ] Pagination: Next/Prev move through pages; buttons disable at the ends.
- [ ] Generate a new lab alert (`/cyberguard-test`) → it appears within ~3s
      without a full-page reload or visible flicker.
- [ ] Stop the backend → the API-failure banner appears and the last data stays.
- [ ] Inject a marker in a URL (e.g. `/cyberguard-test?x=<b>hi</b>`) → the detail
      panel shows it as literal text (no bold), confirming XSS-safe rendering.

## Kali VM validation (COMPLETE — verified manually)

- `sudo suricata -T -c /etc/suricata/suricata.yaml -v` → **2 rules loaded, 0
  failed** (rev:2). Suricata restarted.
- New requests produced genuine alerts: `/cyberguard-test` → **severity 1**
  (sid 1000001), `/cyberguard-warning` → **severity 2** (sid 1000002).
- Dashboard in Kali Firefox showed **Total 10, Critical 1, High 1**, the severity
  distribution chart, top source IPs / signatures, the filterable paginated alerts
  table, and **"SURICATA RUNNING (verified)"**.
- The older 8 alerts (written under rev:1) remained severity 3 — historical EVE
  records are not rewritten.
