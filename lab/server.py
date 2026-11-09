#!/usr/bin/env python3
"""Minimal harmless HTTP test server for the CyberGuard lab.

Bound to 127.0.0.1 ONLY. Serves fixed, in-memory responses so controlled local
traffic can exercise the Suricata detection rules (sid 1000001 / 1000002):

    GET /                    -> 200 (index page)
    GET /index.html          -> 200 (index page)
    GET /cyberguard-test     -> 200 text/plain  (trips "CyberGuard Test Alert")
    GET /cyberguard-warning  -> 200 text/plain  (trips "CyberGuard Warning Alert")
    anything else            -> 404

Standard library only. It does NOT write files, execute shell commands, or list
directories. Suricata matches the HTTP request URI, so the response status code
does not affect detection.

NOTE: written on Windows; NOT yet run on the Kali VM. It will be validated when
the repository is cloned onto the VM. (The manual Phase 3 tests used
`python3 -m http.server`, which returned 404 for the /cyberguard-* paths; this
purpose-built server returns 200 for them instead. Either way Suricata alerts on
the request URI.)

Usage:
    python lab/server.py [--port 8000]
"""

import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer

INDEX_HTML = (
    b"<!DOCTYPE html>\n"
    b"<html><body><h1>CyberGuard lab server</h1>"
    b"<p>Harmless local test server.</p></body></html>\n"
)


class CyberGuardLabHandler(BaseHTTPRequestHandler):
    """Handle GET requests with fixed, in-memory responses only."""

    server_version = "CyberGuardLab/1.0"

    def _respond(self, status, body, content_type="text/plain; charset=utf-8"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        # Ignore any query string; match on the path only.
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            self._respond(200, INDEX_HTML, "text/html; charset=utf-8")
        elif path == "/cyberguard-test":
            self._respond(200, b"CyberGuard test marker\n")
        elif path == "/cyberguard-warning":
            self._respond(200, b"CyberGuard warning marker\n")
        else:
            self._respond(404, b"Not Found\n")


def main():
    parser = argparse.ArgumentParser(
        description="CyberGuard harmless lab HTTP server (localhost only)."
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to listen on (default: 8000).",
    )
    args = parser.parse_args()

    # Bind to loopback only — never expose this server beyond the local machine.
    server = HTTPServer(("127.0.0.1", args.port), CyberGuardLabHandler)
    print(
        f"CyberGuard lab server listening on http://127.0.0.1:{args.port} "
        "(Ctrl+C to stop)"
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
