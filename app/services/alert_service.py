"""Higher-level queries for the API layer.

Reports the honest state of the detection engine and stored alerts. This module
does NOT detect anything — it only reflects whether Suricata's EVE JSON output
exists and how many genuine alerts have been stored.
"""

from app.services import database, eve_reader


def get_engine_status(config):
    """Return an honest status of the Suricata detection engine.

    Suricata is the only detection engine. We consider it "configured" only
    when its EVE JSON output file is present and readable. We never report a
    fake active status.
    """
    eve_path = config.EVE_JSON_PATH
    eve_exists = eve_reader.eve_file_exists(eve_path)

    if eve_exists:
        message = "Suricata EVE JSON output detected."
    else:
        message = (
            "Suricata detection engine is NOT configured. No EVE JSON output "
            "was found. Python does not perform detection — install and "
            "configure Suricata to generate genuine security events."
        )

    return {
        "detection_engine": "suricata",
        "suricata_configured": eve_exists,
        "eve_json_path": eve_path,
        "eve_json_exists": eve_exists,
        "message": message,
    }


def get_alert_count(config):
    """Return the number of stored alerts, or 0 if the database is unavailable."""
    try:
        return database.count_alerts(config.SQLITE_DB_PATH)
    except Exception:
        return 0
