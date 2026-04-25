#!/usr/bin/env python3
"""Simple HTTP server that serves a rotating image from a directory."""

import argparse
import os
import random
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

DEFAULT_PORT = 8124
EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


def get_images(image_dir):
    return sorted([
        f for f in os.listdir(image_dir)
        if os.path.splitext(f.lower())[1] in EXTENSIONS
    ])


def make_handler(image_dir):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlparse(self.path)

            if parsed.path not in ["/rotate", "/rotate.jpg"]:
                self.send_error(404)
                return

            params = parse_qs(parsed.query)
            try:
                interval = max(1, int(params.get("n", [15])[0]))
            except (ValueError, TypeError):
                interval = 15

            images = get_images(image_dir)
            if not images:
                self.send_error(404, "No images found")
                return

            bucket = int(time.time() // interval)
            random.seed(bucket)
            filename = random.choice(images)

            ext = os.path.splitext(filename.lower())[1]
            content_type = CONTENT_TYPES.get(ext, "application/octet-stream")

            path = os.path.join(image_dir, filename)
            with open(path, "rb") as f:
                data = f.read()

            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, format, *args):
            pass  # suppress per-request console noise

    return Handler


def main():
    parser = argparse.ArgumentParser(description="Serve a rotating image from a directory")
    parser.add_argument("image_dir", help="Directory containing images")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Port to listen on (default: {DEFAULT_PORT})")
    args = parser.parse_args()

    if not os.path.isdir(args.image_dir):
        parser.error(f"Directory not found: {args.image_dir}")

    server = HTTPServer(("0.0.0.0", args.port), make_handler(args.image_dir))
    print(f"Serving rotating images from {args.image_dir} on port {args.port}")
    print(f"URL: http://<host>:{args.port}/rotate?n=<seconds>")
    server.serve_forever()


if __name__ == "__main__":
    main()
```
