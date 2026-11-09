# Phase 7 — Optional Telegram Alert Notifications

> Beginner-friendly guide. Telegram is **optional**. If you do not configure it,
> CyberGuard works exactly as before. When configured, CyberGuard sends you a
> short message whenever **Suricata** detects a new genuine alert. Python does
> **no** detection here — it only forwards what Suricata already found.

---

## 1. What this adds

| Piece | What it does |
|-------|--------------|
| `app/services/telegram_notifier.py` | Standard-library sender (no new dependency) that forwards new alerts |
| 4 env vars | token, chat id, severity threshold, rate limit |
| `python -m app.main telegram-test` | Sends ONE clearly-labelled test message |
| `/api/status` fields | `telegram_enabled`, `last_notification_status`, `last_notification_at` (never the token) |

**Golden rule:** a message is sent **only** for alerts that the background worker
**newly inserts** into SQLite. Historical alerts (already in the database or
already in `eve.json` when you start the app) never trigger a message, so there
is no flood on startup.

---

## 2. Step 1 — Create a bot with BotFather

1. In Telegram, search for **@BotFather** and open the chat.
2. Send `/newbot`.
3. Choose a name (any) and a username ending in `bot` (e.g. `cyberguard_lab_bot`).
4. BotFather replies with a **token** that looks like
   `123456789:AAExampleExampleExampleExampleExample`.
   - This token is a **password**. Keep it secret. Never put it in the repo, in a
     commit, in a screenshot, or in chat. **(Azərbaycanca:** bu token paroldur —
     heç vaxt repoya və ya şəklə qoyma.)

---

## 3. Step 2 — Get your chat id

The bot can only message a chat it knows about. The easiest way to find your chat
id:

1. Open a chat with your new bot and press **Start** (or send any message like
   `hi`).
2. In a browser, open (replace `<TOKEN>` with your token):

   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```

3. In the JSON you get back, find `"chat":{"id":<NUMBER>, ...}`. That `<NUMBER>`
   is your **chat id** (it may be negative for a group).

> Tip: if `getUpdates` is empty, send your bot another message and refresh.

---

## 4. Step 3 — Put the values in your local `.env` (never committed)

CyberGuard reads these from the environment. On the **Kali VM**, create/edit a
local `.env` in the project root (it is git-ignored — confirm with
`git check-ignore .env`):

```bash
# .env  (LOCAL ONLY — never commit this file)
CYBERGUARD_TELEGRAM_TOKEN=123456789:AAExample...your-real-token...
CYBERGUARD_TELEGRAM_CHAT_ID=123456789
# Optional tuning (safe to leave out — defaults shown):
CYBERGUARD_TELEGRAM_MIN_SEVERITY=3   # notify only when severity <= 3
CYBERGUARD_TELEGRAM_RATE_PER_MIN=5   # at most 5 messages/min, rest summarised
```

- Telegram is **enabled only when BOTH** the token and chat id are set.
- `.env.example` in the repo keeps these **blank** on purpose — it is a template.

---

## 5. Step 4 — Test connectivity (no detection involved)

```bash
python -m app.main telegram-test
```

- If configured correctly, you receive a message:
  **"CyberGuard connectivity test (not a detection alert)"**, and the terminal
  prints `OK`.
- If not configured, it prints a hint and sends nothing.
- On any error it prints `FAILED` **without** printing the token.

---

## 6. Step 5 — Run the app and see real alerts

1. Make sure Suricata is running and the backend is up (see
   `docs/phase6-rule-lab.md`, `bash scripts/start_lab.sh`).
2. Start the backend: `python -m app.main`.
   - The **first** poll cycle reads whatever is already in `eve.json` as a silent
     baseline (no messages) so you are not flooded.
3. Generate a new alert, e.g. `curl http://127.0.0.1:8000/cyberguard-test`.
4. Suricata detects it → the worker stores it → you get a Telegram message like:

   ```
   CyberGuard Security Alert
   Rule: CyberGuard Test Alert (sid 1000001)
   Severity: 1
   Source: 127.0.0.1:46988 -> 127.0.0.1:8000
   URL: /cyberguard-test
   Time (UTC): 2026-11-10T14:46:33.623977+00:00
   Status: Detected by Suricata
   ```

The dashboard status card also shows **"Telegram: on"** and the last send result.

---

## 7. How to revoke a leaked token (do this if a token is ever exposed)

If a token is ever committed, pasted, or shown anywhere:

1. Open **@BotFather** → `/revoke` → pick the bot. The old token stops working
   immediately.
2. BotFather gives you a **new** token. Put the new one in your local `.env`.
3. If the token was committed to git, treat the commit as compromised: rotate the
   token (step 1) — rotation is what actually protects you, since the old value
   may already be cached by others.

---

## 8. Safety design (why this is hard to abuse)

- **Plain text only** (no `parse_mode`): attacker-controlled fields (URL, user
  agent, signature) cannot inject Telegram markup. Each field is stripped of
  control characters and truncated (~100 chars), so a crafted URL cannot forge
  extra lines in the message.
- **No shell, no subprocess, no new dependency:** sending uses only
  `urllib.request` over HTTPS with a short (~5s) timeout.
- **Failure isolation:** any network/HTTP/timeout error is caught and logged
  **without** the token (the token is scrubbed from error text and URLs).
  Ingestion never crashes or slows down because of Telegram; sending runs on a
  small background thread.
- **Deduplication:** the same `(flow_id, timestamp_raw, signature_id)` is never
  sent twice (the DB UNIQUE key plus an in-memory guard).
- **Rate limiting:** at most `CYBERGUARD_TELEGRAM_RATE_PER_MIN` messages per
  rolling minute; extra alerts are collapsed into **one** summary message
  ("N more alerts suppressed in the last minute") — never dropped silently, never
  unbounded.
- **`/api/status` never exposes the token or chat id.**

---

## 9. Limitations

- Telegram requires outbound internet from the Kali VM to `api.telegram.org`. In a
  fully offline lab, `telegram-test` will fail (which is handled gracefully).
- The summary message is intentionally coarse: it tells you *how many* alerts were
  suppressed, not their details — open the dashboard for the full list.
- The in-memory dedup guard resets when the backend restarts; the DB UNIQUE key
  still prevents duplicate storage, and the baseline pass prevents a restart from
  re-sending old alerts.
- Telegram is a **notification** channel only. The dashboard and API remain the
  source of truth; Suricata remains the only detection engine.
