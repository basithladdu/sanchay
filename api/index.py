from http.server import BaseHTTPRequestHandler
from pathlib import Path

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        root = Path(__file__).parent.parent
        index_file = root / "public" / "index.html"
        if not index_file.exists():
            index_file = root / "index.html"
            
        if index_file.exists():
            content = index_file.read_bytes()
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"SANCHAY Live")
