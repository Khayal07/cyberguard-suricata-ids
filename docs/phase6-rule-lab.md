# Phase 6 — Rule Lab and End-to-End Testing

> Beginner-friendly guide. Suricata is the detection engine; everything here only
> **reads** state or **drives harmless local traffic**. Nothing in this phase
> performs detection, edits rules from the web app, or fabricates alerts.

---

## 1. What Phase 6 adds

| Piece | What it is | Detection role |
|-------|------------|----------------|
| `GET /api/rules` | Read-only JSON view of the Suricata rules **file** | None — only displays file text |
| Rule Lab page (`/rule-lab`) | Read-only table of the parsed rules + "how to test" box | None |
| `scripts/start_lab.sh` | Checks Suricata + ports are ready (prints fix commands) | None — read-only checks |
| `scripts/e2e_test.sh` | Automated pipeline test via the API | None — reads API, sends HTTP |
| `scripts/rule_toggle_experiment.sh` | Manual Kali proof that detection depends on the rule | Changes the **Suricata rule**, nothing else |

**Golden rule:** the Rule Lab shows **file state, not proof that Suricata loaded
it.** Only Suricata (e.g. `suricata -T`) can confirm a rule is actually active.

---

## 2. The Rule Lab (`/rule-lab`)

- Backend reads **one fixed path** from the environment variable
  `CYBERGUARD_RULES_PATH` (default `/var/lib/suricata/rules/cyberguard.rules`).
  The path is **never** taken from the HTTP request, so no one can point it at
  another file.
- The parser extracts, per rule line: `sid`, `msg`, `priority`, `classtype`,
  `rev`, and `enabled`. A line starting with `alert` is **enabled**; a line
  starting with `#alert` (the way Phase 3 disabled a rule) is **disabled**.
- If the file is missing, the API returns `file_found: false` and an empty list —
  it never crashes.
- The page polls `/api/rules` every ~3s and renders a read-only table. There are
  **no** toggle/edit buttons and **no** endpoint that writes files or runs
  commands. All text is rendered with `textContent` (XSS-safe).

Example response:

```json
{
  "file_found": true,
  "file_path": "/var/lib/suricata/rules/cyberguard.rules",
  "file_mtime": "2026-11-09T18:00:00+00:00",
  "rules": [
    {"sid": 1000001, "msg": "CyberGuard Test Alert", "priority": 1,
     "classtype": "misc-activity", "rev": 2, "enabled": true},
    {"sid": 1000002, "msg": "CyberGuard Warning Alert", "priority": 2,
     "classtype": "misc-activity", "rev": 2, "enabled": true}
  ],
  "note": "File state, not proof that Suricata loaded it."
}
```

---

## 3. The scripts (run on the Kali VM)

All scripts are **written on Windows and validated on the Kali VM**. They use LF
line endings (enforced by `.gitattributes`) and are marked executable in git.

### 3a. `scripts/start_lab.sh` — readiness check

Checks (does **not** start, never uses `sudo` itself):

1. Suricata running — reads `/tmp/suricata.pid`, then `/proc/<pid>/comm`.
2. Lab HTTP server listening on port 8000.
3. Flask backend listening on port 5000.

For anything missing it prints the **exact** command to fix it. Exit code is `0`
when everything is ready, `1` otherwise.

```bash
bash scripts/start_lab.sh
```

Expected (all ready):

```
[OK] Suricata running (pid 1234, comm=Suricata-Main)
[OK] Lab HTTP server listening on port 8000
[OK] Flask backend listening on port 5000
All lab components are ready. Next: bash scripts/e2e_test.sh
```

### 3b. `scripts/e2e_test.sh` — automated end-to-end test

Talks to the API at `http://127.0.0.1:5000` only. It **never** writes to the DB
or `eve.json`; it reads the API and sends harmless HTTP to the lab server. Uses
`curl` + `python3` for JSON (no `jq`).

Steps and checks:

- **Precondition:** `/api/status` `suricata_process == "verified_running"`,
  else it prints `FATAL` and exits (code 2).
- **A** — `GET /index.html` → wait → total alert count **unchanged**.
- **B** — `GET /cyberguard-test` → poll `/api/alerts` up to 15s → a new
  `signature_id 1000001` alert, total **+1**.
- **C** — `GET /cyberguard-warning` → new `sid 1000002`, total **+1**.
- **D** — wait another window → total **stable** (no duplicates).

Prints a PASS/FAIL table and exits non-zero if any check fails.

```bash
bash scripts/e2e_test.sh
```

### 3c. `scripts/rule_toggle_experiment.sh` — manual proof (Kali only)

Reproduces the Phase 3 proof that **detection depends on the Suricata rule**:
backs up the rules file, comments out sid 1000001, validates with
`suricata -T`, restarts Suricata, sends `/cyberguard-test` and shows **no** new
1000001 alert, then restores the rule, validates, restarts, and shows detection
working again.

Safety features:

- **Refuses** to run if not on Linux.
- Requires an explicit **`y/N`** confirmation before starting.
- **Prints every command** it runs (`+ sudo ...`).
- A **`trap`** always restores the original rules on exit or error.
- Needs `sudo` (to edit the deployed rules and restart Suricata).
- **Never** callable from the dashboard — it is a manual shell script only.

```bash
bash scripts/rule_toggle_experiment.sh
```

---

## 4. Recommended demo order

1. `bash scripts/start_lab.sh` — confirm Suricata + servers are up.
2. In another terminal: `python3 lab/server.py --port 8000`.
3. Open the dashboard and the Rule Lab (`/rule-lab`) in Firefox.
4. `bash scripts/e2e_test.sh` — watch the PASS table and the dashboard counters
   grow.
5. `bash scripts/rule_toggle_experiment.sh` — prove detection depends on the
   rule.

---

## 5. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `start_lab.sh` says Suricata MISSING | Suricata not started | Run the printed `sudo suricata ... -i lo -D --pidfile ...` |
| `e2e_test.sh` prints `FATAL ... suricata_process` | Backend can't verify Suricata (no pidfile / wrong `/proc`) | Start Suricata with `--pidfile /tmp/suricata.pid`; check `CYBERGUARD_SURICATA_PID` |
| Port 5000/8000 shown MISSING | Backend or lab server not running | `python3 -m app.main` / `python3 lab/server.py --port 8000` |
| Rule Lab shows "Rules file not found" | `CYBERGUARD_RULES_PATH` wrong on this host | Point it at the deployed `cyberguard.rules`, or accept it's absent on Windows |
| `e2e_test.sh` B/C fail (no new alert) | Suricata not watching `lo`, or rule disabled | Confirm capture on `lo`; check the rule is enabled in the Rule Lab |
| Totals jump by more than 1 | Other traffic also tripping a rule | Run in a quiet lab; re-check baseline |

---

## 6. Validation status

- **Windows (dev):** `/api/rules` parser + endpoint covered by `tests/test_rules.py`
  (enabled, disabled `#alert`, missing file, malformed line, reordered options,
  endpoint found/missing). Full suite green. Scripts pass `bash -n` and are LF.
- **Kali VM (validated manually by the project owner):**
  - `scripts/start_lab.sh` → all `[OK]`: Suricata pid verified
    (`comm=Suricata-Main`), lab server on port 8000 and backend on port 5000 both
    listening.
  - `scripts/e2e_test.sh` → **PASS 4 / FAIL 0, exit code 0**: A `/index.html` benign,
    no alert (total unchanged at 10); B `/cyberguard-test` → sid 1000001 (total
    10→11); C `/cyberguard-warning` → sid 1000002 (total 11→12); D no duplicates
    (total stable at 12).
  - `scripts/rule_toggle_experiment.sh` → with sid 1000001 disabled, `suricata -T`
    loaded **1 rule** and the sid 1000001 count stayed 7→7; after restore, **2
    rules** loaded and the count went 7→8; the trap restored the original rules file
    (`grep -c '^#alert'` = 0).
  - Rule Lab page `/rule-lab` showed both rules **enabled** (priority 1 and 2,
    rev 2) with the "file state, not proof that Suricata loaded it" notice.
