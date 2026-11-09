"""Optional Telegram alert notifications for CyberGuard.

This module sends a short message to a Telegram chat when Suricata produces a
NEW genuine alert that the ingestion worker just stored. It is strictly
OPTIONAL: if the token and chat id are not both configured, nothing is sent and
the rest of the application behaves exactly as before.

Design / safety guarantees:
- **No detection here.** Every alert originates from Suricata; this module only
  forwards what was already stored in SQLite.
- **Standard library only** (``urllib.request``) over HTTPS to api.telegram.org;
  no new dependency.
- **Plain text** messages (no ``parse_mode``) so attacker-controlled fields
  (URL, user agent, signature) cannot inject Telegram markup. Each field is
  truncated and stripped of control characters.
- **Only new inserts notify.** The caller passes the records that were actually
  inserted this run; duplicates and historical alerts never reach a send.
- **Deduplication** on ``(flow_id, timestamp_raw, signature_id)`` via an
  in-memory guard (the DB UNIQUE key is the primary guard).
- **Rate limiting:** at most ``rate_per_min`` messages per rolling minute; excess
  alerts are collapsed into ONE summary message, never dropped, never unbounded.
- **Failure isolation:** any network/HTTP error is caught and logged WITHOUT the
  token; ingestion never crashes or blocks because of Telegram.
"""

import logging
import queue
import re
import threading
import time
import urllib.parse
import urllib.request
from collections import deque
from datetime import datetime, timezone

logger = logging.getLogger("cyberguard.telegram")

# Telegram Bot API base. The token is injected per-request; it is NEVER logged.
_API_BASE = "https://api.telegram.org"
_SEND_TIMEOUT = 5  # seconds — short so it cannot block for long
_FIELD_MAXLEN = 100  # per-field truncation
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")  # strip control chars (incl. newlines)
_DEDUP_MAX = 10000  # bound the in-memory dedup guard (DB is the real guard)
_SENTINEL = object()  # queue stop marker


class TelegramSendError(Exception):
    """Raised by the HTTP sender on failure, with the token already scrubbed."""


# --- Module-level active notifier (for /api/status) -----------------------
# The ingestion worker registers its notifier here so the status endpoint can
# report last-notification state. Only ever holds a reference the app created.
_active_notifier = None


def set_active(notifier):
    """Register (or clear with None) the notifier used by the running worker."""
    global _active_notifier
    _active_notifier = notifier


def _cfg(config, name, default):
    """Read a config attribute with a default (works for Config and test stubs)."""
    return getattr(config, name, default)


def is_enabled(config):
    """True only when BOTH a token and a chat id are configured."""
    return bool(_cfg(config, "TELEGRAM_TOKEN", "") and _cfg(config, "TELEGRAM_CHAT_ID", ""))


def status_fields(config):
    """Telegram fields for /api/status. NEVER includes the token or chat id."""
    notifier = _active_notifier
    if notifier is not None:
        return {
            "telegram_enabled": notifier.enabled,
            "last_notification_status": notifier.last_status,
            "last_notification_at": notifier.last_at,
        }
    return {
        "telegram_enabled": is_enabled(config),
        "last_notification_status": "none",
        "last_notification_at": None,
    }


# --- Sanitisation helpers -------------------------------------------------

def _scrub(text, token):
    """Remove the bot token from arbitrary text (e.g. exception/URL strings)."""
    if not text:
        return text
    text = str(text)
    if token:
        text = text.replace(token, "<redacted>")
    # Also redact any ``/bot<token>/`` pattern that might survive.
    return re.sub(r"/bot[^/\s]+/", "/bot<redacted>/", text)


def _clean(value, maxlen=_FIELD_MAXLEN):
    """Return a single-line, control-char-free, truncated string for a field."""
    if value is None:
        return "-"
    text = _CONTROL_CHARS.sub(" ", str(value)).strip()
    if not text:
        return "-"
    if len(text) > maxlen:
        text = text[:maxlen] + "…"
    return text


def format_alert(record):
    """Build the plain-text alert message from a stored alert record (dict)."""
    sig = _clean(record.get("signature"))
    sid = _clean(record.get("signature_id"))
    severity = _clean(record.get("severity"))
    src = "%s:%s" % (_clean(record.get("src_ip")), _clean(record.get("src_port")))
    dst = "%s:%s" % (_clean(record.get("dest_ip")), _clean(record.get("dest_port")))
    url = _clean(record.get("http_url"))
    ts = _clean(record.get("timestamp_utc"))
    return (
        "CyberGuard Security Alert\n"
        "Rule: %s (sid %s)\n"
        "Severity: %s\n"
        "Source: %s -> %s\n"
        "URL: %s\n"
        "Time (UTC): %s\n"
        "Status: Detected by Suricata"
    ) % (sig, sid, severity, src, dst, url, ts)


def _dedup_key(record):
    return (
        record.get("flow_id"),
        record.get("timestamp_raw"),
        record.get("signature_id"),
    )


# --- HTTP sender (standard library only) ----------------------------------

def send_message(token, chat_id, text, timeout=_SEND_TIMEOUT):
    """POST a plain-text message to Telegram. Raises TelegramSendError on
    failure, with the token scrubbed from the error. No ``parse_mode`` is used."""
    url = "%s/bot%s/sendMessage" % (_API_BASE, token)
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = getattr(response, "status", response.getcode())
            if status != 200:
                raise TelegramSendError("Telegram HTTP status %s" % status)
    except TelegramSendError:
        raise
    except Exception as exc:  # network, HTTPError (URL carries token!), timeout
        # str(exc)/the URL may contain the token — scrub before it escapes.
        raise TelegramSendError(_scrub("%s: %s" % (type(exc).__name__, exc), token))


# --- Notifier -------------------------------------------------------------

class TelegramNotifier:
    """Decides what to send and delivers it without blocking ingestion.

    Decisions (severity filter, dedup, rate limit) run synchronously in the
    caller's thread (fast, no network). Delivery runs on a small background
    thread so a slow network never stalls the ingestion loop. Pass
    ``async_send=False`` for deterministic, synchronous behaviour in tests.
    """

    def __init__(self, config, sender=None, async_send=True):
        self.token = _cfg(config, "TELEGRAM_TOKEN", "")
        self.chat_id = _cfg(config, "TELEGRAM_CHAT_ID", "")
        self.min_severity = int(_cfg(config, "TELEGRAM_MIN_SEVERITY", 3))
        self.rate_per_min = max(1, int(_cfg(config, "TELEGRAM_RATE_PER_MIN", 5)))
        self.enabled = bool(self.token and self.chat_id)
        self._sender = sender or send_message

        # Dedup guard (bounded): a set for lookups + a deque for eviction order.
        self._seen = set()
        self._seen_order = deque()
        # Rate-limit state: timestamps of individual sends in the last 60s, a
        # running suppressed counter, and the time of the last summary message.
        self._send_times = deque()
        self._suppressed = 0
        self._last_summary_at = 0.0

        self._lock = threading.Lock()
        self.last_status = "none"  # "none" | "ok" | "error"
        self.last_at = None        # ISO UTC string of the last send attempt

        self._async = async_send and self.enabled
        self._queue = None
        self._deliver_thread = None
        if self._async:
            self._queue = queue.Queue()
            self._deliver_thread = threading.Thread(
                target=self._deliver_loop, name="cyberguard-telegram", daemon=True
            )
            self._deliver_thread.start()

    # --- public API -------------------------------------------------------

    def mark_seen(self, records):
        """Record dedup keys WITHOUT sending (used for the worker's baseline
        first pass so pre-existing/backlog alerts never trigger a flood)."""
        if not self.enabled or not records:
            return
        with self._lock:
            for record in records:
                self._remember(_dedup_key(record))

    def notify_new_alerts(self, records):
        """Notify for newly-inserted alert records. Never raises."""
        if not self.enabled or not records:
            return
        to_send = []
        summary_count = 0
        with self._lock:
            for record in records:
                key = _dedup_key(record)
                if key in self._seen:
                    continue  # in-memory dedup guard
                self._remember(key)
                severity = record.get("severity")
                if severity is None or int(severity) > self.min_severity:
                    continue  # below the configured severity threshold
                if self._allow_individual_locked():
                    to_send.append(format_alert(record))
                else:
                    self._suppressed += 1
            summary_count = self._take_summary_locked()
        # Deliver outside the lock so network latency never holds it.
        for message in to_send:
            self._deliver(message)
        if summary_count:
            self._deliver(
                "CyberGuard: %d more alert(s) suppressed in the last minute "
                "(rate limit %d/min)." % (summary_count, self.rate_per_min)
            )

    def send_test(self):
        """Send a clearly-labelled connectivity test synchronously. Returns a
        bool; never prints or raises."""
        if not self.enabled:
            return False
        return self._send(
            "CyberGuard connectivity test (not a detection alert)"
        )

    def stop(self):
        """Stop the background delivery thread (if any)."""
        if self._async and self._queue is not None:
            self._queue.put(_SENTINEL)
            if self._deliver_thread:
                self._deliver_thread.join(timeout=_SEND_TIMEOUT + 1)

    # --- internals --------------------------------------------------------

    def _remember(self, key):
        """Add a dedup key, evicting the oldest if the guard is full."""
        if key in self._seen:
            return
        self._seen.add(key)
        self._seen_order.append(key)
        if len(self._seen_order) > _DEDUP_MAX:
            old = self._seen_order.popleft()
            self._seen.discard(old)

    def _allow_individual_locked(self):
        """True if another individual message fits in the rolling-minute budget."""
        now = time.monotonic()
        while self._send_times and now - self._send_times[0] >= 60:
            self._send_times.popleft()
        if len(self._send_times) < self.rate_per_min:
            self._send_times.append(now)
            return True
        return False

    def _take_summary_locked(self):
        """Return a suppressed count to summarise now (at most one summary per
        rolling minute), or 0. Suppressed alerts are never dropped — they are
        reported in the next summary once a minute has elapsed."""
        if self._suppressed <= 0:
            return 0
        now = time.monotonic()
        if self._last_summary_at and now - self._last_summary_at < 60:
            return 0
        count = self._suppressed
        self._suppressed = 0
        self._last_summary_at = now
        return count

    def _deliver(self, text):
        """Hand a ready message to the delivery path (async queue or direct)."""
        if self._async and self._queue is not None:
            self._queue.put(text)
        else:
            self._send(text)

    def _deliver_loop(self):
        while True:
            item = self._queue.get()
            if item is _SENTINEL:
                break
            self._send(item)

    def _send(self, text):
        """Actually send one message; isolate and scrub all failures."""
        try:
            self._sender(self.token, self.chat_id, text)
            self._set_status("ok")
            return True
        except Exception as exc:  # never let Telegram break ingestion
            logger.error("Telegram send failed: %s", _scrub(str(exc), self.token))
            self._set_status("error")
            return False

    def _set_status(self, status):
        with self._lock:
            self.last_status = status
            self.last_at = datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%S.%f"
            ) + "+00:00"
