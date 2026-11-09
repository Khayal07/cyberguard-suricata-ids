"""Tests for app.services.eve_reader (incremental EVE JSON reading)."""

from pathlib import Path

from app.services import database, eve_reader
from tests.conftest import LINE1, LINE2, STATS_EVENT, write_eve


def test_missing_file_reports_eve_missing(config):
    config.EVE_PATH = str(Path(config.EVE_PATH).parent / "does_not_exist.json")
    result = eve_reader.read_new_alerts(config.DB_PATH, config.EVE_PATH)
    assert result["status"] == "eve_missing"
    assert result["alerts"] == []


def test_reads_real_alert_fixtures(config):
    write_eve(config, LINE1, LINE2)
    result = eve_reader.read_new_alerts(config.DB_PATH, config.EVE_PATH)

    assert result["status"] == "ok"
    assert len(result["alerts"]) == 2

    first = result["alerts"][0]
    assert first["signature_id"] == 1000001
    assert first["signature"] == "CyberGuard Test Alert"
    assert first["src_ip"] == "127.0.0.1"
    assert first["dest_port"] == 8000
    assert first["app_proto"] == "http"
    assert first["http_url"] == "/cyberguard-test"
    assert first["http_method"] == "GET"
    assert first["http_status"] == 200
    assert first["http_user_agent"] == "curl/8.21.0"
    assert first["in_iface"] == "lo"
    assert first["severity"] == 3
    assert first["category"] == ""  # empty category preserved
    assert first["raw_json"] == LINE1


def test_invalid_json_line_is_skipped_and_counted(config):
    write_eve(config, LINE1, "this is not json", LINE2)
    result = eve_reader.read_new_alerts(config.DB_PATH, config.EVE_PATH)
    assert len(result["alerts"]) == 2
    assert result["invalid_lines"] == 1
    assert result["total_invalid_lines"] == 1


def test_non_alert_events_are_ignored(config):
    write_eve(config, STATS_EVENT, LINE1)
    result = eve_reader.read_new_alerts(config.DB_PATH, config.EVE_PATH)
    assert len(result["alerts"]) == 1
    assert result["alerts"][0]["signature_id"] == 1000001
    # last_event_timestamp reflects the last complete event (the alert here).
    assert result["last_event_timestamp"] is not None


def test_partial_last_line_is_not_consumed(config):
    # First complete line + an incomplete second line (no trailing newline).
    partial = LINE2[:-5]
    Path(config.EVE_PATH).write_bytes((LINE1 + "\n" + partial).encode("utf-8"))

    r1 = eve_reader.read_new_alerts(config.DB_PATH, config.EVE_PATH)
    assert len(r1["alerts"]) == 1
    state = database.get_ingest_state(config.DB_PATH)
    assert state["byte_offset"] == len((LINE1 + "\n").encode("utf-8"))

    # Append the rest of line 2 plus a newline — now it is complete.
    with open(config.EVE_PATH, "ab") as handle:
        handle.write((LINE2[-5:] + "\n").encode("utf-8"))

    r2 = eve_reader.read_new_alerts(config.DB_PATH, config.EVE_PATH)
    assert len(r2["alerts"]) == 1
    assert r2["alerts"][0]["signature_id"] == 1000002


def test_truncation_restarts_from_zero(config):
    write_eve(config, LINE1, LINE2)
    r1 = eve_reader.read_new_alerts(config.DB_PATH, config.EVE_PATH)
    assert len(r1["alerts"]) == 2

    # Truncate the file to just the first line (size < stored offset).
    write_eve(config, LINE1)
    r2 = eve_reader.read_new_alerts(config.DB_PATH, config.EVE_PATH)
    assert r2["rotated"] is True
    assert len(r2["alerts"]) == 1


def test_inode_change_restarts_from_zero(config):
    write_eve(config, LINE1, LINE2)
    eve_reader.read_new_alerts(config.DB_PATH, config.EVE_PATH)

    # Simulate rotation: store a different (bogus) inode.
    database.update_ingest_state(config.DB_PATH, inode=999999999)
    result = eve_reader.read_new_alerts(config.DB_PATH, config.EVE_PATH)
    assert result["rotated"] is True
    assert len(result["alerts"]) == 2  # re-read from the start


def test_no_new_lines_when_suricata_stopped(config):
    write_eve(config, LINE1, LINE2)
    eve_reader.read_new_alerts(config.DB_PATH, config.EVE_PATH)
    # File unchanged (Suricata stopped) -> no new alerts, no crash.
    result = eve_reader.read_new_alerts(config.DB_PATH, config.EVE_PATH)
    assert result["status"] == "ok"
    assert result["alerts"] == []
