"""Get a library: download its zip with resume, check it, unpack it beside the old one, switch with a rename.

  <dest>/Lastbook-Small-….zip.partial    a download in progress. Running again carries on from where it stopped
  <dest>/LastbookData.unpack/            the new library while it is unpacked. Also resumable
  <dest>/LastbookData                    the library, switched in with one rename
  <dest>/LastbookData.old-<time>         the library it replaced, if there was one. Delete it when the new one works

Standard library only.
"""
import hashlib
import http.client
import os
import shutil
import stat
import sys
import time
import urllib.error
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath

from lbx import manifest, paths
from lbx.errors import Problem

DATA_NAME = 'LastbookData'
CHUNK = 1 << 20
RETRIES = 8                     # failures in a row before giving up. Any progress resets the count
SLACK = 1.02                    # installed_bytes is measured; a zip's members may add a little
SPACE_MARGIN = 1 << 30


def say(*a):
    print(*a, flush=True)


# ---------------------------------------------------------------- progress ----

class Progress:
    """One line on stderr, rewritten in place on a terminal and printed now and then otherwise."""

    def __init__(self, label, total, out=sys.stderr):
        self.label, self.total, self.out = label, total, out
        self.tty = out.isatty()
        self.start = self.last = time.monotonic()
        self.first = None

    def __call__(self, done, force=False):
        now = time.monotonic()
        if self.first is None:
            self.first = (now, done)
        if not force and now - self.last < (1 if self.tty else 30):
            return
        self.last = now
        t0, d0 = self.first
        rate = (done - d0) / (now - t0) if now > t0 else 0
        pct = f'{100 * done / self.total:5.1f}%' if self.total else ''
        line = f'{self.label}  {gb(done)} / {gb(self.total)}  {pct}  {mb(rate)}/s'
        self.out.write(('\r' + line + '   ') if self.tty else line + '\n')
        self.out.flush()

    def done(self, done):
        self(done, force=True)
        if self.tty:
            self.out.write('\n')


def gb(n):
    return f'{n / 1e9:.2f} GB'


def mb(n):
    return f'{n / 1e6:.1f} MB'


# ---------------------------------------------------------------- download ----

def download(f: manifest.File, folder: Path, say=say) -> Path:
    """<folder>/<f.name>, downloaded or resumed. Size checked here; the SHA-256 by verify()."""
    final = folder / f.name
    if final.is_file() and final.stat().st_size == f.size:
        say(f'Already downloaded: {f.name}')
        return final
    part = folder / (f.name + '.partial')
    have = part.stat().st_size if part.is_file() else 0
    if have > f.size:
        part.unlink()
        have = 0
    if have:
        say(f'Resuming {f.name} at {gb(have)}')
    progress = Progress(f.name, f.size)
    failures = 0
    while have < f.size:
        before = have
        try:
            _fetch_from(f, part, have, progress)
        except urllib.error.HTTPError as e:
            if e.code in (404, 403, 410):
                raise Problem(f'the server refused {f.url} ({e.code} {e.reason}).')
            if e.code == 416:           # the server can't start where the partial file ends: start again
                part.unlink(missing_ok=True)
            err = f'{e.code} {e.reason}'
        except (urllib.error.URLError, http.client.HTTPException, OSError) as e:
            err = str(getattr(e, 'reason', e)) or type(e).__name__
        else:
            err = 'the connection closed early'
        have = part.stat().st_size if part.is_file() else 0     # what reached the disk, however the attempt ended
        if have >= f.size:
            break
        failures = 0 if have > before else failures + 1
        if failures > RETRIES:
            raise Problem(f'the download of {f.name} keeps failing ({err}). '
                          f'{gb(have)} is saved: run the same command again to carry on.')
        wait = min(60, 2 ** failures) if failures else 1
        say(f'\n{f.name}: {err}. Trying again in {wait} s.')
        time.sleep(wait)
    progress.done(have)
    if part.stat().st_size != f.size:
        raise Problem(f'{f.name} came out at {part.stat().st_size:,} bytes, not {f.size:,}. '
                      f'Delete {part} and run again.')
    os.replace(part, final)
    return final


def _fetch_from(f, part, have, progress):
    """One request from byte <have>. Returns the bytes now on disk."""
    headers = {'User-Agent': manifest.USER_AGENT}
    if have:
        headers['Range'] = f'bytes={have}-'
    req = urllib.request.Request(f.url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as r:
        if have and r.status == 200:            # the server ignored Range: start again
            have = 0
        elif have and r.status == 206:
            start = _range_start(r.headers.get('Content-Range'))
            if start != have:
                have = 0
                r.close()
                return _fetch_from(f, part, 0, progress)
        with open(part, 'r+b' if have else 'wb') as out:
            out.seek(have)
            out.truncate()
            while have < f.size:
                chunk = r.read(min(CHUNK, f.size - have))
                if not chunk:
                    break
                out.write(chunk)
                have += len(chunk)
                progress(have)
    return have


def _range_start(value):
    try:
        unit, rest = (value or '').split(' ', 1)
        return int(rest.split('-', 1)[0]) if unit == 'bytes' else None
    except ValueError:
        return None


def verify(path: Path, f: manifest.File, say=say):
    """Size and SHA-256 against the manifest. A file that fails is renamed to <name>.bad."""
    size = path.stat().st_size
    if size != f.size:
        raise Problem(f'{path.name} is {size:,} bytes, but the manifest says {f.size:,}.')
    say(f'Checking the SHA-256 of {path.name}')
    if sha256(path, Progress(f'checking {path.name}', size)) != f.sha256:
        bad = path.with_name(path.name + '.bad')
        os.replace(path, bad)
        raise Problem(f'{path.name} does not match its SHA-256 in the manifest. '
                      f'It was moved to {bad.name}. Delete it and run again.')


def sha256(path: Path, progress=None) -> str:
    h = hashlib.sha256()
    done = 0
    with open(path, 'rb') as fh:
        while chunk := fh.read(CHUNK * 8):
            h.update(chunk)
            done += len(chunk)
            if progress:
                progress(done)
    if progress:
        progress.done(done)
    return h.hexdigest()


# ---------------------------------------------------------------- unpack ----

def members(zip_path: Path, installed_bytes=0):
    """Every member of a pack zip, checked before anything is written (the same rules as upstream's setup).
    Returns [(info, relative parts under LastbookData)] and the total size."""
    try:
        z = zipfile.ZipFile(zip_path)
    except (OSError, zipfile.BadZipFile) as e:
        raise Problem(f'{zip_path.name} could not be opened as a zip ({type(e).__name__}).')
    out, total, seen = [], 0, set()
    with z:
        for info in z.infolist():
            name = info.filename
            if '\\' in name or '\x00' in name:
                raise Problem(f'{zip_path.name} holds a file with an unacceptable name: {name[:80]!r}.')
            p = PurePosixPath(name)
            parts = [x for x in p.parts if x not in ('', '.')]
            if (p.is_absolute() or (parts and ':' in parts[0]) or '..' in parts
                    or not parts or parts[0] != DATA_NAME):
                raise Problem(f'{zip_path.name} holds a file outside {DATA_NAME}/: {name[:80]!r}.')
            mode = (info.external_attr >> 16) & 0o170000
            if mode and mode not in (stat.S_IFREG, stat.S_IFDIR):
                raise Problem(f'{zip_path.name} holds a link or special file: {name[:80]!r}.')
            if info.flag_bits & 0x1:
                raise Problem(f'{zip_path.name} is encrypted.')
            if info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
                raise Problem(f'{zip_path.name} uses an unexpected compression: {name[:80]!r}.')
            key = name.rstrip('/').lower()
            if key in seen and not info.is_dir():
                raise Problem(f'{zip_path.name} holds the same file twice: {name[:80]!r}.')
            seen.add(key)
            total += info.file_size
            out.append((info, tuple(parts[1:])))
    if installed_bytes and total > installed_bytes * SLACK + (1 << 20):
        raise Problem(f'{zip_path.name} unpacks to {total:,} bytes, more than the {installed_bytes:,} it should.')
    return out, total


def unpack(zips, staging: Path, installed_bytes=0, say=say) -> Path:
    """Unpack pack zips into <staging>/LastbookData. Files already whole from an earlier run are kept."""
    checked = [(z, *members(z, installed_bytes)) for z in zips]
    root = (staging / DATA_NAME).resolve()
    root.mkdir(parents=True, exist_ok=True)
    total = sum(t for _, _, t in checked)
    progress = Progress('unpacking', total)
    done = 0
    for zip_path, items, _ in checked:
        with zipfile.ZipFile(zip_path) as z:
            for info, parts in items:
                dest = root.joinpath(*parts)
                if info.is_dir():
                    dest.mkdir(parents=True, exist_ok=True)
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                if dest.is_symlink():
                    raise Problem(f'a link appeared in {staging}.')
                if dest.is_file() and dest.stat().st_size == info.file_size:
                    done += info.file_size
                    continue
                part = dest.with_name(dest.name + '.partial')
                written = 0
                with z.open(info) as src, open(part, 'wb') as out:
                    while chunk := src.read(CHUNK):
                        written += len(chunk)
                        if written > info.file_size:
                            raise Problem(f'a file in the zip is larger than it says: {info.filename[:80]!r}.')
                        out.write(chunk)
                        done += len(chunk)
                        progress(done)
                if written != info.file_size:
                    raise Problem(f'a file in the zip came out the wrong size: {info.filename[:80]!r}.')
                os.replace(part, dest)
                t = time.mktime(info.date_time + (0, 0, -1))
                os.utime(dest, (t, t))
    progress.done(done)
    return root


def switch(new: Path, target: Path):
    """Put <new> at <target> with renames. Returns where the old library went, or None."""
    old = None
    if target.exists():
        old = target.with_name(f'{target.name}.old-{datetime.now():%Y%m%d-%H%M%S}')
        os.replace(target, old)
    try:
        os.replace(new, target)
    except OSError:
        if old:
            os.replace(old, target)
        raise
    return old


# ---------------------------------------------------------------- fetch ----

def free_space_ok(folder: Path, need: int):
    free = shutil.disk_usage(folder).free
    if free < need + SPACE_MARGIN:
        raise Problem(f'not enough free space in {folder}: {gb(free)} free, about {gb(need + SPACE_MARGIN)} needed.')


def match_zips(zips, pack: manifest.Pack):
    """Pair zips from elsewhere with the pack's files, by size. The name may have changed on the way."""
    pairs = []
    for z in zips:
        size = z.stat().st_size
        f = next((f for f in pack.files if f.size == size), None)
        if f is None:
            raise Problem(f'{z} ({size:,} bytes) is not one of the {pack.id} library\'s files.')
        pairs.append((z, f))
    missing = {f.name for f in pack.files} - {f.name for _, f in pairs}
    if missing:
        raise Problem(f'the {pack.id} library also needs: {", ".join(sorted(missing))}.')
    return pairs


def fetch(pack_id, dest=None, zips=(), keep_zip=False, download_only=False, manifest_source=None, say=say):
    """Get a library into <dest>/LastbookData (default: the data home's <pack>/LastbookData). Returns its path."""
    pack = manifest.pack(manifest.load(manifest_source), pack_id)
    folder = Path(dest).expanduser() if dest else paths.library(pack_id).parent
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / DATA_NAME

    if zips:
        pairs = match_zips([Path(z).expanduser() for z in zips], pack)
    else:
        need = sum(f.size for f in pack.files if not (folder / f.name).is_file())
        need -= sum((folder / (f.name + '.partial')).stat().st_size
                    for f in pack.files if (folder / (f.name + '.partial')).is_file())
        if not download_only:
            need += pack.installed_bytes
        free_space_ok(folder, max(need, 0))
        say(f'Getting the {pack.title} library ({gb(sum(f.size for f in pack.files))}) into {folder}')
        pairs = [(download(f, folder, say), f) for f in pack.files]

    for path, f in pairs:
        verify(path, f, say)
    if download_only:
        say('Downloaded and checked: ' + ', '.join(str(p) for p, _ in pairs))
        return folder

    staging = folder / f'{DATA_NAME}.unpack'
    if zips:
        free_space_ok(folder, pack.installed_bytes)
    new = unpack([p for p, _ in pairs], staging, pack.installed_bytes, say)
    old = switch(new, target)
    staging.rmdir()
    if not zips and not keep_zip:
        for p, _ in pairs:
            p.unlink()
    say(f'\nThe {pack.title} library is ready: {target}')
    if old:
        say(f'The library it replaced is in {old}. Delete it once the new one works.')
    say(f'Serve it with: lbx serve {target}')
    return target
