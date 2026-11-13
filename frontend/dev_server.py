"""Serve the frontend at http://127.0.0.1:5500 without browser caching.

`python3 -m http.server` lets the browser keep old copies of index.html,
styles.css, and app.js, so changes don't show up until a hard refresh. This
server tells the browser to always fetch the current files.

Run from the frontend folder:  python3 dev_server.py
"""

import http.server
import socketserver

PORT = 5500


class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True

    with socketserver.TCPServer(("127.0.0.1", PORT), NoCacheHandler) as server:
        print(f"Serving the frontend at http://127.0.0.1:{PORT} (no caching). Ctrl+C to stop.")
        server.serve_forever()
