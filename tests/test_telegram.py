"""Tests for the optional Telegram notifier (Phase 7).

No network is used: the HTTP sender is always injected/mocked. These tests prove
the feature is disabled unless configured, only new inserts notify, duplicates
and historical alerts never notify, the severity filter and rate limit behave,
errors never break ingestion, the token never leaks into logs, and /api/status
never exposes the token or chat id.
"""

import json
import logging

import pytest

from app import create_app
from app.services import alert_service, database, telegram_notifier
from tests.conftest import LINE1, LINE2, make_config, write_eve

# Obvious fake credentials — NOT real. Never use a real token in tests.
TOKEN = "123456789:FAKE-TEST-TOKEN-do-not-use"
CHAT = "999000111"


class CollectingSender:
    """Mock sender that records (token, chat_id, text) calls instead of HTTP."""

    def __init__(self):
        self.calls = []

    def __call__(self, token, chat_id, text):
        self.calls.append((token, chat_id, text))


class RaisingSender:
    """Mock sender that fails with an error string LEAKING the token (as a real
    urllib HTTPError URL would), to prove the notifier scrubs it."""

    def __init__(self, token):
        self.token = token
        self.calls = 0

    def __call__(self, token, chat_id, text):
        self.calls += 1
        raise RuntimeError(
            "HTTP Error 401 at https://api.telegram.org/bot%s/sendMessage" % token
        )


def tg_config(tmp_path, **overrides):
    opts = dict(
        TELEGRAM_TOKEN=TOKEN,
        TELEGRAM_CHAT_ID=CHAT,
        TELEGRAM_MIN_SEVERITY=3,
        TELEGRAM_RATE_PER_MIN=5,
    )
    opts.update(overrides)
    return make_config(tmp_path, **opts)


def make_record(**over):
    rec = dict(
        flow_id=1,
        timestamp_raw="2026-11-10T09:00:00.000000-0500",
        timestamp_utc="2026-11-10T14:00:00.000000+00:00",
        signature="CyberGuard Test Alert",
        signature_id=1000001,
        severity=1,
        src_ip="127.0.0.1",
        src_port=5555,
        dest_ip="127.0.0.1",
        dest_port=8000,
        http_url="/cyberguard-test",
    )
    rec.update(over)
    return rec


@pytest.fixture(autouse=True)
def _reset_active():
    """Keep the module-level active notifier from leaking across tests."""
    telegram_notifier.set_active(None)
    yield
    telegram_notifier.set_active(None)


# --- Enablement -----------------------------------------------------------

def test_disabled_when_unset(tmp_path):
    sender = CollectingSender()
    cfg = make_config(tmp_path)  # no Telegram vars at all
    notifier = telegram_notifier.TelegramNotifier(cfg, sender=sender, async_send=False)
    assert notifier.enabled is False
    notifier.notify_new_alerts([make_record()])
    assert sender.calls == []  # nothing sent when disabled


def test_disabled_when_only_token_set(tmp_path):
    cfg = make_config(tmp_path, TELEGRAM_TOKEN=TOKEN)  # chat id missing
    notifier = telegram_notifier.TelegramNotifier(cfg, async_send=False)
    assert notifier.enabled is False


# --- Message format / sanitisation ----------------------------------------

def test_message_format_exact():
    msg = telegram_notifier.format_alert(make_record())
    assert msg == (
        "CyberGuard Security Alert\n"
        "Rule: CyberGuard Test Alert (sid 1000001)\n"
        "Severity: 1\n"
        "Source: 127.0.0.1:5555 -> 127.0.0.1:8000\n"
        "URL: /cyberguard-test\n"
        "Time (UTC): 2026-11-10T14:00:00.000000+00:00\n"
        "Status: Detected by Suricata"
    )


def test_truncation_and_control_char_stripping():
    # An attacker-influenced URL with newlines must NOT forge extra lines, and a
    # very long signature must be truncated.
    rec = make_record(
        signature="A" * 250,
        http_url="/x\r\n\tInjected: evil\nSeverity: 99",
    )
    msg = telegram_notifier.format_alert(rec)
    lines = msg.split("\n")
    assert len(lines) == 7  # exactly the 7 template lines, no injected lines
    assert lines[1] == "Rule: " + "A" * 100 + "… (sid 1000001)"
    url_line = lines[4]
    assert url_line.startswith("URL: ")
    assert "\t" not in url_line and "\r" not in url_line
    assert "Injected: evil" in url_line  # folded onto one line, not a new line


def test_none_fields_render_dash():
    msg = telegram_notifier.format_alert(make_record(http_url=None, src_port=None))
    assert "URL: -" in msg
    assert "Source: 127.0.0.1:- -> 127.0.0.1:8000" in msg


# --- Only new inserts / dedup ---------------------------------------------

def test_new_alert_notifies_once_and_dedupes(tmp_path):
    sender = CollectingSender()
    notifier = telegram_notifier.TelegramNotifier(
        tg_config(tmp_path), sender=sender, async_send=False
    )
    rec = make_record()
    notifier.notify_new_alerts([rec])
    notifier.notify_new_alerts([rec])  # same (flow_id, ts_raw, sid) -> no resend
    assert len(sender.calls) == 1
    assert sender.calls[0][0] == TOKEN
    assert sender.calls[0][1] == CHAT


def test_marked_baseline_alerts_never_notify(tmp_path):
    sender = CollectingSender()
    notifier = telegram_notifier.TelegramNotifier(
        tg_config(tmp_path), sender=sender, async_send=False
    )
    rec = make_record()
    notifier.mark_seen([rec])  # baseline record: remember but do not send
    notifier.notify_new_alerts([rec])  # later re-seen -> still suppressed
    assert sender.calls == []


# --- Severity filter ------------------------------------------------------

def test_min_severity_filter(tmp_path):
    sender = CollectingSender()
    notifier = telegram_notifier.TelegramNotifier(
        tg_config(tmp_path, TELEGRAM_MIN_SEVERITY=2), sender=sender, async_send=False
    )
    notifier.notify_new_alerts([make_record(flow_id=10, severity=3)])  # 3 > 2: skip
    assert sender.calls == []
    notifier.notify_new_alerts([make_record(flow_id=11, severity=2)])  # 2 <= 2: send
    notifier.notify_new_alerts([make_record(flow_id=12, severity=1)])  # 1 <= 2: send
    assert len(sender.calls) == 2


# --- Rate limit + single summary ------------------------------------------

def test_rate_limit_collapses_to_single_summary(tmp_path):
    sender = CollectingSender()
    notifier = telegram_notifier.TelegramNotifier(
        tg_config(tmp_path, TELEGRAM_RATE_PER_MIN=3), sender=sender, async_send=False
    )
    records = [make_record(flow_id=100 + i, src_port=6000 + i) for i in range(5)]
    notifier.notify_new_alerts(records)
    texts = [c[2] for c in sender.calls]
    # 3 individual alerts + exactly ONE summary for the 2 excess.
    assert len(texts) == 4
    assert all(t.startswith("CyberGuard Security Alert") for t in texts[:3])
    assert texts[3].startswith("CyberGuard: 2 more alert(s) suppressed")
    # Suppressed alerts are counted, never silently dropped or unbounded.
    assert "rate limit 3/min" in texts[3]


# --- Failure isolation / token never logged -------------------------------

def test_send_error_does_not_raise_and_token_not_logged(tmp_path, caplog):
    sender = RaisingSender(TOKEN)
    notifier = telegram_notifier.TelegramNotifier(
        tg_config(tmp_path), sender=sender, async_send=False
    )
    with caplog.at_level(logging.ERROR):
        notifier.notify_new_alerts([make_record()])  # must NOT raise
    assert sender.calls == 1
    assert notifier.last_status == "error"
    logged = "\n".join(r.getMessage() for r in caplog.records)
    assert TOKEN not in logged  # token scrubbed from the log
    assert "<redacted>" in logged


def test_scrub_removes_token():
    leaky = "boom at https://api.telegram.org/bot%s/sendMessage timeout" % TOKEN
    scrubbed = telegram_notifier._scrub(leaky, TOKEN)
    assert TOKEN not in scrubbed
    assert "<redacted>" in scrubbed


# --- Worker baseline (no startup flood) + ingest-once (no notify) ----------

def test_worker_baseline_then_new_alert(tmp_path):
    cfg = tg_config(tmp_path)
    database.init_db(cfg.DB_PATH)
    write_eve(cfg, LINE1, LINE2)  # two alerts already present at startup
    sender = CollectingSender()
    notifier = telegram_notifier.TelegramNotifier(cfg, sender=sender, async_send=False)
    worker = alert_service.IngestionWorker(cfg, notifier=notifier)

    worker.poll_once()  # baseline cycle: ingests the 2 historical, sends nothing
    assert sender.calls == []

    # A genuinely new alert (distinct flow_id) appears; next cycle notifies once.
    new_line = LINE1.replace('"flow_id":420878223340296', '"flow_id":111111111111111')
    write_eve(cfg, LINE1, LINE2, new_line)
    worker.poll_once()
    assert len(sender.calls) == 1
    assert sender.calls[0][2].startswith("CyberGuard Security Alert")


def test_ingest_once_never_notifies(tmp_path):
    cfg = tg_config(tmp_path)
    database.init_db(cfg.DB_PATH)
    write_eve(cfg, LINE1, LINE2)
    sender = CollectingSender()
    notifier = telegram_notifier.TelegramNotifier(cfg, sender=sender, async_send=False)
    telegram_notifier.set_active(notifier)
    # The one-shot CLI calls ingest WITHOUT an on_inserted callback.
    alert_service.ingest(cfg)
    assert sender.calls == []


# --- /api/status never exposes secrets ------------------------------------

def test_status_endpoint_reports_telegram_without_secrets(tmp_path):
    cfg = tg_config(tmp_path)
    write_eve(cfg, LINE1)
    app = create_app(cfg)
    resp = app.test_client().get("/api/status")
    data = resp.get_json()
    assert data["telegram_enabled"] is True
    assert data["last_notification_status"] == "none"
    assert data["last_notification_at"] is None
    body = resp.get_data(as_text=True)
    assert TOKEN not in body
    assert CHAT not in body
    # No field name hints at a stored secret either.
    assert "token" not in body.lower()


def test_status_reflects_active_notifier_state(tmp_path):
    cfg = tg_config(tmp_path)
    database.init_db(cfg.DB_PATH)
    sender = CollectingSender()
    notifier = telegram_notifier.TelegramNotifier(cfg, sender=sender, async_send=False)
    notifier.send_test()  # drives last_status -> "ok"
    telegram_notifier.set_active(notifier)
    status = alert_service.get_status(cfg)
    assert status["telegram_enabled"] is True
    assert status["last_notification_status"] == "ok"
    assert status["last_notification_at"] is not None
    assert TOKEN not in json.dumps(status)
    # The connectivity test message is clearly labelled as not a detection.
    assert sender.calls[0][2] == "CyberGuard connectivity test (not a detection alert)"
