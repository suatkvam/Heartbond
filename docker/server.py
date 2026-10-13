"""Demo GPU-node stand-in (D-04): GET /health -> 200, anything else -> 404."""
import json
import os
import signal
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BODY = json.dumps({"ok": True, "node": os.environ.get("NODE", "node")}).encode()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        ok = self.path == "/health"
        body = BODY if ok else b'{"ok": false}'
        self.send_response(200 if ok else 404)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


# PID 1 ignores SIGTERM unless a handler is installed; exit at once so probes fail right away.
signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
