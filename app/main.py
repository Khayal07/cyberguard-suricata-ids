"""CyberGuard application entry point.

Run with:
    python -m app.main

Builds the Flask app via the application factory and serves it on the
configured host/port (localhost by default).
"""

from app import create_app
from app.config import Config

app = create_app()

if __name__ == "__main__":
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
