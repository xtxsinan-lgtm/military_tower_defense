"""HTTP server and JSON API router for tools.webproto."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import traceback
from typing import Any, Dict, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from .session import SESSION_STORE, GameSession

STATIC_DIR = Path(__file__).resolve().parent / "static"


def dispatch_api(
    method: str,
    url_path: str,
    body: Optional[Dict[str, Any]] = None,
    session: Optional[GameSession] = None,
) -> Tuple[int, Dict[str, Any]]:
    """Route API requests to GameSession and return (status_code, response_dict)."""
    sess = session or SESSION_STORE
    parsed = urlparse(url_path)
    route = parsed.path.rstrip("/")
    qs = parse_qs(parsed.query)
    payload = body or {}

    try:
        if method == "GET" and route == "/api/init":
            lvl = qs.get("level", ["test_01"])[0]
            night = int(qs.get("night", [str(sess.night_index)])[0])
            seed = int(qs.get("seed", [str(sess.seed)])[0])
            reset = qs.get("reset", ["0"])[0] in ("1", "true", "True")
            return 200, sess.init_level(level_id=lvl, night_index=night, seed=seed, reset=reset)

        if method == "POST" and route == "/api/coverage":
            return 200, sess.compute_coverage(payload)

        if method == "POST" and route == "/api/start_night":
            return 200, sess.start_night(payload)

        if method == "POST" and route == "/api/step":
            ticks = int(payload.get("ticks", 5))
            return 200, sess.step(ticks=ticks)

        if method == "POST" and route == "/api/command":
            return 200, sess.apply_command(payload)

        if method == "POST" and route == "/api/next_night":
            return 200, sess.advance_to_next_night(payload)

        return 404, {"ok": False, "error": f"Unknown API endpoint: {method} {route}"}
    except Exception as exc:
        return 500, {
            "ok": False,
            "error": str(exc),
            "trace": traceback.format_exc(),
        }


class WebProtoHandler(BaseHTTPRequestHandler):
    """Zero-dependency HTTP request handler for API and static frontend assets."""

    server_version = "NightwatchWebProto/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        # Keep console output quiet during high-frequency /api/step polling
        if getattr(self.server, "verbose", False):
            super().log_message(fmt, *args)

    def _send_json(self, status: int, data: Dict[str, Any]) -> None:
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def _serve_static(self, rel_path: str) -> None:
        if not rel_path or rel_path == "/":
            rel_path = "index.html"
        clean = rel_path.lstrip("/")
        if clean.startswith("static/"):
            clean = clean[len("static/") :]
        target = (STATIC_DIR / clean).resolve()
        if not str(target).startswith(str(STATIC_DIR.resolve())) or not target.is_file():
            self.send_error(404, f"File not found: {rel_path}")
            return
        ctype, _ = mimetypes.guess_type(str(target))
        if not ctype:
            ctype = "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript", "application/json"):
            ctype += "; charset=utf-8"
        raw = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        if self.path.startswith("/api/"):
            status, resp = dispatch_api("GET", self.path, None, getattr(self.server, "session", SESSION_STORE))
            self._send_json(status, resp)
            return
        parsed = urlparse(self.path)
        self._serve_static(parsed.path)

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw_body = self.rfile.read(length) if length > 0 else b"{}"
        try:
            body = json.loads(raw_body.decode("utf-8")) if raw_body else {}
        except Exception:
            body = {}
        status, resp = dispatch_api("POST", self.path, body, getattr(self.server, "session", SESSION_STORE))
        self._send_json(status, resp)


class WebProtoServer(ThreadingHTTPServer):
    allow_reuse_address = True

    def __init__(self, server_address: Tuple[str, int], session: Optional[GameSession] = None, verbose: bool = False):
        super().__init__(server_address, WebProtoHandler)
        self.session = session or SESSION_STORE
        self.verbose = verbose


def run_server(host: str = "127.0.0.1", port: int = 8765, verbose: bool = False) -> None:
    srv = WebProtoServer((host, port), verbose=verbose)
    print(f"============================================================")
    print(f"  《守夜》Nightwatch 网页版可交互纸面原型已启动")
    print(f"  请在浏览器打开: http://{host}:{port}/")
    print(f"  模拟核心: tools.papersim (14 系统确定性模拟)")
    print(f"============================================================")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n正在关闭服务...")
    finally:
        srv.server_close()
