# CyberGuard — Presentation Outline

This is the slide-by-slide outline for the final presentation. Each slide has a
title, up to five short bullets, speaker notes, and which screenshot or live demo
step to show.

> Note: this outline was turned into `CyberGuard_Presentation.pptx` in this folder
> (15 slides, dark theme, speaker notes, embedded screenshots, and a native-shape
> architecture diagram). You can also paste this outline into any slide tool.

---

## Slide 1 — Title

- CyberGuard
- A Suricata-Powered Network IDS and Monitor
- University Information Security Project
- Student: Khayal
- Suricata detects. Python only shows.

**Speaker notes:** "Hello. My project is CyberGuard. It is a network security
monitor. The big idea is simple: Suricata finds the attacks, and my Python code
only shows them."

**Show:** title slide (no screenshot).

---

## Slide 2 — The problem

- Networks face many attacks.
- Teams need to see suspicious traffic fast.
- Many demos mix detection and display.
- Then it is hard to trust the result.
- We want clear, honest detection.

**Speaker notes:** "Many small demos make their own alerts in the display code. So
you cannot tell what really found the attack. I wanted a clean design that is easy
to trust."

**Show:** no screenshot.

---

## Slide 3 — The main idea

- Suricata is the only detection engine.
- Python never detects anything.
- Python reads, stores, and shows alerts.
- If Suricata stops, new alerts stop.
- This is the correctness test.

**Speaker notes:** "This is the heart of my project. One engine does detection.
Everything else just presents the results. If I stop Suricata, new alerts must
stop. I will prove that later."

**Show:** no screenshot.

---

## Slide 4 — What is an IDS?

- IDS = Intrusion Detection System.
- It watches traffic and warns.
- It detects but does not block.
- IPS can block; we are IDS only.
- Suricata is a free, open-source IDS.

**Speaker notes:** "An IDS watches and warns. It does not block. A tool that blocks
is an IPS. I chose IDS so I never drop good traffic by mistake."

**Show:** no screenshot.

---

## Slide 5 — Architecture

- Traffic → Suricata → EVE JSON.
- EVE JSON → Python reader → SQLite.
- SQLite → Flask API → Dashboard.
- Optional Telegram for new alerts.
- One direction, simple and clear.

**Speaker notes:** "Here is the data flow. Suricata writes alerts to a file called
EVE JSON. Python reads the new lines, stores them in SQLite, and serves an API. The
dashboard shows them."

**Show:** the Mermaid architecture diagram from the README.

---

## Slide 6 — Technology stack

- Suricata 8.0.7 on Kali Linux.
- Python 3 and Flask.
- SQLite for storage.
- HTML, CSS, vanilla JavaScript.
- Telegram Bot API (optional).

**Speaker notes:** "I kept the stack small. No React, no Docker, no cloud. Just a
real IDS, Python, SQLite, and plain web code. It is easy to read and maintain."

**Show:** no screenshot.

---

## Slide 7 — The dashboard

- Honest engine status card.
- Cards: total, critical, high.
- Severity chart and top lists.
- Alert table with filters and paging.
- Click a row for full details.

**Speaker notes:** "This is the dashboard. The status card is honest: it checked
the Suricata process. The cards and chart give a quick view. The table lists the
alerts."

**Show:** Screenshot 1 — dashboard overview (`docs/screenshots/01-dashboard-overview.png`).

---

## Slide 8 — An alert in detail

- Click a row to open details.
- Source and destination IP and port.
- Protocol and HTTP fields.
- Severity and signature.
- All of it came from Suricata.

**Speaker notes:** "When I click an alert, I see all its fields. The source, the
destination, the URL, the time. My code did not create any of this. It only stored
what Suricata wrote."

**Show:** Screenshot 2 — alert detail panel (`docs/screenshots/02-alert-detail.png`).

---

## Slide 9 — The two rules

- Rule 1000001: URL has `/cyberguard-test`.
- Priority 1 → severity 1 (Critical).
- Rule 1000002: URL has `/cyberguard-warning`.
- Priority 2 → severity 2 (High).
- Both match HTTP requests to a server.

**Speaker notes:** "I wrote two simple rules. One fires on a test URL and is
critical. One fires on a warning URL and is high. The priority in the rule sets the
severity in the alert."

**Show:** Screenshot 3 — Rule Lab page (`docs/screenshots/03-rule-lab.png`).

---

## Slide 10 — Live demo: detection

- Benign request → no alert.
- `/cyberguard-test` → SID 1000001.
- `/cyberguard-warning` → SID 1000002.
- Alerts appear on the dashboard.
- Suricata did all the detection.

**Speaker notes:** "Now a quick live demo. First a normal request: nothing happens.
Then two test requests: two alerts appear. This is live, and Suricata found them."

**Show:** live demo — Demo Guide steps 2 to 4.

---

## Slide 11 — Automated end-to-end test

- One script sends real traffic.
- It checks the API after each step.
- PASS 4 / FAIL 0, exit 0.
- Benign no alert; two alerts; no duplicates.
- Repeatable proof the pipeline works.

**Speaker notes:** "I also have a script that does this automatically. It sends
traffic and checks the API. It shows four passes and zero fails. So the whole
pipeline works end to end."

**Show:** Screenshot 4 — e2e_test PASS table (`docs/screenshots/04-e2e-pass-table.png`).

---

## Slide 12 — Proof: detection depends on the rule

- Turn off rule 1000001.
- Send the request → no new alert.
- Turn the rule back on.
- Send again → the alert returns.
- Python did not fake it.

**Speaker notes:** "This is my strongest proof. I turn the rule off and the alert
stops. I turn it back on and the alert comes back. So the detection is real and
depends on Suricata."

**Show:** Screenshot 5 — rule_toggle SUMMARY output (`docs/screenshots/05-rule-toggle-summary.png`).

---

## Slide 13 — Honest status and safety

- "Running" only after a real check.
- Stop Suricata → "NOT RUNNING".
- Stop backend → "API unavailable".
- No commands run from the web app.
- Dashboard is XSS-safe.

**Speaker notes:** "The app is honest. If the engine is down, it says so. If the
backend is down, the browser shows that too. The web app cannot run commands, and
it is safe from XSS."

**Show:** Screenshot 7 — Suricata NOT RUNNING banner (`docs/screenshots/07-suricata-not-running.png`).

---

## Slide 14 — Optional Telegram alerts

- Off unless token and chat id are set.
- Sends a short plain-text message.
- Only new, serious alerts.
- No startup flood; rate limited.
- Token stays only in local `.env`.

**Speaker notes:** "I added optional Telegram alerts. If I set a token, I get a
message for each new serious alert. It is plain text, it never floods, and the
token is never committed."

**Show:** Screenshot 6 — Telegram alerts on a phone (`docs/screenshots/06-telegram-alerts.jpg`).

---

## Slide 15 — Limitations and future work

- Loopback only; two rules; IDS only.
- Rate-limit and revoke: unit-tested only.
- Dev server, no login (localhost only).
- Next: more rules, real interface, login.
- Next: Docker, suricata-update.

**Speaker notes:** "The project has limits. It watches loopback, has two rules, and
does not block. Next I would add more rules, a real interface, a login, and Docker.
Thank you. I am happy to answer questions."

**Show:** no screenshot (closing slide).
