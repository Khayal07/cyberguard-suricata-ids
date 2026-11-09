"""CyberGuard application entry point.

Usage:
    python -m app.main               # run the Flask server + ingestion worker
    python -m app.main serve         # same as above
    python -m app.main ingest-once   # run a single ingestion cycle and exit
    python -m app.main telegram-test # send one Telegram connectivity test

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
from app.services import alert_service, database, telegram_notifier


def _should_start_worker(debug):
    """Start the worker once: always when not in debug; in debug only in the
    reloader child process."""
    if not debug:
        return True
    return os.environ.get("WERKZEUG_RUN_MAIN") == "true"


def run_server():
    app = create_app()
    if _should_start_worker(Config.DEBUG):
        notifier = telegram_notifier.TelegramNotifier(Config)
        telegram_notifier.set_active(notifier)
        worker = alert_service.IngestionWorker(Config, notifier=notifier)
        worker.start()
        atexit.register(worker.stop)
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)


def ingest_once():
    # No notifier is passed: the one-shot CLI never sends Telegram messages.
    database.init_db(Config.DB_PATH)
    summary = alert_service.ingest(Config)
    print(summary)


def telegram_test():
    """Send one clearly-labelled connectivity test. Prints OK/failed, never the
    token. Does nothing (prints a hint) when Telegram is not configured."""
    notifier = telegram_notifier.TelegramNotifier(Config, async_send=False)
    if not notifier.enabled:
        print(
            "Telegram is not configured — set CYBERGUARD_TELEGRAM_TOKEN and "
            "CYBERGUARD_TELEGRAM_CHAT_ID in your .env. Nothing was sent."
        )
        return
    if notifier.send_test():
        print("OK: Telegram connectivity test message sent.")
    else:
        print("FAILED: could not send the Telegram test (see logs; token not shown).")


def main():
    parser = argparse.ArgumentParser(description="CyberGuard backend.")
    parser.add_argument(
        "command",
        nargs="?",
        default="serve",
        choices=["serve", "ingest-once", "telegram-test"],
        help="serve (default) runs the API + worker; ingest-once runs one "
        "cycle; telegram-test sends one Telegram connectivity test.",
    )
    args = parser.parse_args()
    if args.command == "ingest-once":
        ingest_once()
    elif args.command == "telegram-test":
        telegram_test()
    else:
        run_server()


if __name__ == "__main__":
    main()
