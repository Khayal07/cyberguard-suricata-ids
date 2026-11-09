"""CyberGuard Flask application package.

Exposes an application factory, ``create_app``, which wires configuration,
ensures the SQLite schema exists, and registers routes.

Architecture note: this package NEVER performs intrusion detection. It only
reads, stores, and serves the genuine events that Suricata writes to EVE JSON.
"""

from flask import Flask, jsonify, render_template

from app.config import Config
from app.services import alert_service, database


def create_app(config=None):
    """Build and return the configured Flask application."""
    config = config or Config

    app = Flask(__name__)
    app.config.from_object(config)
    # Keep the active config object available to request handlers.
    app.config["APP_CONFIG"] = config

    # Ensure the SQLite schema exists. The database is empty until Suricata
    # events are ingested in a later phase.
    database.init_db(config.SQLITE_DB_PATH)

    _register_routes(app, config)
    return app


def _register_routes(app, config):
    """Register page and API routes on the given app."""

    # --- Pages ---
    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/alerts")
    def alerts_page():
        return render_template("alerts.html")

    @app.route("/rule-lab")
    def rule_lab_page():
        return render_template("rule_lab.html")

    # --- API ---
    @app.route("/api/health")
    def health():
        """Liveness of the Flask API itself (NOT the detection engine)."""
        return jsonify(
            {
                "status": "ok",
                "service": "cyberguard",
                "component": "flask-api",
            }
        )

    @app.route("/api/status")
    def status():
        """Honest status of the Suricata detection engine and stored alerts."""
        engine = alert_service.get_engine_status(config)
        engine["alert_count"] = alert_service.get_alert_count(config)
        return jsonify(engine)
