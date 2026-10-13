import json
import os
import socket
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

VERSION = os.environ.get("APP_VERSION", "1.0.0")
STUDENT = os.environ.get("STUDENT_ID", "02230135")
FEATURE_PINNED = os.environ.get("FEATURE_PINNED", "false") == "true"
BROKEN = VERSION == "1.2.0-broken"
STARTED = time.monotonic()

BASE_NOTICES = [
    {"id": 1, "title": "Library hours", "message": "Library closes at 8 PM."},
    {"id": 2, "title": "Exam registration", "message": "Register by Friday."},
    {"id": 3, "title": "Campus sports", "message": "Sports day is on Saturday."},
]


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, body):
        encoded = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self):
        path = urlsplit(self.path).path
        uptime = round(time.monotonic() - STARTED, 3)

        if path == "/version":
            self.send_json(200, {
                "version": VERSION,
                "student": STUDENT,
                "pod": socket.gethostname(),
                "uptimeSeconds": uptime,
            })

        elif path == "/healthz":
            healthy = uptime >= 5 and not BROKEN
            self.send_json(200 if healthy else 503, {
                "healthy": healthy,
                "student": STUDENT,
                "version": VERSION,
                "uptimeSeconds": uptime,
            })

        elif path == "/notices":
            notices = [dict(notice) for notice in BASE_NOTICES]
            pinned_first = False

            if VERSION != "1.0.0":
                categories = ["Library", "Academic", "Events"]
                for notice, category in zip(notices, categories):
                    notice["category"] = category
                    notice["pinned"] = notice["id"] == 2

                if FEATURE_PINNED:
                    notices.sort(key=lambda notice: not notice["pinned"])
                    pinned_first = True

            self.send_json(200, {
                "student": STUDENT,
                "notices": notices,
                "pinnedFirst": pinned_first,
            })

        else:
            self.send_json(404, {"error": "Not found", "student": STUDENT})


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", 8080), Handler)
    print(f"Student {STUDENT}: version {VERSION} listening on port 8080",
          flush=True)
    server.serve_forever()