"""Tiny mock of GET /api/v3/events/{id}/registrants for local tap testing.

Serves two cursor-paginated pages per event and asserts the Bearer header.
Run: python scripts/mock_server.py  (listens on 127.0.0.1:8765)
"""

import json
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

PAGE1 = {
    "items": [
        {
            "first_name": "Ada",
            "last_name": "Lovelace",
            "email": "ada@example.com",
            "registered_at": "2026-08-30T12:00:00Z",
            "approved": True,
            "join_url": "https://riverside.fm/audience/abc",
            "participated": True,
            "attendance_rate": None,
            "duration": "05:46",
            "referrer": "https://pulumi.com",
            "utm": {
                "source": "newsletter",
                "medium": "email",
                "campaign": "fy27q1",
                "term": None,
                "content": None,
            },
            "custom_fields": {"company": "Analytical Engines"},
        }
    ],
    "page": {"limit": 1, "next_cursor": "cur_2", "total_items": 2},
}

PAGE2 = {
    "items": [
        {
            "first_name": "Grace",
            "last_name": None,
            "email": "grace@example.com",
            "registered_at": "2026-08-31T09:30:00Z",
            "approved": True,
            "join_url": None,
            "participated": False,
            "attendance_rate": None,
            "duration": "00:00",
            "referrer": None,
            "utm": {
                "source": None,
                "medium": None,
                "campaign": None,
                "term": None,
                "content": None,
            },
            "custom_fields": None,
        }
    ],
    "page": {"limit": 1, "next_cursor": None, "total_items": 2},
}

ROUTE = re.compile(r"^/api/v3/events/(?P<event_id>[0-9a-f]{24})/registrants$")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        match = ROUTE.match(url.path)
        auth = self.headers.get("Authorization", "")
        if not match or not auth.startswith("Bearer "):
            self.send_response(401 if match else 404)
            self.end_headers()
            return
        cursor = parse_qs(url.query).get("cursor", [None])[0]
        body = dict(PAGE2 if cursor == "cur_2" else PAGE1)
        body["event_id"] = match["event_id"]
        payload = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):  # noqa: A002 - silence per-request noise
        pass


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 8765), Handler).serve_forever()
