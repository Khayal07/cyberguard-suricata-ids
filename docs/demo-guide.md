# CyberGuard Demo Guide (about 10 minutes)

This is a step-by-step script for a live demo on the Kali VM. Follow it in order.
Each step has the exact command and what you should see.

> Keep it calm. Each step shows one idea: Suricata detects, Python only shows.

---

## Before you start (prerequisites)

You need three terminals open in the project folder, and Suricata installed.

- Terminal 1: the lab web server.
- Terminal 2: the CyberGuard backend.
- Terminal 3: Suricata (and your test commands).

Start the lab server and the backend:

```bash
# Terminal 1
python3 lab/server.py --port 8000

# Terminal 2
source .venv/bin/activate
python -m app.main
```

Start Suricata (Terminal 3):

```bash
sudo suricata -c /etc/suricata/suricata.yaml -i lo -D --pidfile /tmp/suricata.pid
```

Check that everything is ready:

```bash
bash scripts/start_lab.sh
```

Expected output (all green):

```
[OK] Suricata running (pid 1234, comm=Suricata-Main)
[OK] Lab HTTP server listening on port 8000
[OK] Flask backend listening on port 5000
All lab components are ready. Next: bash scripts/e2e_test.sh
```

---

## Step 1 — Open the dashboard (1 min)

Open http://127.0.0.1:5000/ in Firefox on the VM.

Point out:
- The **Suricata Engine** card shows "SURICATA RUNNING (verified)".
- The summary cards: Total, Critical (sev 1), High (sev 2).
- The severity chart, the top source IPs, and the recent alerts table.

Say: "The status is honest. The backend checked the Suricata process. It did not
guess."

---

## Step 2 — A benign request makes no alert (1 min)

```bash
curl http://127.0.0.1:8000/index.html
```

Wait a few seconds, then refresh the dashboard.

Expected: the total alert count does **not** change. No new alert appears.

Say: "This request does not match any rule. So Suricata writes nothing. Python has
nothing new to show."

---

## Step 3 — Trigger the test alert (1 min)

```bash
curl http://127.0.0.1:8000/cyberguard-test
```

Wait a few seconds, then refresh.

Expected: a new alert appears: **"CyberGuard Test Alert"**, SID **1000001**,
severity **1 (Critical)**.

If Telegram is on, you also get a Telegram message that ends with
"Status: Detected by Suricata".

---

## Step 4 — Trigger the warning alert (1 min)

```bash
curl http://127.0.0.1:8000/cyberguard-warning
```

Wait a few seconds, then refresh.

Expected: a new alert appears: **"CyberGuard Warning Alert"**, SID **1000002**,
severity **2 (High)**.

---

## Step 5 — Open an alert detail panel (1 min)

Click one alert row in the table.

Point out the fields: source IP and port, destination IP and port, protocol,
HTTP URL, HTTP method, status, user agent, and the time in UTC.

Say: "All of this came from Suricata. Python just stored it and showed it."

---

## Step 6 — Show the Rule Lab page (1 min)

Open http://127.0.0.1:5000/rule-lab

Point out:
- The table shows both rules: SID, message, priority, class, revision, and an
  enabled/disabled badge.
- The note says: **"File state, not proof that Suricata loaded it."**

Say: "This page only reads the rules file. It cannot change rules. Only Suricata
can confirm a rule is really active."

---

## Step 7 — Run the automated end-to-end test (1 min)

```bash
bash scripts/e2e_test.sh
```

Expected: a results table with **PASS: 4   FAIL: 0**, and the script exits 0.

The four checks:
- A: benign `/index.html` — total unchanged.
- B: `/cyberguard-test` — new SID 1000001, total +1.
- C: `/cyberguard-warning` — new SID 1000002, total +1.
- D: no duplicates — total stays the same.

---

## Step 8 — Prove detection depends on the rule (2 min)

```bash
bash scripts/rule_toggle_experiment.sh
```

It asks "Proceed? [y/N]". Type `y`.

The script turns off rule 1000001, restarts Suricata, and sends the request.

Expected SUMMARY:

```
rule DISABLED: 7 -> 7  (no new 1000001 alert => detection depends on the rule)
rule ENABLED : 7 -> 8  (new 1000001 alert => detection works again)
```

Say: "When the rule is off, no alert. When it is on, the alert comes back. So the
detection is real. Python did not fake it."

The script always restores the original rules at the end.

---

## Step 9 — Stop Suricata: honest "NOT RUNNING" (1 min)

```bash
sudo kill "$(cat /tmp/suricata.pid)"
```

Refresh the dashboard.

Expected: the engine card shows **"SURICATA NOT RUNNING (verified)"** and a warning
banner. New alerts stop.

Say: "The app does not hide this. If the engine is down, it tells the truth."

---

## Step 10 — Stop the backend: "API unavailable" (1 min)

In Terminal 2, press `Ctrl+C` to stop the backend.

Refresh the dashboard.

Expected: a banner says the API is unavailable. The browser cannot reach the
backend.

Say: "This is a different state from Suricata being down. The dashboard shows each
problem clearly."

To finish, restart Suricata and the backend if you want the demo running again.

---

## If something fails

| Problem                                   | Likely cause                         | Fix                                                        |
|-------------------------------------------|--------------------------------------|------------------------------------------------------------|
| `start_lab.sh` says Suricata MISSING      | Suricata not started                 | Run the printed `sudo suricata ... -i lo -D --pidfile ...` |
| Dashboard shows "API unavailable"         | Backend not running                  | Start it: `python -m app.main`                             |
| Dashboard shows "SURICATA UNVERIFIED"     | No `/proc` (for example on Windows)  | Run on the Kali VM; it is honest, not an error             |
| `e2e_test.sh` prints `FATAL ... suricata_process` | Backend cannot verify the engine | Start Suricata with `--pidfile /tmp/suricata.pid`          |
| No alert after `/cyberguard-test`         | Suricata not watching `lo`, or rule off | Check capture on `lo`; check the Rule Lab badge         |
| Totals jump by more than 1                | Other traffic also matched a rule    | Use a quiet lab; re-check the baseline                     |
| Telegram message did not arrive           | Token/chat id not set, or no internet | Check `.env`; run `python -m app.main telegram-test`       |
