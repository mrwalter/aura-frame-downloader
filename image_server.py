#!/usr/bin/env python3
"""HTTP server that serves rotating images and videos from a directory."""

import argparse
import json
import os
import random
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, quote, unquote, urlparse

DEFAULT_PORT = 8124

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm"}
ALL_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS

CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".mp4": "video/mp4",
    ".m4v": "video/mp4",
    ".mov": "video/quicktime",
    ".webm": "video/webm",
}


def media_type_for(filename):
    ext = os.path.splitext(filename.lower())[1]
    if ext in VIDEO_EXTENSIONS:
        return "video"
    if ext in IMAGE_EXTENSIONS:
        return "image"
    return None


def list_media(image_dir, kinds):
    files = sorted(os.listdir(image_dir))
    out = []
    for f in files:
        ext = os.path.splitext(f.lower())[1]
        if "image" in kinds and ext in IMAGE_EXTENSIONS:
            out.append(f)
        elif "video" in kinds and ext in VIDEO_EXTENSIONS:
            out.append(f)
    return out


def pick_for_bucket(files, interval):
    bucket = int(time.time() // interval)
    random.seed(bucket)
    return random.choice(files)


PAGE_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Aura rotating media</title>
<style>
  html, body { margin: 0; padding: 0; height: 100%; background: black; overflow: hidden; }
  #media { width: 100vw; height: 100vh; display: flex; align-items: center; justify-content: center; }
  #media > * { max-width: 100%; max-height: 100%; width: auto; height: auto; object-fit: contain; }
</style>
</head>
<body>
<div id="media"></div>
<script>
const INTERVAL = __INTERVAL__;
const AUDIO = __AUDIO__;

function renderItem(item) {
  const container = document.getElementById('media');
  container.innerHTML = '';
  if (item.type === 'video') {
    const v = document.createElement('video');
    v.src = item.url;
    v.autoplay = true;
    v.loop = true;
    v.playsInline = true;
    v.muted = !AUDIO;
    container.appendChild(v);
    v.play().catch(() => {});
  } else {
    const img = document.createElement('img');
    img.src = item.url;
    container.appendChild(img);
  }
}

async function tick() {
  try {
    const resp = await fetch('/current?n=' + INTERVAL, { cache: 'no-store' });
    const item = await resp.json();
    renderItem(item);
  } catch (e) {
    // ignore transient errors; will try again at next bucket
  }
  // schedule next swap at the next bucket boundary
  const now = Date.now() / 1000;
  const nextBoundary = (Math.floor(now / INTERVAL) + 1) * INTERVAL;
  const wait = Math.max(100, (nextBoundary - now) * 1000 + 50);
  setTimeout(tick, wait);
}

tick();
</script>
</body>
</html>
"""


def make_handler(image_dir):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)

            try:
                interval = max(1, int(params.get("n", [15])[0]))
            except (ValueError, TypeError):
                interval = 15

            audio = params.get("audio", ["0"])[0].lower() in ("1", "true", "yes", "on")

            path = parsed.path

            if path in ("/rotate", "/rotate.jpg"):
                self._serve_image(interval)
            elif path == "/page":
                self._serve_page(interval, audio)
            elif path == "/current":
                self._serve_current(interval)
            elif path.startswith("/file/"):
                self._serve_file(unquote(path[len("/file/"):]))
            else:
                self.send_error(404)

        def _serve_image(self, interval):
            images = list_media(image_dir, kinds={"image"})
            if not images:
                self.send_error(404, "No images found")
                return
            filename = pick_for_bucket(images, interval)
            self._send_file(os.path.join(image_dir, filename), filename)

        def _serve_page(self, interval, audio):
            html = (PAGE_HTML
                    .replace("__INTERVAL__", str(interval))
                    .replace("__AUDIO__", "true" if audio else "false"))
            data = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.end_headers()
            self.wfile.write(data)

        def _serve_current(self, interval):
            media = list_media(image_dir, kinds={"image", "video"})
            if not media:
                self.send_error(404, "No media found")
                return
            filename = pick_for_bucket(media, interval)
            payload = {
                "type": media_type_for(filename),
                "url": "/file/" + quote(filename),
            }
            data = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.end_headers()
            self.wfile.write(data)

        def _serve_file(self, name):
            # prevent path traversal: only serve files directly inside image_dir
            if not name or "/" in name or "\\" in name or name.startswith("."):
                self.send_error(400, "Invalid filename")
                return
            full = os.path.join(image_dir, name)
            if not os.path.isfile(full):
                self.send_error(404)
                return
            self._send_file(full, name)

        def _send_file(self, full_path, filename):
            ext = os.path.splitext(filename.lower())[1]
            content_type = CONTENT_TYPES.get(ext, "application/octet-stream")
            try:
                size = os.path.getsize(full_path)
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(size))
                self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()
                with open(full_path, "rb") as f:
                    while True:
                        chunk = f.read(64 * 1024)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def log_message(self, format, *args):
            pass

    return Handler


def main():
    parser = argparse.ArgumentParser(description="Serve rotating images and videos from a directory")
    parser.add_argument("image_dir", help="Directory containing images and/or videos")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Port to listen on (default: {DEFAULT_PORT})")
    args = parser.parse_args()

    if not os.path.isdir(args.image_dir):
        parser.error(f"Directory not found: {args.image_dir}")

    server = HTTPServer(("0.0.0.0", args.port), make_handler(args.image_dir))
    print(f"Serving rotating media from {args.image_dir} on port {args.port}")
    print(f"  images only:    http://<host>:{args.port}/rotate?n=<seconds>")
    print(f"  iframe page:    http://<host>:{args.port}/page?n=<seconds>[&audio=1]")
    server.serve_forever()


if __name__ == "__main__":
    main()
