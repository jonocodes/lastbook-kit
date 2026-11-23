"""Start upstream's server.py from the pinned checkout, with lastbook-kit's defaults."""
import os
import sys
from pathlib import Path

from lbx import overlay, upstream
from lbx.errors import Problem


class NotALibrary(Problem):
    pass


def data_folder(path) -> Path:
    path = Path(path).expanduser().resolve()
    if not (path / 'library-data').is_dir():
        raise NotALibrary(f'{path} is not a Lastbook data folder: it has no library-data/ folder.')
    return path


def load(data: Path):
    """Import upstream's server module for this data folder. It reads LASTBOOK_DATA when imported."""
    os.environ['LASTBOOK_DATA'] = str(data)
    sys.path.insert(0, str(upstream.root()))
    import server  # upstream's server.py
    return server


def run(data, port=8890, lan=False, no_index=False):
    server = load(data_folder(data))
    overlay.apply(server)
    server.init(no_index)
    server.serve(port, lan)
