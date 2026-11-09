# CLAUDE.md — Permanent Instructions for CyberGuard

> **This file is mandatory reading for every Claude Code session before doing any work.**

---

## 0. Project Identity

**CyberGuard** — Suricata-Powered Network Intrusion Detection and Monitoring System.
A university Information Security project. Suricata IDS is the central, indispensable
detection engine. Python only reads, processes, stores, serves, and displays the
events Suricata produces.

---

## 1. Session Startup Checklist (DO THIS FIRST, EVERY TIME)

At the beginning of every new Claude Code session, before touching anything:

1. **Read `CLAUDE.md`** (this file).
2. **Read `PROJECT_MEMORY.md`** — the persistent project memory.
3. **Run `git status`** to see the working tree state.
4. **Run `git log --oneline -10`** to see recent commits.
5. **Summarize the current project state** and the current phase to the user
   before continuing any work.

Never assume previous session context is available. The memory files are the
single source of truth.

---

## 2. Core Architecture Rules (NEVER VIOLATE)

- **Suricata is the ONLY detection engine.** It inspects traffic (live or authorized
  PCAP), evaluates packets against rules, and writes genuine events to EVE JSON.
- **Python must NEVER become an alternative IDS.** Python only: reads EVE JSON,
  processes genuine events, stores them in SQLite, serves a Flask API, renders the
  dashboard, and (optional final phase) sends Telegram notifications.
- **If Suricata is stopped/removed, new genuine detections must stop.** This is the
  correctness test for the architecture.
- **Never fabricate detection results.** No synthetic/mock "detections" standing in
  for real Suricata output. Test data must be clearly labeled as fixtures.

---

## 3. Technology Stack (do not expand without explicit approval)

Suricata 8.x (or compatible stable) · Kali Linux (Debian-based) · Python 3 · Flask · SQLite ·
HTML · CSS · Vanilla JavaScript · EVE JSON · Telegram Bot API (optional final phase).

**Forbidden unless explicitly approved:** React, Next.js, Docker, Redis,
Elasticsearch, cloud infrastructure, or any other heavy dependency. Keep it
beginner-friendly and maintainable.

---

## 4. Development Discipline

- Preserve previously implemented architecture. Do not rewrite working code
  without reason.
- Never repeat completed phases unnecessarily — check `PROJECT_MEMORY.md` first.
- Write clean, readable code with meaningful names and explicit error handling.
- Add tests where appropriate. Do not fabricate test results or claim features
  work without verifying them.
- Explain cybersecurity concepts in simple language — the project owner knows
  Python/AI engineering but is a cybersecurity beginner.
- Update `PROJECT_MEMORY.md` after every meaningful change and before completing
  a phase.

---

## 5. Strict Phase Workflow

- The project is built phase by phase. Execute ONLY the phase the user explicitly
  provides.
- Never start a future phase automatically. The master plan is NOT permission to
  implement everything.
- Complete and test the current phase → thorough code review → update
  `PROJECT_MEMORY.md` → commit and push → detailed completion report → **STOP** and
  wait for the next explicit phase prompt.

---

## 6. GitHub Workflow (at the end of each completed phase)

1. Review all modified and new files.
2. Confirm no secrets or sensitive files are staged.
3. Run all relevant tests.
4. Inspect `git diff`.
5. Verify the phase is genuinely complete.
6. Update `PROJECT_MEMORY.md`.
7. `git add` the intended changes.
8. Create a meaningful commit (one per completed phase; no empty/broken commits).
9. Push to the current branch.
10. Verify the push succeeded.
11. Report the commit hash.

If a phase fails verification: fix it, rerun tests, and do NOT commit/push until it
passes. If blocked, explain and wait for the user.

**Do not** force-push. **Do not** amend existing commits unless explicitly requested.
**Do not** push to unrelated branches.

---

## 7. Git Authorship & AI Attribution (STRICT)

- All commits use the repository's existing Git identity: **Khayal07
  <khayal.izada39@gmail.com>**.
- **Never** add Claude/Anthropic/AI as author or co-author.
- **Never** add `Co-authored-by` trailers mentioning Claude, Anthropic, or AI tools.
- **Never** add AI-generated attribution to commit messages.
- **Never** change the Git username/email or create a separate AI identity.
- **Never** modify global Git configuration.
- Before committing, verify the configured author. After committing, verify the
  actual author and message.

---

## 8. Security Rules

- All security experiments run only in an authorized local laboratory.
- Use harmless HTTP markers and controlled lab traffic.
- **No** external scanning, unauthorized pentesting, credential attacks,
  destructive attacks, or public exposure of the Flask app.
- Keep credentials in environment variables. Never commit `.env` or real tokens —
  use `.env.example` with placeholders only.
- Keep Flask bound to `localhost` for development.

---

## 9. Where Things Live

- `PROJECT_MEMORY.md` — detailed persistent memory (architecture, config paths,
  rules, schema, endpoints, tests, errors, current phase, next steps).
- `CLAUDE.md` — this file; permanent instructions.
- `.gitignore` — excludes secrets, venvs, logs, databases, PCAPs, caches.

Keep both memory files accurate. They are how future sessions continue correctly.
