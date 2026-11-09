"""Tests for app.services.database (persistence, dedup, queries, stats)."""

from app.services import alert_service, database, eve_reader


def _records_from_fixture(config):
    from tests.conftest import LINE1, LINE2, write_eve

    write_eve(config, LINE1, LINE2)
    result = eve_reader.read_new_alerts(config.DB_PATH, config.EVE_PATH)
    return [alert_service.to_db_record(a) for a in result["alerts"]]


def test_insert_and_query_persists_fields(config):
    records = _records_from_fixture(config)
    conn = database.get_connection(config.DB_PATH)
    try:
        for rec in records:
            assert database.insert_alert(conn, rec) == 1
        conn.commit()
    finally:
        conn.close()

    rows = database.query_alerts(config.DB_PATH)
    assert len(rows) == 2
    # Newest first: line 2 (…637) precedes line 1 (…623).
    assert rows[0]["signature_id"] == 1000002
    assert rows[0]["timestamp_utc"].endswith("+00:00")
    assert rows[0]["raw_json"]  # raw JSON preserved in the DB


def test_unique_constraint_prevents_duplicates(config):
    records = _records_from_fixture(config)
    conn = database.get_connection(config.DB_PATH)
    try:
        assert database.insert_alert(conn, records[0]) == 1
        assert database.insert_alert(conn, records[0]) == 0  # duplicate ignored
        conn.commit()
    finally:
        conn.close()
    assert database.count_alerts(config.DB_PATH) == 1


def test_query_filters(config):
    records = _records_from_fixture(config)
    conn = database.get_connection(config.DB_PATH)
    try:
        for rec in records:
            database.insert_alert(conn, rec)
        conn.commit()
    finally:
        conn.close()

    assert len(database.query_alerts(config.DB_PATH, {"severity": 3})) == 2
    assert len(database.query_alerts(config.DB_PATH, {"signature_id": 1000001})) == 1
    assert len(database.query_alerts(config.DB_PATH, {"src_ip": "127.0.0.1"})) == 2
    assert len(database.query_alerts(config.DB_PATH, {"signature": "Warning"})) == 1
    assert len(database.query_alerts(config.DB_PATH, {"q": "cyberguard-test"})) == 1
    # Date range on timestamp_utc.
    assert len(
        database.query_alerts(
            config.DB_PATH,
            {
                "date_from": "2026-11-09T00:00:00.000000+00:00",
                "date_to": "2026-11-10T00:00:00.000000+00:00",
            },
        )
    ) == 2
    assert len(
        database.query_alerts(
            config.DB_PATH, {"date_from": "2026-11-10T00:00:00.000000+00:00"}
        )
    ) == 0


def test_indexes_exist(config):
    conn = database.get_connection(config.DB_PATH)
    try:
        names = {
            r["name"]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index'"
            )
        }
    finally:
        conn.close()
    assert {
        "idx_alerts_timestamp_utc",
        "idx_alerts_signature_id",
        "idx_alerts_severity",
        "idx_alerts_src_ip",
    } <= names


def test_get_stats_with_since(config):
    records = _records_from_fixture(config)
    conn = database.get_connection(config.DB_PATH)
    try:
        for rec in records:
            database.insert_alert(conn, rec)
        conn.commit()
    finally:
        conn.close()

    stats = database.get_stats(
        config.DB_PATH, since_utc="2026-11-09T00:00:00.000000+00:00"
    )
    assert stats["total"] == 2
    assert stats["by_severity"] == {"3": 2}
    assert stats["by_signature"]["CyberGuard Test Alert"] == 1
    assert stats["by_src_ip"]["127.0.0.1"] == 2
    assert stats["last_24h"] == 2

    stats_future = database.get_stats(
        config.DB_PATH, since_utc="2026-11-10T00:00:00.000000+00:00"
    )
    assert stats_future["last_24h"] == 0


def test_parameterized_insert_rejects_injection_as_data(config):
    # A malicious-looking signature is stored as literal data, not executed.
    records = _records_from_fixture(config)
    records[0]["signature"] = "evil'); DROP TABLE alerts;--"
    conn = database.get_connection(config.DB_PATH)
    try:
        database.insert_alert(conn, records[0])
        conn.commit()
    finally:
        conn.close()
    # Table still exists and holds the row with the literal signature.
    rows = database.query_alerts(config.DB_PATH)
    assert len(rows) == 1
    assert "DROP TABLE" in rows[0]["signature"]
