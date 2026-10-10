"""
HTTP server of the mobile web portal.
It exposes a small JSON API (plus a Server-Sent Events stream) and serves the React build from webapp/dist.
Only the standard library is used, so no extra web framework is required on the photobooth machine.
"""
import hmac
import json
import mimetypes
import os
import ssl
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, unquote

from photobooth.web.session import WebSession, PHASE_APPROVAL, PHASE_COPIES

WEBAPP_DIST_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'webapp', 'dist'))
SSE_KEEPALIVE_SEC = 15
MAX_BODY_BYTES = 4096
SOCKET_TIMEOUT_SEC = 30

# A phone closing the tab, locking the screen or switching network drops the connection abruptly:
# over TLS this surfaces as SSLEOFError (no close_notify), over plain HTTP as BrokenPipe/ConnectionReset.
CLIENT_DISCONNECT_ERRORS = (ConnectionError, TimeoutError, ssl.SSLError)


class PortalServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, session: WebSession, token: str, ssl_context: ssl.SSLContext = None):
        super().__init__(address, PortalRequestHandler)
        self.session = session
        self.token = token
        self.ssl_context = ssl_context

    def finish_request(self, request, client_address):
        # the TLS handshake runs in the per-connection thread, so a slow client never blocks accept()
        if self.ssl_context is None:
            super().finish_request(request, client_address)
            return

        request.settimeout(SOCKET_TIMEOUT_SEC)
        try:
            tls_request = self.ssl_context.wrap_socket(request, server_side=True)
        except (ssl.SSLError, OSError):
            # e.g. plain HTTP request on the HTTPS port, or certificate rejected by the browser
            return
        try:
            super().finish_request(tls_request, client_address)
        except CLIENT_DISCONNECT_ERRORS:
            pass
        finally:
            # wrap_socket detached the original socket, so socketserver can no longer close it
            tls_request.close()


    def handle_error(self, request, client_address):
        # client disconnections are routine, only unexpected errors deserve a traceback on the terminal
        if isinstance(sys.exc_info()[1], CLIENT_DISCONNECT_ERRORS):
            return
        super().handle_error(request, client_address)


class PortalRequestHandler(BaseHTTPRequestHandler):
    server: PortalServer

    # ---------- routing ----------

    def do_GET(self):
        url = urlparse(self.path)
        path = url.path

        if not path.startswith('/api/'):
            self._serve_static(path)
            return
        if not self._is_authorized(url):
            self._send_json(401, {"error": "unauthorized"})
            return

        session = self.server.session
        if path == '/api/state':
            self._send_json(200, session.snapshot())
        elif path == '/api/events':
            self._stream_events()
        elif path == '/api/preview':
            data = session.get_preview_jpeg()
            if data is None:
                self._send_json(404, {"error": "no preview"})
            else:
                self._send_bytes(200, data, "image/jpeg", cache="no-store")
        elif path == '/api/gallery':
            self._send_json(200, {"photos": session.list_gallery()})
        elif path.startswith('/api/gallery/'):
            name = unquote(path[len('/api/gallery/'):])
            thumbnail = parse_qs(url.query).get('thumb', ['0'])[0] == '1'
            result = session.get_gallery_image(name, thumbnail)
            if result is None:
                self._send_json(404, {"error": "not found"})
            else:
                self._send_bytes(200, result[0], result[1], cache="private, max-age=3600")
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self):
        url = urlparse(self.path)
        if not self._is_authorized(url):
            self._send_json(401, {"error": "unauthorized"})
            return

        body = self._read_json()
        if body is None:
            self._send_json(400, {"error": "invalid body"})
            return

        session = self.server.session
        if url.path == '/api/approval':
            accepted = body.get('accepted')
            if not isinstance(accepted, bool):
                self._send_json(400, {"error": "'accepted' must be a boolean"})
                return
            ok = session.submit(PHASE_APPROVAL, accepted)
        elif url.path == '/api/copies':
            copies = body.get('copies')
            limits = session.snapshot()['copies']
            if not isinstance(copies, int) or isinstance(copies, bool) or not limits['min'] <= copies <= limits['max']:
                self._send_json(400, {"error": f"'copies' must be between {limits['min']} and {limits['max']}"})
                return
            ok = session.submit(PHASE_COPIES, copies)
        elif url.path == '/api/reprint':
            self._handle_reprint(body)
            return
        elif url.path == '/api/back':
            # undo the photo approval: from the copies selection back to the framed preview
            ok = session.submit(PHASE_COPIES, None)
        else:
            self._send_json(404, {"error": "not found"})
            return

        if ok:
            self._send_json(200, {"ok": True})
        else:
            self._send_json(409, {"error": "the engine is not waiting for this answer"})

    # ---------- handlers ----------

    def _handle_reprint(self, body: dict):
        session = self.server.session
        name, copies = body.get('name'), body.get('copies')
        limits = session.snapshot()['copies']
        if not isinstance(copies, int) or isinstance(copies, bool) or not limits['min'] <= copies <= limits['max']:
            self._send_json(400, {"error": f"'copies' must be between {limits['min']} and {limits['max']}"})
            return
        if not any(p['name'] == name for p in session.list_gallery()):
            self._send_json(404, {"error": "photo not found"})
            return
        try:
            pending = session.reprint(name, copies)
        except FileNotFoundError as e:
            self._send_json(404, {"error": f"missing file: {e}"})
            return
        except Exception as e:
            print(f"Error reprinting {name}: {e}")
            self._send_json(500, {"error": "print failed"})
            return
        self._send_json(200, {"ok": True, "pending": pending})

    def _stream_events(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        session = self.server.session
        state = session.snapshot()
        try:
            self._write_event(state)
            while True:
                new_state = session.wait_for_change(state['version'], SSE_KEEPALIVE_SEC)
                if new_state['version'] == state['version']:
                    self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
                else:
                    state = new_state
                    self._write_event(state)
        except CLIENT_DISCONNECT_ERRORS:
            pass

    def _write_event(self, state: dict):
        self.wfile.write(f"data: {json.dumps(state)}\n\n".encode())
        self.wfile.flush()

    def _serve_static(self, path: str):
        if not os.path.isdir(WEBAPP_DIST_PATH):
            message = ("Web portal not built. Run 'npm install && npm run build' in the webapp folder, "
                       "then restart the engine.")
            self._send_bytes(503, message.encode(), "text/plain; charset=utf-8")
            return

        file_path = os.path.abspath(os.path.join(WEBAPP_DIST_PATH, unquote(path).lstrip('/')))
        if not file_path.startswith(WEBAPP_DIST_PATH + os.sep) or not os.path.isfile(file_path):
            # single page app: unknown routes fall back to index.html
            file_path = os.path.join(WEBAPP_DIST_PATH, 'index.html')

        content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
        # hashed bundles can be cached forever, index.html must always be revalidated
        cache = "public, max-age=31536000, immutable" if '/assets/' in file_path else "no-cache"
        with open(file_path, 'rb') as f:
            self._send_bytes(200, f.read(), content_type, cache=cache)

    # ---------- helpers ----------

    def _is_authorized(self, url) -> bool:
        token = self.headers.get('X-Photobooth-Token') or parse_qs(url.query).get('t', [''])[0]
        return hmac.compare_digest(token.encode(), self.server.token.encode())

    def _read_json(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            if length <= 0 or length > MAX_BODY_BYTES:
                return None
            body = json.loads(self.rfile.read(length))
            return body if isinstance(body, dict) else None
        except (ValueError, json.JSONDecodeError):
            return None

    def _send_json(self, status: int, payload: dict):
        self._send_bytes(status, json.dumps(payload).encode(), "application/json", cache="no-store")

    def _send_bytes(self, status: int, data: bytes, content_type: str, cache: str = None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        if cache:
            self.send_header("Cache-Control", cache)
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        # keep the terminal clean: the engine prints its own messages there
        pass


def start_portal_server(session: WebSession, host: str, port: int, token: str, cert_files: tuple = None) -> PortalServer:
    """
    Starts the portal HTTP server in a background daemon thread.
    :param cert_files: optional (certificate path, key path) to serve the portal over HTTPS
    :return: the running server instance
    """
    ssl_context = None
    if cert_files is not None:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(*cert_files)
    server = PortalServer((host, port), session, token, ssl_context)
    threading.Thread(target=server.serve_forever, daemon=True, name="web-portal").start()
    return server
