"""Rule service: read-only view of the Suricata rules file.

This module PARSES a rules file so the Rule Lab can DISPLAY its contents. It is
strictly read-only and makes no detection decision: it never edits the file,
never runs Suricata, and never claims a rule is active. Whether Suricata has
actually loaded a rule can only be proven by Suricata itself — the Rule Lab
shows *file state*, not proof of loading.

The path is fixed by configuration (``CYBERGUARD_RULES_PATH``); it is NEVER taken
from an HTTP request, so no endpoint can be tricked into reading another file.
"""

import os
import re
from datetime import datetime, timezone

# Honest disclaimer surfaced in the API and the UI.
RULE_STATE_NOTE = "File state, not proof that Suricata loaded it."

# Field extractors — order-independent, tolerant of missing options.
_SID = re.compile(r"\bsid:\s*(\d+)")
_REV = re.compile(r"\brev:\s*(\d+)")
_PRIORITY = re.compile(r"\bpriority:\s*(\d+)")
_MSG = re.compile(r'\bmsg:\s*"([^"]*)"')
_CLASSTYPE = re.compile(r"\bclasstype:\s*([^;]+)")

# A rule line starts with "alert" (enabled) or "#alert" (disabled). We allow
# optional spaces after the '#' so "# alert ..." is still recognized as a
# disabled rule rather than a plain comment.
_ENABLED = re.compile(r"^alert\b")
_DISABLED = re.compile(r"^#\s*alert\b")


def _int_or_none(match):
    return int(match.group(1)) if match else None


def _str_or_none(match):
    return match.group(1).strip() if match else None


def _parse_rule_line(line, enabled):
    """Extract the displayed fields from a single rule line (never raises)."""
    return {
        "sid": _int_or_none(_SID.search(line)),
        "msg": _str_or_none(_MSG.search(line)),
        "priority": _int_or_none(_PRIORITY.search(line)),
        "classtype": _str_or_none(_CLASSTYPE.search(line)),
        "rev": _int_or_none(_REV.search(line)),
        "enabled": enabled,
    }


def parse_rules_file(path):
    """Parse the rules file at ``path`` into a display-only summary.

    Returns a dict with ``file_found``, ``file_path``, ``file_mtime`` (ISO UTC or
    None), ``rules`` (list of parsed rule dicts in file order), and ``note``.
    A missing or unreadable file yields ``file_found=False`` and an empty list —
    it never raises.
    """
    summary = {
        "file_found": False,
        "file_path": path,
        "file_mtime": None,
        "rules": [],
        "note": RULE_STATE_NOTE,
    }

    if not path or not os.path.isfile(path):
        return summary

    try:
        mtime = os.path.getmtime(path)
        summary["file_mtime"] = (
            datetime.fromtimestamp(mtime, timezone.utc)
            .strftime("%Y-%m-%dT%H:%M:%S")
            + "+00:00"
        )
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            lines = handle.read().splitlines()
    except OSError:
        # File vanished or is unreadable between the checks above — stay honest.
        return summary

    summary["file_found"] = True
    rules = []
    for raw in lines:
        line = raw.strip()
        if _ENABLED.match(line):
            rules.append(_parse_rule_line(line, enabled=True))
        elif _DISABLED.match(line):
            rules.append(_parse_rule_line(line, enabled=False))
        # Any other line (blank or a plain comment) is ignored, not a rule.
    summary["rules"] = rules
    return summary


def get_rules(config):
    """Return the rule summary for the configured rules path (read-only)."""
    return parse_rules_file(getattr(config, "RULES_PATH", None))
