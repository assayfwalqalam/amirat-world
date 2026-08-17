"""Receives a canvas frame from the running page and writes it to disk.

The browser pane cannot be screenshotted while it is hidden, and headless
SwiftShader takes tens of minutes on a scene this size. The page can, however,
read its own canvas and POST it here, which takes about a second.

    python tools/catch_shot.py            # listens on 8899 until stopped

From the page:
    fetch('http://localhost:8899/shots/name.png', {method:'POST', body: dataURL})
"""
import base64
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Catch(BaseHTTPRequestHandler):
    timeout = 20   # a dead connection may not freeze the server
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(n).decode("utf-8", "replace")
        m = re.match(r"data:image/(\w+);base64,(.*)$", body, re.S)
        if not m:
            self.send_response(400)
            self._cors()
            self.end_headers()
            return
        # the path is taken from the request, but kept inside the project
        rel = self.path.lstrip("/") or "shots/posted.png"
        rel = rel.replace("\\", "/")
        dest = os.path.normpath(os.path.join(ROOT, rel))
        if not dest.startswith(ROOT):
            self.send_response(403)
            self._cors()
            self.end_headers()
            return
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as f:
            f.write(base64.b64decode(m.group(2)))
        print("wrote %s (%d bytes)" % (dest, os.path.getsize(dest)), flush=True)
        self.send_response(200)
        self._cors()
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print("catching frames on http://localhost:8899", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 8899), Catch).serve_forever()
