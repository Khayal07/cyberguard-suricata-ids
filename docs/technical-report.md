# CyberGuard: A Suricata-Powered Network Intrusion Detection and Monitoring System

**Technical Report — University Information Security Project**

---

## Abstract

CyberGuard is a network security monitor. It uses Suricata, a real IDS, as its only
detection engine. Suricata reads traffic, checks it against rules, and writes
alerts to EVE JSON. A Python backend reads those alerts, stores them in SQLite, and
serves them through a small Flask API. A simple web dashboard shows the alerts.
This report explains the problem, the goals, the design, the work done in each
phase, and the test results. It also lists the limits and future work.

---

## 1. Introduction

Networks face many attacks. Teams need tools that watch traffic and warn them
about suspicious activity. One common tool is an IDS (Intrusion Detection System).
An IDS reads traffic and raises an alert when it sees a known bad pattern.

CyberGuard is a student project that uses an IDS in a clear and honest way. The
main idea is strict: Suricata does all the detection, and Python never detects
anything. Python only reads, stores, and shows what Suricata found. This makes the
results easy to trust.

---

## 2. Problem statement

Many small monitoring demos mix detection and display in one program. Then it is
hard to say what really found the attack. If the display code also makes alerts,
the demo can look good but prove nothing.

The problem we solve is this: build a monitor where the detection is clearly done
by a real engine, and the rest of the system only presents the results. If the
engine stops, new alerts must stop too. This is the test of a correct design.

---

## 3. Objectives

1. Use Suricata as the only detection engine.
2. Read Suricata's real EVE JSON output with Python.
3. Store genuine alerts in SQLite with no duplicates.
4. Serve the alerts through a small Flask API.
5. Show the alerts on a simple, safe dashboard.
6. Report honest status (never fake a "running" engine).
7. Add optional Telegram alerts without breaking the core.
8. Prove the detection is real with a repeatable experiment.

---

## 4. System architecture

The data flows in one direction:

```
Network traffic -> Suricata -> EVE JSON -> Python reader -> SQLite -> Flask API -> Dashboard
                                                                   -> optional Telegram
```

Suricata inspects the traffic on the loopback interface. It writes alerts to
`/var/log/suricata/eve.json`. The Python reader reads new lines from that file. It
keeps only alert events. It changes the timestamp to UTC and stores each alert in
SQLite. The Flask API serves the alerts as JSON. The dashboard fetches the API and
draws the cards, chart, and table. If Telegram is set up, Python sends a short
message for each new serious alert.

The system host for Suricata is Kali Linux 2026.3 in a VirtualBox VM. The code was
written on Windows and tested on both sides: unit tests on Windows, and the live
end-to-end flow on the Kali VM.

A full description of the components, the database schema, the duplicate and
rotation logic, and the status model is in
[`architecture.md`](architecture.md).

---

## 5. Implementation by phase

The project was built in phases. Each phase was tested and recorded before the
next one started.

- **Phase 0 — Foundation.** Set up the repository, the `.gitignore`, and the memory
  files. Checked the Git identity and remote.
- **Phase 1 — Backend shell.** Built the Flask app factory, the config from the
  environment, the EVE reader, the SQLite layer, and honest status endpoints.
- **Phase 2 — Suricata setup.** Installed Suricata 8.0.7 on the Kali VM in IDS
  mode. Pointed the config at our rules file. Confirmed EVE JSON was written.
- **Phase 3 — Detection tests.** Sent lab traffic and confirmed genuine alerts for
  SID 1000001 and SID 1000002. Ran a first disable/restore check.
- **Phase 4 — EVE integration.** Connected the backend to real EVE JSON. Added the
  incremental reader, dedup, the background worker, and the alerts/stats API.
- **Phase 5 — Dashboard.** Built the dark SOC dashboard with cards, a severity
  chart, top lists, filters, paging, and an alert detail panel. Raised the rules to
  rev 2 (priority and class).
- **Phase 6 — Rule Lab and tests.** Added a read-only rules view and three Kali
  scripts: a readiness check, an end-to-end test, and the rule toggle experiment.
- **Phase 7 — Optional Telegram.** Added a standard-library Telegram notifier with
  dedup, a severity filter, rate limiting, and full failure isolation.
- **Phase 8 — Documentation.** Wrote this report, the README, the demo guide, the
  Q&A, and the slide outline.

---

## 6. Testing and results

All numbers below are recorded results, not estimates.

**Unit tests (Windows, no Suricata, no network):**
- `pytest` reports **57 tests passed**.
- The tests cover EVE parsing, invalid and partial lines, non-alert events,
  dedup, rotation and truncation, the SQLite layer, the API (status, alerts,
  stats), the read-only rules parser, and the Telegram logic with a mocked sender.

**Phase 4 end-to-end (Kali VM, live Suricata 8.0.7):**
- `ingest-once` read 6 real alerts and inserted 6 (0 duplicates, 0 invalid).
- `/api/status` reported `verified_running`.
- The dashboard showed "SURICATA RUNNING (verified)".
- The background worker stored new live alerts (count grew from 6 to 8).

**Phase 5 end-to-end (Kali VM):**
- `suricata -T` loaded 2 rules, 0 failed (rev 2).
- `/cyberguard-test` produced severity 1 (SID 1000001).
- `/cyberguard-warning` produced severity 2 (SID 1000002).

**Phase 6 end-to-end (Kali VM):**
- `start_lab.sh` showed all `[OK]`.
- `e2e_test.sh` reported **PASS 4 / FAIL 0** (exit 0): benign request no alert
  (total 10), test alert (10 to 11), warning alert (11 to 12), no duplicates
  (stable at 12).
- `rule_toggle_experiment.sh`: with SID 1000001 off, the count stayed 7 to 7;
  after restore, the count went 7 to 8. The backup was restored.

**Phase 7 end-to-end (Kali VM, real bot, token only in `.env`):**
- `telegram-test` delivered the connectivity test message.
- `e2e_test.sh` delivered exactly 2 plain-text alerts: SID 1000001 severity 1 and
  SID 1000002 severity 2, each ending "Status: Detected by Suricata".
- The benign request sent no message. Old alerts did not flood on startup.

---

## 7. Limitations

- Suricata captures on loopback (`lo`) only. Other interfaces are not watched.
- There are only two custom rules.
- The system is IDS only. It does not block traffic (no IPS).
- The Telegram rate-limit summary and token revocation are tested only with mock
  unit tests, not live on the VM.
- The app uses the Flask development server and has no login. It is safe only
  because it stays on localhost.

---

## 8. Conclusion

CyberGuard meets its main goal. Suricata is the only detection engine, and Python
only reads, stores, and shows the alerts. The honest status and the rule toggle
experiment prove the design is correct: when the engine or a rule stops, the
alerts stop. The system is small, readable, and fully tested with 57 passing unit
tests and recorded end-to-end checks on the Kali VM.

---

## 9. Future work

- Add more rules, and try `suricata-update` for community rule sets.
- Capture on a real network interface, not only loopback.
- Add a login to the dashboard for safe remote use.
- Package the app with Docker for easy setup.
- Add a reports or export feature for alert history.

---

## References (project documents)

- [`../README.md`](../README.md) — project overview and setup.
- [`architecture.md`](architecture.md) — components, data flow, schema, status.
- [`demo-guide.md`](demo-guide.md) — the live demo script.
- [`professor-qa.md`](professor-qa.md) — questions and answers.
- [`../PROJECT_MEMORY.md`](../PROJECT_MEMORY.md) — detailed project memory.
