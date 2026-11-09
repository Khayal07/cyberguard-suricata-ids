"""CyberGuard Flask application package.

Exposes an application factory, ``create_app``, which wires configuration,
ensures the SQLite schema exists, and registers routes.

Architecture note: this package NEVER performs intrusion detection. It only
reads, stores, and serves the genuine events that Suricata writes to EVE JSON.
No route executes shell commands or accepts filesystem paths.
"""

from flask import Flask, jsonify, render_template, request

from app.config import Config
from app.services import alert_service, database, rule_service


def create_app(config=None):
    """Build and return the configured Flask application.

    The background ingestion worker is NOT started here (so importing the app
    in tests never spawns threads); it is started explicitly in app/main.py.
    """
    config = config or Config

    app = Flask(__name__)
    app.config.from_object(config)
    app.config["APP_CONFIG"] = config

    database.init_db(config.DB_PATH)

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
            {"status": "ok", "service": "cyberguard", "component": "flask-api"}
        )

    @app.route("/api/status")
    def status():
        """Honest status: backend, EVE file, and verified Suricata process."""
        return jsonify(alert_service.get_status(config))

    @app.route("/api/alerts")
    def alerts():
        """Paginated, filterable list of stored Suricata alerts (newest first)."""
        filters = alert_service.build_filters(request.args)
        limit = request.args.get("limit", 50)
        offset = request.args.get("offset", 0)
        try:
            limit = int(limit)
            offset = int(offset)
        except (TypeError, ValueError):
            limit, offset = 50, 0
        return jsonify(alert_service.list_alerts(config, filters, limit, offset))

    @app.route("/api/stats")
    def stats():
        """Aggregate statistics over stored alerts."""
        return jsonify(alert_service.get_stats(config))

    @app.route("/api/rules")
    def rules():
        """Read-only view of the Suricata rules FILE (not proof of loading).

        Reads a single configured path; never a path from the request, and never
        edits the file or runs Suricata. Detection stays entirely with Suricata.
        """
        return jsonify(rule_service.get_rules(config))
