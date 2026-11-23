"""A tiny library and a download server for it, so fetch and check can be tested without the network.

The library has the same shape as a real one: LastbookData/ with library-data/, derived/, pack.json and a
pack-manifest.tsv listing every file's size and SHA-256.
"""
import hashlib
import http.server
import json
import os
import threading
import zipfile
from pathlib import Path

FILES = {
    'library-data/catalog.json': b'{"records": []}\n',
    'library-data/documents/guide.pdf': os.urandom(200_000),
    'library-data/videos/first-aid/How to: stop bleeding [abc123].mp4': os.urandom(300_000),
    'derived/geo/places.sqlite': os.urandom(50_000),
}


def make_library(parent: Path, files=None) -> Path:
    """<parent>/LastbookData with pack.json and pack-manifest.tsv, as a real library has."""
    files = FILES if files is None else files
    lib = parent / 'LastbookData'
    rows = ['path\tbytes\tsha256\thow\tchanges']
    for rel, data in sorted(files.items()):
        p = lib / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        rows.append(f'{rel}\t{len(data)}\t{hashlib.sha256(data).hexdigest()}\tclone\t')
    (lib / 'pack-manifest.tsv').write_text('\n'.join(rows) + '\n', encoding='utf-8')
    (lib / 'pack.json').write_text(json.dumps({'name': 'small', 'counts': {}}), encoding='utf-8')
    return lib


def zip_library(lib: Path, zip_path: Path, extra=()) -> Path:
    """Zip a library as Lastbook publishes it: every member under LastbookData/. extra: (name, bytes) added as is."""
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in sorted(lib.rglob('*')):
            z.write(p, 'LastbookData/' + p.relative_to(lib).as_posix())
        for name, data in extra:
            if isinstance(data, zipfile.ZipInfo):
                z.writestr(data, b'')
            else:
                z.writestr(name, data)
    return zip_path


def installed_bytes(lib: Path) -> int:
    return sum(p.stat().st_size for p in lib.rglob('*') if p.is_file())


class Server:
    """Serves files from memory with HTTP Range, on a free loopback port.

    drop_after: for the first `drops` responses, send only this many body bytes and then close the connection.
    ignore_range: answer every request with the whole file (200), as some servers do.
    """

    def __init__(self, files: dict, drop_after=None, drops=1, ignore_range=False):
        self.files, self.drop_after, self.drops, self.ignore_range = files, drop_after, drops, ignore_range
        self.requests = []
        outer = self

        class Handler(http.server.BaseHTTPRequestHandler):
            protocol_version = 'HTTP/1.1'

            def log_message(self, *a):
                pass

            def do_GET(self):
                name = self.path.lstrip('/')
                rng = self.headers.get('Range')
                outer.requests.append((name, rng))
                data = outer.files.get(name)
                if data is None:
                    self.send_error(404)
                    return
                start, status = 0, 200
                if rng and not outer.ignore_range:
                    start = int(rng.split('=', 1)[1].split('-', 1)[0])
                    if start >= len(data):
                        self.send_response(416)
                        self.send_header('Content-Range', f'bytes */{len(data)}')
                        self.send_header('Content-Length', '0')
                        self.end_headers()
                        return
                    status = 206
                body = data[start:]
                self.send_response(status)
                self.send_header('Content-Length', str(len(body)))
                if status == 206:
                    self.send_header('Content-Range', f'bytes {start}-{len(data) - 1}/{len(data)}')
                self.end_headers()
                if outer.drop_after is not None and outer.drops > 0 and name.endswith('.zip'):
                    outer.drops -= 1
                    self.wfile.write(body[:outer.drop_after])
                    self.wfile.flush()
                    self.close_connection = True
                    self.connection.shutdown(2)
                    return
                self.wfile.write(body)

        self.httpd = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.url = f'http://127.0.0.1:{self.httpd.server_address[1]}'

    def __enter__(self):
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *exc):
        self.httpd.shutdown()
        self.httpd.server_close()

    def zip_requests(self):
        return [r for r in self.requests if r[0].endswith('.zip')]


def manifest(base_url, zip_name, zip_bytes: bytes, installed, sha=None, pack_id='small'):
    return {
        'version': 1,
        'packs': [{
            'id': pack_id, 'title': pack_id.title(), 'installed_bytes': installed, 'available': True,
            'files': [{'name': zip_name, 'url': f'{base_url}/{zip_name}', 'size': len(zip_bytes),
                       'sha256': sha or hashlib.sha256(zip_bytes).hexdigest(), 'kind': 'zip'}],
        }, {'id': 'medium', 'title': 'Medium', 'available': True, 'files': []}],
    }
