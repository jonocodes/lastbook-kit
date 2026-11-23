"""Keep the server's own files out of the library, in a state folder.

Why: upstream's server.py writes page images (derived/cache/), map tiles (derived/geo/tilecache/) and a
semantic index (derived/index/) inside the data folder, and crashes at start-up when it can't (#1). Here
they go to a state folder, so a library can be read-only (a mounted drive, a shared copy) and stays
exactly as published, which is what `lbx check` checks. The layout mirrors derived/, so pointing
--state at <data>/derived gives upstream's behaviour back.
"""
import threading
from pathlib import Path


def apply(server, state: Path):
    import retrieval     # upstream's, imported by server.py

    server.CACHE = state / 'cache'
    retrieval.IDX = state / 'index'
    tiles = state / 'geo' / 'tilecache'

    def map_tile(z, x, y):
        """Upstream's map_tile (server.py), with the tile cache in the state folder."""
        version = server.data_version()
        if z > 9 or server.national_status().get('state') != 'complete':
            return server._map_tile(z, x, y, version)
        path = tiles / f'{version}/{z}/{x}/{y}.json'
        try:
            return path.read_bytes()
        except OSError:
            data = server._map_tile(z, x, y, version)
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                tmp = path.with_suffix(f'.{threading.get_ident()}.tmp')
                tmp.write_bytes(data)
                tmp.replace(path)
            except OSError:
                pass
            return data

    server.map_tile = map_tile
