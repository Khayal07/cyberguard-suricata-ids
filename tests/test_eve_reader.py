"""Tests for app.services.eve_reader.

These verify the reader behaves safely whether or not Suricata EVE JSON exists,
and that it parses genuine JSON-Lines output correctly.
"""

import json

from app.services import eve_reader


def test_eve_file_exists_false_for_missing(tmp_path):
    missing = tmp_path / "eve.json"
    assert eve_reader.eve_file_exists(str(missing)) is False


def test_eve_file_exists_false_for_empty_path():
    assert eve_reader.eve_file_exists("") is False


def test_read_events_missing_file_returns_empty(tmp_path):
    missing = tmp_path / "eve.json"
    assert eve_reader.read_events(str(missing)) == []


def test_parse_line_valid_and_invalid():
    assert eve_reader.parse_line('{"event_type": "alert"}') == {"event_type": "alert"}
    assert eve_reader.parse_line("") is None
    assert eve_reader.parse_line("   ") is None
    assert eve_reader.parse_line("not json") is None


def test_read_events_parses_json_lines(tmp_path):
    eve = tmp_path / "eve.json"
    events = [
        {"event_type": "alert", "signature_id": 1000001},
        {"event_type": "flow", "proto": "TCP"},
    ]
    eve.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")

    result = eve_reader.read_events(str(eve))
    assert result == events


def test_read_events_skips_malformed_lines(tmp_path):
    eve = tmp_path / "eve.json"
    eve.write_text(
        '{"event_type": "alert"}\n'
        "this line is broken\n"
        "\n"
        '{"event_type": "flow"}\n',
        encoding="utf-8",
    )

    result = eve_reader.read_events(str(eve))
    assert result == [{"event_type": "alert"}, {"event_type": "flow"}]


def test_read_events_limit_returns_most_recent(tmp_path):
    eve = tmp_path / "eve.json"
    lines = [json.dumps({"n": i}) for i in range(5)]
    eve.write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = eve_reader.read_events(str(eve), limit=2)
    assert result == [{"n": 3}, {"n": 4}]


def test_count_events(tmp_path):
    eve = tmp_path / "eve.json"
    eve.write_text('{"a": 1}\n{"b": 2}\n', encoding="utf-8")
    assert eve_reader.count_events(str(eve)) == 2
    assert eve_reader.count_events(str(tmp_path / "missing.json")) == 0
