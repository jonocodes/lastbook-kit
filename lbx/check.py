"""Is a library complete and unmodified? Checked against its own pack-manifest.tsv.

pack-manifest.tsv lists every file the pack shipped (path, bytes, sha256, how, changes), except itself.
Files the server writes while it runs are expected and ignored. Any other file not in the list is
reported, but isn't an error. Standard library only.
"""
import concurrent.futures
import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from lbx.errors import Problem

MANIFEST = 'pack-manifest.tsv'
# Written by upstream's server.py while it runs: page images, map tiles, the semantic index, the LAN key.
RUNTIME = ('derived/cache/', 'derived/geo/tilecache/', 'derived/index/', 'derived/lan-key')
CHUNK = 8 << 20


@dataclass(frozen=True)
class Entry:
    path: str
    bytes: int
    sha256: str
    how: str


@dataclass
class Result:
    library: Path
    entries: int = 0
    total_bytes: int = 0
    quick: bool = False
    missing: list = field(default_factory=list)
    wrong_size: list = field(default_factory=list)      # (path, expected, found)
    wrong_hash: list = field(default_factory=list)
    extra: list = field(default_factory=list)

    @property
    def ok(self):
        return not (self.missing or self.wrong_size or self.wrong_hash)


def read_manifest(lib: Path) -> list:
    path = lib / MANIFEST
    if not path.is_file():
        raise Problem(f'{lib} has no {MANIFEST}, so there is nothing to check it against.')
    entries = []
    with open(path, encoding='utf-8', newline='') as f:
        header = f.readline().rstrip('\r\n').split('\t')
        if header[:3] != ['path', 'bytes', 'sha256']:
            raise Problem(f'{path} does not start with the columns path, bytes, sha256.')
        for n, line in enumerate(f, start=2):
            line = line.rstrip('\r\n')
            if not line:
                continue
            cols = line.split('\t')
            try:
                rel, size, sha = cols[0], int(cols[1]), cols[2].lower()
            except (IndexError, ValueError):
                raise Problem(f'{path}, line {n}, is not path, bytes, sha256.')
            p = PurePosixPath(rel)
            if not rel or '\\' in rel or p.is_absolute() or '..' in p.parts or len(sha) != 64:
                raise Problem(f'{path}, line {n}, names a file oddly: {rel[:80]!r}.')
            entries.append(Entry(rel, size, sha, cols[3] if len(cols) > 3 else ''))
    return entries


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while chunk := f.read(CHUNK):
            h.update(chunk)
    return h.hexdigest()


def check(lib, quick=False, workers=None, progress=None) -> Result:
    """Check every file in the library's pack-manifest.tsv. quick: sizes only. progress(done_bytes, total_bytes)."""
    lib = Path(lib).expanduser().resolve()
    entries = read_manifest(lib)
    r = Result(lib, len(entries), sum(e.bytes for e in entries), quick)
    to_hash = []
    for e in entries:
        p = lib / e.path
        try:
            st = p.stat()
        except FileNotFoundError:
            r.missing.append(e.path)
            continue
        if not p.is_file():
            r.missing.append(e.path)
        elif st.st_size != e.bytes:
            r.wrong_size.append((e.path, e.bytes, st.st_size))
        elif not quick:
            to_hash.append(e)
    if to_hash:
        done = 0
        with concurrent.futures.ThreadPoolExecutor(workers or min(8, os.cpu_count() or 1)) as pool:
            jobs = {pool.submit(sha256, lib / e.path): e for e in to_hash}
            for job in concurrent.futures.as_completed(jobs):
                e = jobs[job]
                if job.result() != e.sha256:
                    r.wrong_hash.append(e.path)
                done += e.bytes
                if progress:
                    progress(done, sum(x.bytes for x in to_hash))
    known = {e.path for e in entries} | {MANIFEST}
    for root, dirs, files in os.walk(lib):
        for name in files:
            rel = Path(root, name).relative_to(lib).as_posix()
            if rel not in known and not rel.startswith(RUNTIME):
                r.extra.append(rel)
    for lst in (r.missing, r.wrong_hash, r.extra):
        lst.sort()
    r.wrong_size.sort()
    return r


def report(r: Result, say=print, limit=20):
    def some(title, items, fmt=str):
        if not items:
            return
        say(f'{title} ({len(items)}):')
        for x in items[:limit] if limit else items:
            say('  ' + fmt(x))
        if limit and len(items) > limit:
            say(f'  … and {len(items) - limit} more')

    some('Missing', r.missing)
    some('Wrong size', r.wrong_size, lambda x: f'{x[0]}  (expected {x[1]:,} bytes, found {x[2]:,})')
    some('Changed (SHA-256 differs)', r.wrong_hash)
    some('Not in the pack (not an error)', r.extra)
    what = 'sizes' if r.quick else 'sizes and SHA-256'
    if r.ok:
        say(f'OK: all {r.entries:,} files ({r.total_bytes / 1e9:.2f} GB) match {MANIFEST} ({what}).')
    else:
        bad = len(r.missing) + len(r.wrong_size) + len(r.wrong_hash)
        say(f'NOT OK: {bad:,} of {r.entries:,} files are missing or differ from {MANIFEST} ({what}).')
