"""A small library application with two seeded performance defects.

- GET /search serializes every request behind one lock, as if the database
  connection pool had a single connection: fast alone, slow under load.
- POST /reserve fails one request in 40 (2.5% of errors).
The other endpoints are fast. Run it only on your own computer.
"""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

BOOKS = [{"id": i, "title": f"Book {i}"} for i in range(1, 51)]
POOL = threading.Lock()          # seeded defect 1: a pool of one connection
COUNTER = {"reserve": 0}
COUNTER_LOCK = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # keep the console quiet during load tests
        pass

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            return self._send(200, {"status": "ok"})
        if path == "/books":
            time.sleep(0.005)
            return self._send(200, BOOKS)
        if path == "/search":
            with POOL:
                time.sleep(0.02)
            return self._send(200, BOOKS[:5])
        self._send(404, {"error": "not found"})

    def do_POST(self):
        if urlparse(self.path).path != "/reserve":
            return self._send(404, {"error": "not found"})
        length = int(self.headers.get("Content-Length") or 0)
        self.rfile.read(length)
        time.sleep(0.01)
        with COUNTER_LOCK:
            COUNTER["reserve"] += 1
            n = COUNTER["reserve"]
        if n % 40 == 0:                 # seeded defect 2
            return self._send(500, {"error": "reservation failed"})
        self._send(201, {"status": "reserved"})


class Server(ThreadingHTTPServer):
    request_queue_size = 256   # avoid measuring the listen backlog instead of the application


def serve(port=8099, host="127.0.0.1"):
    server = Server((host, port), Handler)
    server.daemon_threads = True
    return server


if __name__ == "__main__":
    s = serve()
    print("Demo library application on http://127.0.0.1:8099 (Ctrl+C to stop)")
    s.serve_forever()
