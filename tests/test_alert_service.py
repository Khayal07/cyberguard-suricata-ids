"""Tests for app.services.alert_service (normalization, ingest, status)."""

from app.services import alert_service, database
from tests.conftest import LINE1, LINE2, write_eve


def test_normalize_timestamp_offset_without_colon():
    raw, utc = alert_service.normalize_timestamp("2026-11-09T09:46:33.623977-0500")
    assert raw == "2026-11-09T09:46:33.623977-0500"
    assert utc == "2026-11-09T14:46:33.623977+00:00"


def test_normalize_timestamp_invalid_returns_none():
    raw, utc = alert_service.normalize_timestamp("not-a-timestamp")
    assert raw == "not-a-timestamp"
    assert utc is None


def test_ingest_stores_alerts_and_dedupes_on_reingest(config):
    write_eve(config, LINE1, LINE2)

    first = alert_service.ingest(config)
    assert first["status"] == "ok"
    assert first["inserted"] == 2
    assert first["duplicates"] == 0

    # Re-ingesting the unchanged file reads nothing new (offset at end).
    second = alert_service.ingest(config)
    assert second["read"] == 0
    assert second["inserted"] == 0
    assert database.count_alerts(config.DB_PATH) == 2


def test_dedup_holds_even_if_offset_reset(config):
    write_eve(config, LINE1, LINE2)
    alert_service.ingest(config)

    # Force a re-read of the whole file; UNIQUE constraint must prevent dupes.
    database.update_ingest_state(config.DB_PATH, byte_offset=0, inode=0)
    again = alert_service.ingest(config)
    assert again["read"] == 2
    assert again["inserted"] == 0
    assert again["duplicates"] == 2
    assert database.count_alerts(config.DB_PATH) == 2


def test_ingest_missing_file(config):
    config.EVE_PATH = str(config.EVE_PATH) + ".missing"
    result = alert_service.ingest(config)
    assert result["status"] == "eve_missing"
    assert result["inserted"] == 0


def test_empty_category_kept_in_db_shown_as_uncategorized(config):
    write_eve(config, LINE1)
    alert_service.ingest(config)

    raw_rows = database.query_alerts(config.DB_PATH)
    assert raw_rows[0]["category"] == ""  # raw empty value preserved

    listed = alert_service.list_alerts(config)
    assert listed["alerts"][0]["category"] == "uncategorized"  # display only


def test_list_alerts_newest_first(config):
    write_eve(config, LINE1, LINE2)
    alert_service.ingest(config)
    listed = alert_service.list_alerts(config)
    assert listed["count"] == 2
    assert listed["alerts"][0]["signature_id"] == 1000002  # later timestamp first


def test_check_suricata_process_unverified_without_proc(config):
    # PROC_BASE points at a non-existent dir -> cannot verify.
    assert alert_service.check_suricata_process(config.SURICATA_PID_PATH, config.PROC_BASE) == "unverified"


def test_check_suricata_process_not_running_when_pid_missing(tmp_path):
    proc = tmp_path / "proc"
    proc.mkdir()
    pid_path = tmp_path / "suricata.pid"  # does not exist
    assert alert_service.check_suricata_process(str(pid_path), str(proc)) == "verified_not_running"


def test_check_suricata_process_running(tmp_path):
    proc = tmp_path / "proc"
    (proc / "4242").mkdir(parents=True)
    (proc / "4242" / "comm").write_text("Suricata-Main\n", encoding="utf-8")
    pid_path = tmp_path / "suricata.pid"
    pid_path.write_text("4242\n", encoding="utf-8")
    assert alert_service.check_suricata_process(str(pid_path), str(proc)) == "verified_running"


def test_check_suricata_process_wrong_comm(tmp_path):
    proc = tmp_path / "proc"
    (proc / "4242").mkdir(parents=True)
    (proc / "4242" / "comm").write_text("python3\n", encoding="utf-8")
    pid_path = tmp_path / "suricata.pid"
    pid_path.write_text("4242\n", encoding="utf-8")
    assert alert_service.check_suricata_process(str(pid_path), str(proc)) == "verified_not_running"


def test_get_status_fields(config):
    write_eve(config, LINE1, LINE2)
    alert_service.ingest(config)
    status = alert_service.get_status(config)
    assert status["backend_running"] is True
    assert status["eve_file_exists"] is True
    assert status["suricata_process"] == "unverified"  # no /proc in tests
    assert status["total_alerts"] == 2
    assert status["last_event_timestamp"] is not None
    assert status["last_alert_ingested_at"] is not None
