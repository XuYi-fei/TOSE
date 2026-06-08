from __future__ import annotations

import argparse
import json
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .data_loader import DashboardBundle, build_trace_detail, scan_dashboard_bundle


class DashboardServer:
    def __init__(self, root: str | Path, host: str = "127.0.0.1", port: int = 8765):
        self.root = Path(root).resolve()
        self.host = host
        self.port = port
        self.static_dir = Path(__file__).resolve().parent / "static"
        self.bundle: DashboardBundle = scan_dashboard_bundle(self.root)
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def base_url(self) -> str:
        if self._server is None:
            return f"http://{self.host}:{self.port}"
        return f"http://{self.host}:{self._server.server_port}"

    def start(self) -> None:
        parent = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                parent._handle_request(self)

            def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
                return

        self._server = ThreadingHTTPServer((self.host, self.port), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2)

    def rescan(self) -> None:
        self.bundle = scan_dashboard_bundle(self.root)

    def read_static_text(self, filename: str) -> str:
        return (self.static_dir / filename).read_text(encoding="utf-8")

    def get_data_payload(self) -> Any:
        return self.bundle.payload

    def get_scan_payload(self) -> Dict[str, Any]:
        self.rescan()
        return {
            "status": "ok",
            "generated_at": self.bundle.payload.get("generated_at"),
            "result_count": len(self.bundle.payload.get("results", [])),
        }

    def get_trace_detail_payload(self, result_id: str, filename: str) -> Dict[str, Any]:
        return build_trace_detail(self.bundle, self.root, result_id, filename)

    def _handle_request(self, handler: BaseHTTPRequestHandler) -> None:
        parsed = urlparse(handler.path)
        if parsed.path == "/":
            return self._serve_static(handler, "index.html", "text/html; charset=utf-8")
        if parsed.path == "/app.js":
            return self._serve_static(handler, "app.js", "text/javascript; charset=utf-8")
        if parsed.path == "/styles.css":
            return self._serve_static(handler, "styles.css", "text/css; charset=utf-8")
        if parsed.path == "/api/data":
            return self._serve_json(handler, self.get_data_payload())
        if parsed.path == "/api/scan":
            return self._serve_json(handler, self.get_scan_payload())
        if parsed.path == "/api/trace-detail":
            params = parse_qs(parsed.query)
            result_id = params.get("result_id", [None])[0]
            filename = params.get("filename", [None])[0]
            if not result_id or not filename:
                return self._serve_json(
                    handler,
                    {"error": "result_id and filename are required"},
                    status=HTTPStatus.BAD_REQUEST,
                )
            try:
                detail = self.get_trace_detail_payload(result_id, filename)
            except KeyError:
                return self._serve_json(
                    handler,
                    {"error": "trace not found"},
                    status=HTTPStatus.NOT_FOUND,
                )
            return self._serve_json(handler, detail)

        return self._serve_json(handler, {"error": "not found"}, status=HTTPStatus.NOT_FOUND)

    def _serve_static(self, handler: BaseHTTPRequestHandler, filename: str, content_type: str) -> None:
        path = self.static_dir / filename
        data = path.read_bytes()
        handler.send_response(HTTPStatus.OK)
        handler.send_header("Content-Type", content_type)
        handler.send_header("Content-Length", str(len(data)))
        handler.end_headers()
        handler.wfile.write(data)

    @staticmethod
    def _serve_json(
        handler: BaseHTTPRequestHandler,
        payload: Any,
        status: HTTPStatus = HTTPStatus.OK,
    ) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        handler.send_response(status)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.send_header("Content-Length", str(len(data)))
        handler.end_headers()
        handler.wfile.write(data)


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the TOSE anomaly dashboard locally")
    parser.add_argument("--root", default=".", help="Repository root to scan")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind")
    args = parser.parse_args()

    server = DashboardServer(root=args.root, host=args.host, port=args.port)
    server.start()
    print(f"TOSE Detection Dashboard: {server.base_url}")
    print("Press Ctrl+C to stop.")
    try:
        while True:
            threading.Event().wait(3600)
    except KeyboardInterrupt:
        server.stop()


if __name__ == "__main__":
    main()
