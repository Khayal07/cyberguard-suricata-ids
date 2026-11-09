"""Read and parse Suricata EVE JSON output.

EVE JSON is written by Suricata as one JSON object per line (JSON Lines). This
module only *reads* that output — it never generates events. If the file does
not exist yet (Suricata not configured), readers return empty results instead
of raising, so the rest of the app keeps working.
"""

import json
import os


def eve_file_exists(path):
    """Return True if the EVE JSON file exists and is a regular file."""
    return bool(path) and os.path.isfile(path)


def parse_line(line):
    """Parse a single EVE JSON line into a dict, or None if invalid/empty."""
    line = line.strip()
    if not line:
        return None
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return None


def read_events(path, limit=None):
    """Read EVE JSON events from ``path``.

    Returns a list of event dicts. Malformed lines are skipped rather than
    crashing the reader. If ``limit`` is given, returns the most recent
    ``limit`` events.
    """
    events = []
    if not eve_file_exists(path):
        return events

    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            event = parse_line(line)
            if event is not None:
                events.append(event)

    if limit is not None and limit >= 0:
        return events[-limit:]
    return events


def count_events(path):
    """Return the number of valid EVE JSON events in ``path`` (0 if missing)."""
    return len(read_events(path))
