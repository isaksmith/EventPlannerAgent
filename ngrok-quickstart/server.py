#!/usr/bin/env python3
"""Minimal HTTP server for ngrok CLI quickstart (port 8080)."""
from http.server import BaseHTTPRequestHandler, HTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(
            b"""<!DOCTYPE html>
<html>
<head><title>OrchestrateAI ngrok Quickstart</title></head>
<body><h1>Hello from Python HTTP Server!</h1></body>
</html>"""
        )

    def log_message(self, format: str, *args: object) -> None:
        print(f"[server] {args[0]} {args[1]} {args[2]}")


if __name__ == "__main__":
    port = 8080
    print(f"Serving at http://localhost:{port}")
    HTTPServer(("", port), Handler).serve_forever()
