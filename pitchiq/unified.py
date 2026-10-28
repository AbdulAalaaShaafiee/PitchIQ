"""Single-origin launcher for PitchIQ Basic (Streamlit) and Advanced (Figma UI).

The public browser origin is http://127.0.0.1:8765. The unified proxy routes
/ to the existing advanced browser UI and /basic/ to Streamlit. Both frontend
processes remain local and call the same PitchIQ project/analysis code.
"""
from __future__ import annotations

import asyncio
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

import tornado.httpclient
import tornado.httpserver
import tornado.httputil
import tornado.ioloop
import tornado.web
import tornado.websocket
from tornado.httpclient import AsyncHTTPClient, HTTPRequest
from tornado.websocket import websocket_connect

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HOST = os.getenv("PITCHIQ_UNIFIED_HOST", "127.0.0.1")
UNIFIED_PORT = int(os.getenv("PITCHIQ_UNIFIED_PORT", "8765"))
BASIC_PORT = int(os.getenv("PITCHIQ_BASIC_BACKEND_PORT", "8501"))
ADVANCED_PORT = int(os.getenv("PITCHIQ_ADVANCED_BACKEND_PORT", "8766"))
BASIC_PREFIX = "/basic"


def basic_mode_shell() -> str:
    """Return the unified Basic Mode shell containing the real Streamlit app."""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="dark">
  <title>PitchIQ · Basic Mode</title>
  <style>
    :root {{ color-scheme: dark; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; width: 100%; height: 100%; overflow: hidden; background: #061321; color: #edf7ff; }}
    .topbar {{ height: 48px; display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 0 16px; border-bottom: 1px solid rgba(103, 198, 226, .24); background: linear-gradient(120deg, #071624, #0a2031); }}
    .brand {{ font-weight: 850; letter-spacing: .02em; }}
    .mode {{ margin-left: 8px; color: #91b0c7; font-size: 12px; font-weight: 650; letter-spacing: .12em; text-transform: uppercase; }}
    .switch {{ color: #77fff0; text-decoration: none; font-weight: 750; font-size: 13px; border: 1px solid rgba(53, 240, 195, .38); border-radius: 10px; padding: 7px 11px; white-space: nowrap; }}
    .switch:hover, .switch:focus-visible {{ background: rgba(53, 240, 195, .12); outline: 2px solid transparent; }}
    iframe {{ display: block; width: 100%; height: calc(100% - 48px); border: 0; background: #061321; }}
    @media (max-width: 540px) {{ .topbar {{ padding: 0 9px; }} .mode {{ display: none; }} .switch {{ font-size: 12px; padding: 7px 9px; }} }}
  </style>
</head>
<body>
  <header class="topbar">
    <div><span class="brand">⚽ PitchIQ</span><span class="mode">Basic Mode</span></div>
    <a class="switch" href="/" title="Switch to Advanced Mode">↗ Advanced Mode</a>
  </header>
  <iframe title="PitchIQ Basic Mode — Streamlit dashboard" src="http://127.0.0.1:{BASIC_PORT}/basic/?embed=true" allow="clipboard-read; clipboard-write"></iframe>
</body>
</html>"""
STARTUP_TIMEOUT_SECONDS = 45

HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


def upstream_url(mode: str, request_uri: str) -> str:
    """Return the correct internal service URL while retaining path and query."""
    if mode == "basic":
        port = BASIC_PORT
    elif mode == "advanced":
        port = ADVANCED_PORT
    else:
        raise ValueError("Mode must be 'basic' or 'advanced'.")
    if not request_uri.startswith("/"):
        request_uri = "/" + request_uri
    return f"http://127.0.0.1:{port}{request_uri}"


def upstream_websocket_url(request_uri: str) -> str:
    """Map Streamlit's websocket path to its private local backend."""
    if not request_uri.startswith(BASIC_PREFIX + "/"):
        raise ValueError("Only Basic Mode websocket routes can be proxied.")
    return f"ws://127.0.0.1:{BASIC_PORT}{request_uri}"


def _port_is_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.25):
            return True
    except OSError:
        return False


def _wait_for_port(process: subprocess.Popen[Any], port: int, label: str) -> None:
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                f"{label} stopped during startup (exit code {process.returncode}). "
                "Review the error shown above."
            )
        if _port_is_open("127.0.0.1", port):
            return
        time.sleep(0.25)
    raise TimeoutError(f"{label} did not start listening on port {port} in time.")


def _wait_for_health(process: subprocess.Popen[Any], url: str, label: str) -> None:
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                f"{label} stopped during startup (exit code {process.returncode}). "
                "Review the error shown above."
            )
        try:
            with urlopen(url, timeout=1.0) as response:
                if 200 <= response.status < 300:
                    return
        except (OSError, URLError, TimeoutError) as exc:
            last_error = exc
        time.sleep(0.25)
    raise TimeoutError(f"{label} health check timed out. Last error: {last_error}")


def _stop_process(process: subprocess.Popen[Any]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


class HealthHandler(tornado.web.RequestHandler):
    def get(self) -> None:
        self.write({
            "ok": True,
            "service": "PitchIQ unified mode router",
            "basic_path": "/basic/",
            "advanced_path": "/",
        })


class ProxyHandler(tornado.web.RequestHandler):
    """HTTP reverse proxy for one private frontend/API service."""

    mode = "advanced"

    async def _forward(self) -> None:
        if self.mode == "basic" and self.request.path == BASIC_PREFIX:
            self.redirect(BASIC_PREFIX + "/", permanent=False)
            return

        request_headers = tornado.httputil.HTTPHeaders()
        for name, value in self.request.headers.get_all():
            lowered = name.lower()
            if lowered in HOP_BY_HOP_HEADERS or lowered in {"host", "content-length", "if-none-match", "if-modified-since"}:
                continue
            request_headers.add(name, value)

        # Retain the browser-facing host/origin. This makes the proxied
        # Streamlit app appear same-origin to its browser-side CORS/XSRF checks.
        browser_host = self.request.headers.get("Host", f"127.0.0.1:{UNIFIED_PORT}")
        request_headers["Host"] = browser_host
        request_headers["X-Forwarded-Host"] = browser_host
        request_headers["X-Forwarded-Proto"] = "http"
        if self.mode == "basic":
            request_headers["X-Forwarded-Prefix"] = BASIC_PREFIX

        body = self.request.body if self.request.method not in {"GET", "HEAD", "OPTIONS"} else None
        request = HTTPRequest(
            url=upstream_url(self.mode, self.request.uri),
            method=self.request.method,
            headers=request_headers,
            body=body,
            connect_timeout=5,
            request_timeout=120,
            follow_redirects=False,
            decompress_response=False,
            allow_nonstandard_methods=True,
        )

        try:
            response = await AsyncHTTPClient().fetch(request, raise_error=False)
        except Exception as exc:
            self.set_status(502)
            self.set_header("Content-Type", "text/plain; charset=utf-8")
            self.finish(
                f"PitchIQ {self.mode.title()} Mode is unavailable. "
                f"Please restart the unified launcher. Details: {exc}"
            )
            return

        self.set_status(response.code)
        for name, value in response.headers.get_all():
            lowered = name.lower()
            if lowered in HOP_BY_HOP_HEADERS:
                continue
            if lowered == "set-cookie":
                self.add_header(name, value)
            else:
                self.set_header(name, value)
        # HTTP 204/304 and HEAD responses must not carry a body.
        if response.code in {204, 304} or self.request.method == "HEAD":
            self.finish()
        else:
            self.finish(response.body or b"")

    async def get(self, _path: str = "") -> None:
        await self._forward()

    async def post(self, _path: str = "") -> None:
        await self._forward()

    async def put(self, _path: str = "") -> None:
        await self._forward()

    async def patch(self, _path: str = "") -> None:
        await self._forward()

    async def delete(self, _path: str = "") -> None:
        await self._forward()

    async def options(self, _path: str = "") -> None:
        await self._forward()

    async def head(self, _path: str = "") -> None:
        await self._forward()


class BasicProxyHandler(ProxyHandler):
    mode = "basic"

    async def get(self, _path: str = "") -> None:
        """Render a same-origin shell; let Streamlit own its websocket directly.

        Proxying Streamlit's websocket through a second Tornado client was failing
        in the browser even while ordinary HTTP requests returned 200. Embedding
        the direct local Streamlit URL keeps the unified mode selector while
        allowing Streamlit's websocket to connect to its own backend port.
        """
        if self.request.path == BASIC_PREFIX:
            self.redirect(BASIC_PREFIX + "/", permanent=False)
            return
        if self.request.path == BASIC_PREFIX + "/":
            self.set_header("Content-Type", "text/html; charset=utf-8")
            self.set_header("Cache-Control", "no-store")
            self.finish(basic_mode_shell())
            return
        await self._forward()


class AdvancedProxyHandler(ProxyHandler):
    mode = "advanced"


class StreamlitWebSocketProxy(tornado.websocket.WebSocketHandler):
    """Bridge Streamlit's bidirectional websocket through the unified origin."""

    def check_origin(self, origin: str) -> bool:
        # Both the router and the Streamlit backend are bound to loopback.
        # Browser origin is the same unified local origin, not a third-party host.
        expected = self.request.headers.get("Host", f"127.0.0.1:{UNIFIED_PORT}")
        return origin in {f"http://{expected}", f"https://{expected}"}

    async def open(self) -> None:
        headers = tornado.httputil.HTTPHeaders()
        for name in ("Origin", "Cookie", "User-Agent", "Sec-WebSocket-Protocol", "X-Xsrftoken"):
            value = self.request.headers.get(name)
            if value:
                headers[name] = value
        browser_host = self.request.headers.get("Host", f"127.0.0.1:{UNIFIED_PORT}")
        headers["Host"] = browser_host
        self._upstream_ready = asyncio.Event()
        self.upstream = None
        try:
            request = HTTPRequest(
                url=upstream_websocket_url(self.request.uri),
                headers=headers,
                connect_timeout=10,
                request_timeout=30,
            )
            self.upstream = await websocket_connect(request)
            self._upstream_ready.set()
            asyncio.create_task(self._read_backend())
        except Exception as exc:
            self._upstream_ready.set()
            self.close(code=1011, reason=f"Streamlit websocket connection failed: {exc}"[:120])

    async def on_message(self, message: str | bytes) -> None:
        await self._upstream_ready.wait()
        if self.upstream is None:
            return
        try:
            await self.upstream.write_message(message, binary=isinstance(message, bytes))
        except Exception:
            self.close(code=1011, reason="Could not forward message to Basic Mode")

    async def _read_backend(self) -> None:
        try:
            while self.upstream is not None:
                message = await self.upstream.read_message()
                if message is None:
                    if self.ws_connection is not None:
                        self.close(code=1000, reason="Basic Mode connection closed")
                    return
                self.write_message(message, binary=isinstance(message, bytes))
        except tornado.websocket.WebSocketClosedError:
            return
        except Exception:
            if self.ws_connection is not None:
                self.close(code=1011, reason="Basic Mode websocket proxy error")

    def on_close(self) -> None:
        upstream = getattr(self, "upstream", None)
        if upstream is not None:
            upstream.close()


def make_application() -> tornado.web.Application:
    """Build the single-origin router. Basic websocket rule must precede HTTP proxy."""
    return tornado.web.Application(
        [
            (r"/__unified/health", HealthHandler),
            (r"/basic/_stcore/stream/?", StreamlitWebSocketProxy),
            (r"/basic(?:/.*)?", BasicProxyHandler),
            (r"/.*", AdvancedProxyHandler),
        ],
        debug=False,
    )


def _launch_children() -> list[subprocess.Popen[Any]]:
    occupied = []
    for port, label in (
        (UNIFIED_PORT, "Unified website"),
        (BASIC_PORT, "Streamlit Basic Mode"),
        (ADVANCED_PORT, "Advanced Mode API"),
    ):
        if _port_is_open("127.0.0.1", port):
            occupied.append(f"{label} port {port}")
    if occupied:
        formatted = ", ".join(occupied)
        raise RuntimeError(
            f"Cannot start unified PitchIQ because these ports are already in use: {formatted}. "
            "Stop older PitchIQ server windows with Ctrl+C, then try again."
        )

    children: list[subprocess.Popen[Any]] = []
    env_advanced = os.environ.copy()
    env_advanced["PITCHIQ_UI_HOST"] = "127.0.0.1"
    env_advanced["PITCHIQ_UI_PORT"] = str(ADVANCED_PORT)

    print("Starting the shared PitchIQ analysis API…", flush=True)
    api_process = subprocess.Popen(
        [sys.executable, "-m", "pitchiq.webapp"],
        cwd=str(PROJECT_ROOT),
        env=env_advanced,
    )
    children.append(api_process)
    try:
        _wait_for_health(
            api_process,
            f"http://127.0.0.1:{ADVANCED_PORT}/api/health",
            "Advanced Mode API",
        )

        print("Starting Streamlit Basic Mode…", flush=True)
        streamlit_command = [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(PROJECT_ROOT / "pitchiq" / "dashboard.py"),
            f"--server.port={BASIC_PORT}",
            "--server.address=127.0.0.1",
            f"--server.baseUrlPath={BASIC_PREFIX.lstrip('/')}",
            "--server.headless=true",
        ]
        streamlit_process = subprocess.Popen(
            streamlit_command,
            cwd=str(PROJECT_ROOT),
            env=os.environ.copy(),
        )
        children.append(streamlit_process)
        _wait_for_port(streamlit_process, BASIC_PORT, "Streamlit Basic Mode")
        return children
    except Exception:
        for child in reversed(children):
            _stop_process(child)
        raise


def main() -> None:
    """Launch one local URL, and shut down its child services together."""
    if not (PROJECT_ROOT / "webui" / "index.html").is_file():
        raise SystemExit(f"Missing Advanced Mode UI: {PROJECT_ROOT / 'webui' / 'index.html'}")
    if HOST not in {"127.0.0.1", "localhost", "::1"}:
        raise SystemExit("For safety, the unified PitchIQ UI only binds to loopback by default.")

    children: list[subprocess.Popen[Any]] = []
    http_server = None
    try:
        children = _launch_children()
        app = make_application()
        http_server = tornado.httpserver.HTTPServer(
            app,
            max_body_size=210 * 1024 * 1024,
            max_buffer_size=210 * 1024 * 1024,
        )
        http_server.listen(UNIFIED_PORT, address=HOST)
        print("\nPitchIQ Unified Mode is ready", flush=True)
        print(f"One website:  http://{HOST}:{UNIFIED_PORT}/", flush=True)
        print(f"Basic Mode:   http://{HOST}:{UNIFIED_PORT}/basic/  (Streamlit)", flush=True)
        print(f"Advanced Mode: http://{HOST}:{UNIFIED_PORT}/  (Figma-inspired UI + AI HUD)", flush=True)
        print("Both modes call the existing PitchIQ project and analysis logic.", flush=True)
        print("Press Ctrl+C here to stop all three services.\n", flush=True)
        tornado.ioloop.IOLoop.current().start()
    except KeyboardInterrupt:
        print("\nStopping PitchIQ Unified Mode…", flush=True)
    except Exception as exc:
        print(f"\nPitchIQ Unified Mode could not start: {exc}", file=sys.stderr, flush=True)
        raise SystemExit(1) from exc
    finally:
        if http_server is not None:
            http_server.stop()
        try:
            tornado.ioloop.IOLoop.current().stop()
        except Exception:
            pass
        for child in reversed(children):
            _stop_process(child)
        if children:
            print("PitchIQ child services stopped.", flush=True)


if __name__ == "__main__":
    main()
