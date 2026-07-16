import http.server
import socketserver
import os

PORT = 8000
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class NoCacheHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


if __name__ == "__main__":
    with ReusableTCPServer(("127.0.0.1", PORT), NoCacheHTTPRequestHandler) as httpd:
        print(f"Serving {ROOT} at http://localhost:{PORT} (no-cache)")
        httpd.serve_forever()
