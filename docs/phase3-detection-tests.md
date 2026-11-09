# Phase 3 — Detection Tests

> **All experiments below were executed and verified manually on the Kali Linux
> 2026.3 VM (VirtualBox).** Nothing here was run on the Windows workstation, and
> no output was invented. Suricata is the only detection engine; these tests
> confirm that genuine traffic produces genuine Suricata alerts in EVE JSON.

---

## What we are testing

The two custom rules (source of truth: `suricata/rules/cyberguard.rules`; active
on the VM at `/var/lib/suricata/rules/cyberguard.rules`):

| sid     | message                  | fires when the HTTP request URI contains |
|---------|--------------------------|------------------------------------------|
| 1000001 | CyberGuard Test Alert    | `/cyberguard-test`                       |
| 1000002 | CyberGuard Warning Alert | `/cyberguard-warning`                    |

**Beginner note:** each rule watches HTTP requests going *to a server* on an
established TCP connection and inspects the **request URI** (the path the client
asks for). Suricata matches the *request*, so the server's response code (even a
404) does not change whether an alert fires.

---

## Test setup (verified manually on the Kali VM)

- **Test web server:** `python3 -m http.server 8000 --bind 127.0.0.1` (served a
  file `index.html`). The `/cyberguard-*` paths return **404** on this server,
  which is fine — Suricata matches the request URI, not the response.
- **Suricata (IDS, loopback capture):**
  ```bash
  sudo suricata -c /etc/suricata/suricata.yaml -i lo -D --pidfile /tmp/suricata.pid
  ```
  Started, then **waited ~10s** before sending requests (so capture was ready).
- **Alert counting** (EVE JSON is cumulative across runs):
  ```bash
  grep '"event_type":"alert"' eve.json \
    | grep -o '"signature":"[^"]*"' | sort | uniq -c
  ```

---

## Results (verified manually on the Kali VM)

| # | Scenario                          | Expected                | Observed                | Result |
|---|-----------------------------------|-------------------------|-------------------------|--------|
| A | `GET /index.html`                 | no alert                | no alert                | PASS   |
| B | `GET /cyberguard-test`            | "CyberGuard Test Alert" | "CyberGuard Test Alert" | PASS   |
| C | `GET /cyberguard-warning`         | "CyberGuard Warning Alert" | "CyberGuard Warning Alert" | PASS |
| D | Disable Test Alert rule, repeat requests | Test Alert count does NOT increase; Warning Alert does | Test Alert `1` (unchanged), Warning Alert `2` | PASS |
| E | Restore Test Alert rule, send `/cyberguard-test` | Test Alert count increases again | Test Alert `2`, Warning Alert `2` | PASS |

Requests were sent with `curl` (observed user agent `curl/8.21.0`).

### D — Disable experiment (proves detection depends on the rule)

The **Test Alert** rule (sid 1000001) was commented out and Suricata restarted,
then the requests were repeated:

```bash
# Stop Suricata, comment the Test Alert rule line with a leading '#', restart.
# (sed was used to prefix the Test Alert rule with '#'.)
grep -c '^#alert' /var/lib/suricata/rules/cyberguard.rules   # 1 while disabled
```

Observed counts afterwards: **Test Alert = 1 (unchanged)**, **Warning Alert = 2**.
Because the Test Alert rule was disabled, no new Test Alert was generated, while
the still-active Warning rule continued to fire. This confirms detection comes
from Suricata's rule, not from Python.

### E — Restore experiment

```bash
# Remove the '#' comment, confirm no rules are disabled, restart Suricata.
grep -c '^#alert' /var/lib/suricata/rules/cyberguard.rules   # 0 after restore
```

Then `GET /cyberguard-test` was sent again. Observed counts: **Test Alert = 2**,
**Warning Alert = 2** — the re-enabled rule fires again. PASS.

---

## Sample of a real EVE alert record (field list only)

A genuine Scenario B/C alert record in `eve.json` contained these fields (no raw
log dump is stored in the repo):

- `event_type`: `alert`
- `timestamp`: ISO-8601 with `-0500` offset (VM timezone)
- `src_ip`: `127.0.0.1`, `dest_ip`: `127.0.0.1`
- `dest_port`: `8000`
- `app_proto`: `http`
- `alert.signature` / `alert.signature_id` (e.g. `CyberGuard Test Alert` / `1000001`)
- `http.url`, `http.http_method`: `GET`, `http.status`: `404`,
  `http.http_user_agent`: `curl/8.21.0`
- a `flow` section (flow/connection metadata)

These are exactly the fields the Python EVE reader will ingest in a later phase.

---

## Notes & limitations (verified manually on the Kali VM)

- The rule disabled in experiment D was the **Test Alert** rule (sid 1000001),
  **not** the Warning rule.
- A separate `suricata -T` re-validation was **not** run after the disable step;
  Suricata nonetheless started successfully afterwards.
- `eve.json` is **cumulative** across Suricata runs, so the counts above are
  running totals, not per-run counts.
- EVE timestamps show a `-0500` timezone offset (the VM clock).
- Capture is on **`lo` only**; `eth0` is not monitored in this setup.

---

## Repo lab server

`lab/server.py` is a purpose-built, harmless localhost-only test server (returns
**200** for `/cyberguard-test` and `/cyberguard-warning`). It was **written on
Windows and has NOT yet been run on the Kali VM** — it will be validated when the
repository is cloned onto the VM. The manual Phase 3 tests above instead used
`python3 -m http.server`.
