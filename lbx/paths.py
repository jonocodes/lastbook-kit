"""Where lastbook-kit keeps libraries by default."""
import os
from pathlib import Path


def data_home() -> Path:
    """LASTBOOK_KIT_DATA, else $XDG_DATA_HOME/lastbook-kit (~/.local/share/lastbook-kit)."""
    env = os.environ.get('LASTBOOK_KIT_DATA')
    if env:
        return Path(env).expanduser()
    xdg = os.environ.get('XDG_DATA_HOME') or Path.home() / '.local' / 'share'
    return Path(xdg) / 'lastbook-kit'


def library(pack: str) -> Path:
    """The default data folder for a pack: <data home>/<pack>/LastbookData."""
    return data_home() / pack / 'LastbookData'
