#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Jonathan George
"""
Claude Doc Server — serves .claude/ files and persists annotations to JSON.

GET  /                          → directory listing
GET  /<file>                    → serve static file
GET  /annotations/<docname>     → read saved annotations for a doc
POST /annotations/<docname>     → save annotations JSON for a doc

Port selection (first match wins):
  1. CLAUDE_DOC_PORT environment variable
  2. Default 7432
  3. Next free port scanning upward — handles multiple concurrent
     project instances without manual configuration

The bound port is written to server.port so the IDE keybinding updater
and CLAUDE.md workflow can discover it without hardcoding. Cleaned up on
normal exit and SIGTERM.
"""

import http.server
import json
import os
import signal
import socket
import sys
from pathlib import Path
from urllib.parse import urlparse

PREFERRED_PORT = int(os.environ.get("CLAUDE_DOC_PORT", "7432"))
ROOT = Path(__file__).parent
PORT_FILE = ROOT / "server.port"
ANNOTATIONS_DIR = ROOT / "annotations"
ANNOTATIONS_DIR.mkdir(exist_ok=True)


def find_free_port(preferred: int, limit: int = 100) -> int:
    """Try preferred port first, then scan upward until a free one is found."""
    for port in range(preferred, preferred + limit):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("localhost", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No free port found in {preferred}–{preferred + limit - 1}")


def already_running(port: int) -> bool:
    """True if something is already accepting connections on localhost:port."""
    try:
        with socket.create_connection(("localhost", port), timeout=0.5):
            return True
    except OSError:
        return False


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, fmt, *args):
        # Suppress per-request noise; only log errors
        if args and str(args[1]) not in ("200", "304"):
            super().log_message(fmt, *args)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/annotations/"):
            self._get_annotations(parsed.path[len("/annotations/"):])
        elif parsed.path == "/docs":
            self._get_docs()
        else:
            super().do_GET()

    def _get_docs(self):
        import re
        from datetime import datetime
        docs = []
        for f in ROOT.glob("*.html"):
            try:
                content = f.read_text(encoding="utf-8", errors="ignore")
                title_m = re.search(r"<title>([^<]+)</title>", content, re.IGNORECASE)
                title = title_m.group(1).strip() if title_m else f.stem

                ann_count = 0
                ann_file = ANNOTATIONS_DIR / f"{f.stem}.json"
                if ann_file.exists():
                    try:
                        d = json.loads(ann_file.read_text())
                        ann_count = sum(1 for v in d.values() if str(v).strip())
                    except Exception:
                        pass

                dt_m = re.search(
                    r"-(\d{4})-(\d{2})-(\d{2})(?:-(\d{2})(\d{2})(\d{2}))?$", f.stem
                )
                if dt_m:
                    y, mo, d2 = dt_m.group(1), dt_m.group(2), dt_m.group(3)
                    h = dt_m.group(4) or "00"
                    mi = dt_m.group(5) or "00"
                    s = dt_m.group(6) or "00"
                    dt_str = f"{y}-{mo}-{d2} {h}:{mi}:{s}"
                    dt_ts = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S").timestamp()
                else:
                    dt_ts = f.stat().st_mtime
                    dt_str = datetime.fromtimestamp(dt_ts).strftime("%Y-%m-%d %H:%M:%S")

                docs.append({
                    "filename": f.name,
                    "datetime": dt_str,
                    "datetime_ts": dt_ts,
                    "title": title,
                    "annotation_count": ann_count,
                })
            except Exception:
                pass

        docs.sort(key=lambda x: x["datetime_ts"], reverse=True)
        data = json.dumps(docs).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self._cors()
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/annotations/"):
            self._post_annotations(parsed.path[len("/annotations/"):])
        else:
            self.send_error(404)

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _get_annotations(self, docname):
        path = ANNOTATIONS_DIR / f"{docname}.json"
        data = path.read_bytes() if path.exists() else b"{}"
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self._cors()
        self.end_headers()
        self.wfile.write(data)

    def _post_annotations(self, docname):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return
        path = ANNOTATIONS_DIR / f"{docname}.json"
        path.write_text(json.dumps(data, indent=2))
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self._cors()
        self.end_headers()
        self.wfile.write(json.dumps({"saved": True}).encode())


if __name__ == "__main__":
    # If a port file exists and that port is already answering, a healthy
    # instance is running — exit rather than start a duplicate.
    if PORT_FILE.exists():
        try:
            existing = int(PORT_FILE.read_text().strip())
            if already_running(existing):
                print(f"Claude doc server already running on port {existing}.")
                sys.exit(0)
        except (ValueError, OSError):
            pass

    port = find_free_port(PREFERRED_PORT)
    PORT_FILE.write_text(str(port))

    def _shutdown(signum=None, frame=None):
        PORT_FILE.unlink(missing_ok=True)
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)

    os.chdir(ROOT)
    server = http.server.HTTPServer(("localhost", port), Handler)
    print(f"Claude doc server: http://localhost:{port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        PORT_FILE.unlink(missing_ok=True)
