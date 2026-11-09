"""Tests for the read-only rule parser and the /api/rules endpoint.

The parser only DISPLAYS the state of the Suricata rules file — it never decides
detection. These tests run on Windows with no Suricata: they use temporary rule
files only and never read the real /var/lib path.
"""

from app import create_app
from app.services import rule_service
from tests.conftest import make_config

# A normal enabled rule (byte-shaped like the real cyberguard.rules lines).
ENABLED_RULE = (
    'alert http any any -> any any (msg:"CyberGuard Test Alert"; '
    'flow:to_server,established; http.uri; content:"/cyberguard-test"; '
    "priority:1; classtype:misc-activity; sid:1000001; rev:2;)"
)
# A disabled rule is the same line prefixed with '#' (matches Phase 3's ^#alert).
DISABLED_RULE = "#" + (
    'alert http any any -> any any (msg:"CyberGuard Warning Alert"; '
    'flow:to_server,established; http.uri; content:"/cyberguard-warning"; '
    "priority:2; classtype:misc-activity; sid:1000002; rev:2;)"
)


def write_rules(tmp_path, *lines):
    """Write rule lines with real LF endings and return the path as a string."""
    path = tmp_path / "cyberguard.rules"
    path.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
    return str(path)


def test_parses_enabled_rule(tmp_path):
    result = rule_service.parse_rules_file(write_rules(tmp_path, ENABLED_RULE))
    assert result["file_found"] is True
    assert result["file_mtime"]  # a timestamp string, not None
    assert len(result["rules"]) == 1
    rule = result["rules"][0]
    assert rule["sid"] == 1000001
    assert rule["msg"] == "CyberGuard Test Alert"
    assert rule["priority"] == 1
    assert rule["classtype"] == "misc-activity"
    assert rule["rev"] == 2
    assert rule["enabled"] is True


def test_parses_disabled_rule(tmp_path):
    result = rule_service.parse_rules_file(write_rules(tmp_path, DISABLED_RULE))
    assert len(result["rules"]) == 1
    rule = result["rules"][0]
    assert rule["sid"] == 1000002
    assert rule["msg"] == "CyberGuard Warning Alert"
    assert rule["enabled"] is False


def test_ignores_comments_and_blank_lines(tmp_path):
    path = write_rules(
        tmp_path,
        "# CyberGuard custom detection rules (source of truth).",
        "# sid 1000001 — note: this comment is not a rule.",
        "",
        ENABLED_RULE,
    )
    result = rule_service.parse_rules_file(path)
    assert len(result["rules"]) == 1  # only the real alert line counts


def test_missing_file_does_not_crash(tmp_path):
    result = rule_service.parse_rules_file(str(tmp_path / "nope.rules"))
    assert result["file_found"] is False
    assert result["rules"] == []
    assert result["file_mtime"] is None


def test_malformed_rule_line_is_tolerated(tmp_path):
    malformed = 'alert http any any -> any any (msg:"No SID here"; classtype:misc-activity;)'
    rule = rule_service.parse_rules_file(write_rules(tmp_path, malformed))["rules"][0]
    assert rule["sid"] is None  # missing sid -> None, never a crash
    assert rule["msg"] == "No SID here"
    assert rule["priority"] is None
    assert rule["rev"] is None
    assert rule["enabled"] is True


def test_option_order_does_not_matter(tmp_path):
    reordered = (
        "alert tcp any any -> any any (sid:1000003; rev:1; "
        'msg:"Reordered Options"; priority:3; classtype:misc-activity;)'
    )
    rule = rule_service.parse_rules_file(write_rules(tmp_path, reordered))["rules"][0]
    assert rule["sid"] == 1000003
    assert rule["msg"] == "Reordered Options"
    assert rule["priority"] == 3
    assert rule["classtype"] == "misc-activity"
    assert rule["rev"] == 1


def test_api_rules_endpoint(tmp_path):
    path = write_rules(tmp_path, ENABLED_RULE, DISABLED_RULE)
    cfg = make_config(tmp_path, RULES_PATH=path)
    app = create_app(cfg)
    data = app.test_client().get("/api/rules").get_json()
    assert data["file_found"] is True
    assert {r["sid"] for r in data["rules"]} == {1000001, 1000002}
    # Honest disclaimer: this is file state, not proof Suricata loaded it.
    assert "not proof" in data["note"].lower()


def test_api_rules_missing_file(tmp_path):
    cfg = make_config(tmp_path, RULES_PATH=str(tmp_path / "absent.rules"))
    app = create_app(cfg)
    data = app.test_client().get("/api/rules").get_json()
    assert data["file_found"] is False
    assert data["rules"] == []
