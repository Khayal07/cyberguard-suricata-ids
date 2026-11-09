# PROJECT_MEMORY.md — CyberGuard Persistent Memory

> Single source of truth for project state. Update after every meaningful change
> and before completing each phase. Be specific — record *what*, *where*, *how it
> works*, and *how it was verified*.

**Last updated:** 2026-11-09
**Current phase:** Phase 0 — Initialization (COMPLETE)

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
| OS (engine host) | Ubuntu Linux (WSL2 / VM / native — TBD)      |
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
├── .git/
├── .gitignore          # excludes secrets, venvs, logs, DBs, PCAPs, caches
├── .env.example        # placeholder env vars (no real secrets)
├── CLAUDE.md           # permanent instructions for every session
└── PROJECT_MEMORY.md   # this file
```

No application code, Suricata config, or database exists yet (by design — Phase 0
is initialization only).

---

## 5. Development Environment

- **Main workstation:** Windows 11 + VS Code.
- **Linux environment for Suricata:** NOT yet chosen. Options under consideration:
  Ubuntu WSL2 (preferred for simplicity), Ubuntu VM, or native Ubuntu. To be
  decided in a later phase.
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

None yet. Planned modules (subject to refinement):

- `reader` — read/tail EVE JSON, parse event lines.
- `store` — SQLite schema + insert/query helpers.
- `app` — Flask application and API endpoints.
- `notify` — optional Telegram notifications (final phase).

---

## 11. API Endpoints

None yet. To be documented as implemented (method, path, params, response shape).

---

## 12. Database Schema

None yet. SQLite schema (tables, columns, indexes) will be recorded here when the
storage layer is built.

---

## 13. Dashboard Components

None yet. Will record pages, key DOM components, and how they fetch/render data.

---

## 14. Implemented Functionality

**Phase 0 (complete):**
- Initialized repository documentation and guardrails.
- Created `.gitignore`, `CLAUDE.md`, `PROJECT_MEMORY.md`, `.env.example`.
- Verified Git identity, remote, and branch.

No application functionality implemented yet.

---

## 15. Commands Used to Run the Application

Not applicable yet. Will record exact run commands (Suricata start command, Flask
run command, dashboard access URL) as they are implemented.

---

## 16. Tests Performed and Actual Results

**Phase 0:**
- `git status` → fresh repo, branch `main`, no commits yet. ✅
- `git remote -v` → `origin` = `https://github.com/Khayal07/cyberguard-suricata-ids.git`. ✅
- `git config user.name` / `user.email` → `Khayal07` / `khayal.izada39@gmail.com`. ✅
- `git ls-remote origin` → exit 0 (remote reachable, auth OK; empty remote). ✅
- Commit hash for Phase 0: _recorded in the Phase 0 completion report / git log._

---

## 17. Errors Encountered and How They Were Fixed

None in Phase 0.

---

## 18. Known Limitations

- Linux/Suricata environment not yet selected or installed.
- No live traffic validated yet; PCAP fallback may be used.
- Dashboard not secured for public exposure (localhost-only by design).

---

## 19. Current Development Phase

**Phase 0 — Initialization: COMPLETE.** Awaiting the user's explicit Phase 1 prompt.

---

## 20. Exact Next Steps

Wait for the user's next phase prompt. Likely Phase 1 candidates (not started until
explicitly requested):
1. Select and prepare the Linux environment (WSL2 / VM / native Ubuntu).
2. Install Suricata and document version + config paths.
3. Configure EVE JSON output and a minimal custom rule for lab testing.

Do **not** begin any of these until the user explicitly provides the phase.

---

## Phase Plan (agreed roadmap — reference only, implement one at a time)

- **Phase 0 — Initialization:** repo docs, `.gitignore`, memory files, Git/remote
  verification. ✅
- **Phase 1 — Linux + Suricata setup:** choose environment, install Suricata,
  document config paths and run mode.
- **Phase 2 — Detection rules + EVE JSON:** custom lab rules, verify genuine events
  land in EVE JSON from controlled traffic/PCAP.
- **Phase 3 — Python ingestion + storage:** read EVE JSON, define SQLite schema,
  store genuine events.
- **Phase 4 — Flask API:** endpoints serving stored events/metrics.
- **Phase 5 — Dashboard:** HTML/CSS/JS UI consuming the API.
- **Phase 6 — Telegram notifications (optional):** alerting on new events.

Each phase: implement → test → review → update this file → commit/push → report →
STOP.
