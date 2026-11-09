# CyberGuard Lab

This folder holds the **authorized local laboratory** used to generate controlled
traffic that exercises the Suricata detection rules.

## Rules of engagement

- All experiments run only in an isolated, authorized local environment (the Kali
  VM, loopback interface).
- Use **harmless HTTP markers** and controlled traffic only.
- **Do not** perform external scanning, unauthorized penetration testing,
  credential attacks, or any destructive activity.
- Never expose the lab server or the Flask app publicly; keep them bound to
  `localhost` (`127.0.0.1`).

## `server.py` — harmless lab HTTP server

A minimal standard-library HTTP server bound to `127.0.0.1` only. It serves fixed
in-memory responses and does not write files, run shell commands, or list
directories.

```bash
python lab/server.py --port 8000
```

| Request                  | Response | Purpose                              |
|--------------------------|----------|--------------------------------------|
| `GET /`                  | 200      | index page                           |
| `GET /index.html`        | 200      | index page                           |
| `GET /cyberguard-test`   | 200      | trips rule sid 1000001 (Test Alert)  |
| `GET /cyberguard-warning`| 200      | trips rule sid 1000002 (Warning Alert)|
| anything else            | 404      | —                                    |

> **Status:** `server.py` was **written on Windows and has NOT yet been run on
> the Kali VM**; it will be validated when the repo is cloned there. The manual
> Phase 3 detection tests used `python3 -m http.server` instead.

## How a detection test works

1. Start Suricata in IDS mode capturing on `lo` (see
   [`../docs/suricata-setup.md`](../docs/suricata-setup.md)).
2. Start a local HTTP server on `127.0.0.1:8000`.
3. Send a request whose URI contains `/cyberguard-test` or `/cyberguard-warning`
   (e.g. with `curl`).
4. Suricata matches the request URI and writes a genuine alert to
   `/var/log/suricata/eve.json`.

Full results and the PASS/FAIL table are in
[`../docs/phase3-detection-tests.md`](../docs/phase3-detection-tests.md).

Nothing in this folder performs detection — detection happens only inside
Suricata.
