"""CyberGuard application entry point.

Usage:
    python -m app.main              # run the Flask server + ingestion worker
    python -m app.main serve        # same as above
    python -m app.main ingest-once  # run a single ingestion cycle and exit

The background ingestion worker polls EVE JSON every CYBERGUARD_POLL_SECONDS.
When Flask's debug reloader is active it restarts the process, so the worker is
started only in the reloader's child (WERKZEUG_RUN_MAIN == "true") to avoid
running two workers.
"""

import argparse
import atexit
import os

from app import create_app
from app.config import Config
from app.services import alert_service, database


def _should_start_worker(debug):
    """Start the worker once: always when not in debug; in debug only in the
    reloader child process."""
    if not debug:
        return True
    return os.environ.get("WERKZEUG_RUN_MAIN") == "true"


def run_server():
    app = create_app()
    if _should_start_worker(Config.DEBUG):
        worker = alert_service.IngestionWorker(Config)
        worker.start()
        atexit.register(worker.stop)
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)


def ingest_once():
    database.init_db(Config.DB_PATH)
    summary = alert_service.ingest(Config)
    print(summary)


def main():
    parser = argparse.ArgumentParser(description="CyberGuard backend.")
    parser.add_argument(
        "command",
        nargs="?",
        default="serve",
        choices=["serve", "ingest-once"],
        help="serve (default) runs the API + worker; ingest-once runs one cycle.",
    )
    args = parser.parse_args()
    if args.command == "ingest-once":
        ingest_once()
    else:
        run_server()


if __name__ == "__main__":
    main()
