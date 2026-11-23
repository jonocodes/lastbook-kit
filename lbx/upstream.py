"""Where the pinned upstream Lastbook checkout is.

In a clone of this repo it's the `upstream/` submodule. The Nix package and anyone
running from elsewhere point at it with LBX_UPSTREAM.
"""
import os
from pathlib import Path

from lbx.errors import Problem


class NotFound(Problem):
    pass


def root() -> Path:
    env = os.environ.get('LBX_UPSTREAM')
    path = Path(env) if env else Path(__file__).resolve().parents[1] / 'upstream'
    if not (path / 'server.py').is_file():
        raise NotFound(
            f'upstream Lastbook not found at {path}. '
            "In a clone, run 'git submodule update --init'. Otherwise set LBX_UPSTREAM."
        )
    return path.resolve()
