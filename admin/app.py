"""Minimal local GUI for the Data Update Center.

Run with: python admin/app.py --root /path/to/repository --port 8765
"""

from __future__ import annotations

import argparse
import html
import json
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from update_center import DataUpdateCenter


def page(root: Path) -> str:
    center = DataUpdateCenter(root)
    rows = center.list_versions()
    body = "".join(
        f"<tr><td>{html.escape(str(row.get('dataset_id')))}</td>"
        f"<td>{html.escape(str(row.get('version_id')))}</td>"
        f"<td>{html.escape(str(row.get('status')))}</td>"
        f"<td>{html.escape(str(row.get('validation_status')))}</td></tr>"
        for row in rows
    )
    return f"""<!doctype html>
<html lang="ja"><meta charset="utf-8"><title>Data Update Center</title>
<style>body{{font-family:system-ui;margin:2rem;max-width:70rem}}label{{display:block;margin:.6rem 0}}
table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #ccc;padding:.4rem;text-align:left}}
button{{padding:.5rem 1rem}}</style>
<h1>Data Update Center</h1>
<p>候補版を検証し、承認した版だけをactiveへ切り替えます。直接上書きは行いません。</p>
<form method="post" action="/upload" enctype="multipart/form-data">
<label>dataset_id <input name="dataset_id" required></label>
<label>reference_date <input name="reference_date" required placeholder="2026-08-22"></label>
<label>license <input name="license" required></label>
<label>file <input type="file" name="file" required></label>
<button type="submit">検証して候補版へ登録</button>
</form>
<h2>Versions</h2><table><tr><th>dataset</th><th>version</th><th>status</th><th>validation</th></tr>{body}</table>
"""


class Handler(BaseHTTPRequestHandler):
    root: Path

    def do_GET(self) -> None:
        if urlparse(self.path).path == "/":
            payload = page(self.root).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/upload":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        content_type = self.headers.get("Content-Type", "")
        if length <= 0 or "multipart/form-data" not in content_type:
            self.send_error(400, "multipart upload required")
            return
        body = self.rfile.read(length)
        boundary = content_type.split("boundary=", 1)[-1].encode()
        parts = body.split(b"--" + boundary)
        fields: dict[str, bytes] = {}
        for part in parts:
            if b"\r\n\r\n" not in part:
                continue
            header, value = part.split(b"\r\n\r\n", 1)
            value = value.rsplit(b"\r\n", 1)[0]
            marker = b'name="'
            if marker not in header:
                continue
            name = header.split(marker, 1)[1].split(b'"', 1)[0].decode()
            fields[name] = value
        if b"file" not in fields:
            self.send_error(400, "file is required")
            return
        filename = "upload.bin"
        for part in parts:
            if b'name="file"' in part and b'filename="' in part:
                filename = part.split(b'filename="', 1)[1].split(b'"', 1)[0].decode("utf-8", "replace")
                break
        with tempfile.NamedTemporaryFile(dir=self.root / "data" / "staging", delete=False, suffix=Path(filename).suffix) as handle:
            handle.write(fields[b"file"])
            temporary = Path(handle.name)
        try:
            center = DataUpdateCenter(self.root)
            result = center.stage(
                fields.get("dataset_id", b"unknown").decode(),
                temporary,
                fields.get("reference_date", b"").decode(),
                fields.get("license", b"").decode(),
            )
            payload = json.dumps(result, ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except Exception as exc:
            self.send_error(400, str(exc))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    Handler.root = Path(args.root).resolve()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Data Update Center: http://{args.host}:{args.port}/")
    server.serve_forever()


if __name__ == "__main__":
    main()
