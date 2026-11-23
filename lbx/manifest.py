"""Lastbook's published list of libraries (manifest-v1.json)."""
import json
import os
import urllib.request
from dataclasses import dataclass

from lbx.errors import Problem

URL = 'https://downloads.lastbook.org/manifest-v1.json'
USER_AGENT = 'lastbook-kit'


@dataclass(frozen=True)
class File:
    name: str
    url: str
    size: int
    sha256: str


@dataclass(frozen=True)
class Pack:
    id: str
    title: str
    installed_bytes: int
    files: tuple


def url() -> str:
    return os.environ.get('LBX_MANIFEST') or URL


def load(source=None) -> dict:
    """The manifest, from a URL or a local file."""
    source = source or url()
    try:
        if '://' in source:
            req = urllib.request.Request(source, headers={'User-Agent': USER_AGENT})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        with open(source, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        raise Problem(f'could not read the manifest at {source} ({e}).')


def pack(manifest: dict, pack_id: str) -> Pack:
    for p in manifest.get('packs', []):
        if p.get('id') == pack_id:
            if not p.get('available', True):
                raise Problem(f'the {pack_id} library is not available for download right now.')
            files = tuple(File(f['name'], f['url'], int(f['size']), f['sha256'].lower()) for f in p['files'])
            if not files:
                raise Problem(f'the manifest lists no files for the {pack_id} library.')
            for f in files:
                if '/' in f.name or '\\' in f.name or f.name.startswith('.'):
                    raise Problem(f'the manifest names a file oddly: {f.name!r}.')
            return Pack(p['id'], p.get('title', p['id']), int(p.get('installed_bytes') or 0), files)
    known = ', '.join(p.get('id', '?') for p in manifest.get('packs', []))
    raise Problem(f'no library called {pack_id!r} in the manifest. Known: {known}.')
