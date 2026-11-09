"""Tests for the Flask API (health, status, alerts, stats).

Uses Flask's test client (no socket binding), a temp DB, and a temp EVE file.
No Suricata and no network are required.
"""

import pytest

from app import create_app
from app.services import alert_service
from tests.conftest import LINE1, LINE2, make_config, write_eve


@pytest.fixture
def client(tmp_path):
    cfg = make_config(tmp_path)
    write_eve(cfg, LINE1, LINE2)
    app = create_app(cfg)
    alert_service.ingest(cfg)  # populate from the real fixtures
    app.config.update(TESTING=True)
    return app.test_client(), cfg


def test_health(client):
    c, _ = client
    resp = c.get("/api/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_status_unverified_without_proc(client):
    c, _ = client
    data = c.get("/api/status").get_json()
    assert data["backend_running"] is True
    assert data["eve_file_exists"] is True
    assert data["suricata_process"] == "unverified"
    assert data["total_alerts"] == 2
    # Must never claim running just because eve.json exists.
    assert data["suricata_process"] != "verified_running"


def test_status_not_running_with_proc_but_no_pid(tmp_path):
    proc = tmp_path / "proc"
    proc.mkdir()
    cfg = make_config(tmp_path, PROC_BASE=str(proc))
    write_eve(cfg, LINE1)
    app = create_app(cfg)
    data = app.test_client().get("/api/status").get_json()
    assert data["suricata_process"] == "verified_not_running"


def test_alerts_newest_first_and_pagination(client):
    c, _ = client
    data = c.get("/api/alerts").get_json()
    assert data["count"] == 2
    assert data["alerts"][0]["signature_id"] == 1000002

    page = c.get("/api/alerts?limit=1&offset=1").get_json()
    assert page["count"] == 1
    assert page["alerts"][0]["signature_id"] == 1000001


def test_alerts_filters(client):
    c, _ = client
    assert c.get("/api/alerts?severity=3").get_json()["count"] == 2
    assert c.get("/api/alerts?signature_id=1000001").get_json()["count"] == 1
    assert c.get("/api/alerts?src_ip=127.0.0.1").get_json()["count"] == 2
    assert c.get("/api/alerts?signature=Warning").get_json()["count"] == 1
    assert c.get("/api/alerts?q=cyberguard-test").get_json()["count"] == 1


def test_alerts_date_filter(client):
    c, _ = client
    in_range = c.get("/api/alerts?from=2026-11-09&to=2026-11-10").get_json()
    assert in_range["count"] == 2
    out_of_range = c.get("/api/alerts?from=2026-11-10").get_json()
    assert out_of_range["count"] == 0


def test_alerts_category_display(client):
    c, _ = client
    data = c.get("/api/alerts").get_json()
    assert data["alerts"][0]["category"] == "uncategorized"


def test_stats(client):
    c, _ = client
    data = c.get("/api/stats").get_json()
    assert data["total"] == 2
    assert data["by_severity"] == {"3": 2}
    assert data["by_signature"]["CyberGuard Warning Alert"] == 1
    assert data["by_src_ip"]["127.0.0.1"] == 2
    assert isinstance(data["last_24h"], int)
