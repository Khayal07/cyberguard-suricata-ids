# CyberGuard Architecture

This document explains how CyberGuard works. It uses simple words. Technical
terms are explained the first time they appear.

---

## 1. The main principle

**Suricata is the only detection engine. Python never detects anything.**

Suricata reads the traffic, checks it against rules, and writes alerts. Python
only reads those alerts, stores them, and shows them. If Suricata stops, new
alerts stop. This is the most important rule in the whole project.

---

## 2. Data flow

```
 Network traffic or PCAP
          │
          ▼
   ┌───────────────┐    writes     ┌───────────────┐
   │  SURICATA IDS  │ ─────────────▶│   eve.json    │  (one JSON per line)
   │  rules engine  │               │  (EVE output) │
   └───────────────┘               └───────┬───────┘
                                           │ read only (never generated)
                                           ▼
   ┌──────────────────────────────────────────────────┐
   │                 PYTHON / FLASK                     │
   │  eve_reader    → read new EVE JSON lines           │
   │  alert_service → normalize + store + status        │
   │  database      → save alerts in SQLite             │
   │  telegram      → optional message for new alerts   │
   │  app (routes)  → serve the pages and the JSON API  │
   └───────────────────────┬──────────────────────────┘
                           │ HTTP (localhost only)
                           ▼
   ┌──────────────────────────────────────────────────┐
   │   Dashboard (HTML + CSS + vanilla JavaScript)     │
   │   fetches the API and shows the alerts            │
   └──────────────────────────────────────────────────┘
```

**PCAP** is a saved file of captured network packets. Suricata can read live
traffic or a PCAP file. Both give the same kind of alerts.

---

## 3. Components

| Component                        | What it does                                               |
|----------------------------------|-----------------------------------------------------------|
| `app/config.py`                  | Reads settings from the environment. No secrets in code.  |
| `app/__init__.py`                | Builds the Flask app and registers the routes.            |
| `app/main.py`                    | Start point: `serve`, `ingest-once`, `telegram-test`.     |
| `app/services/eve_reader.py`     | Reads new EVE JSON lines. Keeps only alert events.        |
| `app/services/alert_service.py`  | Normalizes time, stores alerts, reports status, runs the worker. |
| `app/services/database.py`       | SQLite tables, queries, and stats.                        |
| `app/services/rule_service.py`   | Reads the rules file (read only). Makes no decision.      |
| `app/services/telegram_notifier.py` | Optional Telegram alerts for new, serious alerts.      |
| `app/templates/*.html`           | Dashboard, Alerts, and Rule Lab pages.                    |
| `app/static/js/dashboard.js`     | Fetches the API and draws the UI (XSS-safe).              |
| `suricata/rules/cyberguard.rules`| The two custom rules (source of truth).                   |

---

## 4. Database schema (SQLite)

The database file is `data/cyberguard.db`. It is git-ignored. It is only a cache:
if you delete it, the app rebuilds it and re-reads the alerts.

**Table `alerts`** — one row per genuine Suricata alert. Main columns:

| Column                     | Meaning                                               |
|----------------------------|-------------------------------------------------------|
| `id`                       | Row number (primary key).                             |
| `timestamp_raw`            | The time as Suricata wrote it (for example `-0500`).  |
| `timestamp_utc`            | The same time changed to UTC.                         |
| `flow_id`                  | Suricata's id for the network flow.                   |
| `src_ip`, `src_port`       | Where the traffic came from.                          |
| `dest_ip`, `dest_port`     | Where the traffic went.                               |
| `proto`, `app_proto`       | Protocol (for example TCP) and app protocol (http).   |
| `signature`                | The rule message (for example "CyberGuard Test Alert").|
| `signature_id`             | The rule number (SID), for example 1000001.           |
| `severity`                 | How serious the alert is (1 is most serious).         |
| `category`                 | The rule class (may be empty).                         |
| `http_*`                   | HTTP details (url, method, status, user agent, host). |
| `in_iface`                 | The capture interface (for example `lo`).             |
| `raw_json`                 | The original EVE line (kept in the DB only).          |

There is a **UNIQUE** rule on `(flow_id, timestamp_raw, signature_id)`. This stops
the same alert from being stored twice.

**Table `ingest_state`** — a single row. It remembers where the reader stopped:
the file `inode`, the `byte_offset`, the invalid-line count, and the last times.

> An **inode** is a number the file system gives to a file. If the file is
> replaced, the inode changes. We use this to notice a new log file.

---

## 5. How the reader avoids duplicates and handles rotation

CyberGuard reads EVE JSON **incrementally**. That means it only reads the new part
of the file each time, not the whole file.

- It saves a **byte offset** (how far it read) and the file **inode**.
- Next time, it starts reading from that offset. Old lines are not read again.
- It also has the UNIQUE database rule. So even if a line is read twice, it is
  stored only once. This is a second safety net.

**Rotation and truncation:**

- If the inode changes, the log file was replaced (rotated). The reader starts
  from offset 0 on the new file.
- If the file is shorter than the saved offset, it was truncated. The reader also
  starts from 0.
- If the file is missing, the reader returns a clear "eve_missing" state. It does
  not crash.
- A partial last line (no newline yet) is not read. The reader waits for the full
  line next time.

---

## 6. Status model (honest status)

The dashboard shows three different states. They mean different things.

| State on screen                | What it means                                            |
|--------------------------------|----------------------------------------------------------|
| **API unavailable**            | The browser cannot reach the Flask backend at all.       |
| **Suricata NOT running**       | The backend is up, but it checked and Suricata is stopped.|
| **Suricata running (verified)**| The backend checked the process and Suricata is alive.    |

How we check Suricata honestly:

1. We read the pidfile at `/tmp/suricata.pid`.
2. We read `/proc/<pid>/comm` to get the process name.
3. If the name contains "Suricata", we report **verified_running**.

We never say "running" just because the EVE file exists. On Windows there is no
`/proc`, so the status is **unverified** (honest, not a guess).

---

## 7. Design decisions and why

- **Why Suricata only?** The project is about using a real IDS. If Python also
  guessed attacks, the result would not be trustworthy. One engine keeps it clear.
- **Why SQLite?** It is a single file. It needs no server. It is easy for a small
  project and easy to reset.
- **Why read EVE JSON instead of a Suricata plugin?** Reading the file is simple
  and safe. It also keeps Python fully separate from detection.
- **Why a byte offset plus a UNIQUE key?** The offset is fast and avoids re-reading.
  The UNIQUE key is a strong backup so duplicates can never be stored.
- **Why plain HTML and vanilla JS?** It is small, has no build step, and is easy to
  read for a beginner. It also makes XSS-safe rendering simple.
- **Why is Telegram optional and isolated?** Alerts must work even with no internet.
  So Telegram is off by default and can never crash or slow the reader.

---

## 8. What Python must never do

- It must never create an alert on its own.
- It must never mark traffic as an attack.
- It must never run a shell command from a web request.
- It must never trust a file path that comes from the browser.

These rules keep Suricata as the one and only detection engine.
