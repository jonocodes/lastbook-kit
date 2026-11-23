"""Start upstream's server.py from the pinned checkout, with lastbook-kit's defaults.

  - Local only (127.0.0.1) unless --lan or --bind. Then other devices need the access link, unless --no-key.
  - The server's own files go to a state folder, so the library stays as published (overlay/state.py).
  - No setup or update API, and no local AI: Chat lists the best pages.
"""
import hashlib
import ipaddress
import os
import secrets
import socket
import sys
from pathlib import Path

from lbx import overlay, upstream
from lbx.errors import Problem

LOCAL = '127.0.0.1'


class NotALibrary(Problem):
    pass


def data_folder(path) -> Path:
    path = Path(path).expanduser().resolve()
    if not (path / 'library-data').is_dir():
        raise NotALibrary(f'{path} is not a Lastbook data folder: it has no library-data/ folder.')
    return path


def state_folder(data: Path, state=None) -> Path:
    """--state, else $XDG_STATE_HOME/lastbook-kit/serve/<pack>-<hash of the data folder's path>."""
    if state:
        path = Path(state).expanduser()
    else:
        base = Path(os.environ.get('XDG_STATE_HOME') or Path.home() / '.local' / 'state')
        key = hashlib.sha256(str(data).encode()).hexdigest()[:12]
        path = base / 'lastbook-kit' / 'serve' / f'{data.parent.name or "library"}-{key}'
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise Problem(f'cannot make the state folder {path} ({e.strerror}).')
    return path.resolve()


def lan_key(state: Path) -> str:
    """The access key for other devices, kept in the state folder. Delete the file to change it."""
    f = state / 'lan-key'
    if not f.exists():
        f.write_text(secrets.token_urlsafe(18))
        os.chmod(f, 0o600)
    return f.read_text(encoding='utf-8').strip()


def load(data: Path):
    """Import upstream's server module for this data folder. It reads LASTBOOK_DATA when imported."""
    os.environ['LASTBOOK_DATA'] = str(data)
    sys.path.insert(0, str(upstream.root()))
    import server  # upstream's server.py
    return server


def this_computers_address():
    """This computer's address on the network, as upstream works it out. No packet is sent."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(('10.255.255.255', 1))
            return s.getsockname()[0]
    except OSError:
        return '<this-computer>'


def run(data, port=8890, lan=False, bind=None, hosts=(), no_key=False, state=None, no_index=False, say=print):
    data = data_folder(data)
    bind = bind or ('0.0.0.0' if lan else LOCAL)
    try:
        ipaddress.IPv4Address(bind)
    except ValueError:
        raise Problem(f'--bind takes an IPv4 address, not {bind!r}.')
    server = load(data)
    state = state_folder(data, state)
    overlay.apply(server, state=state, hosts=hosts, no_key=no_key)
    server.init(no_index)
    if bind != LOCAL and not no_key:
        server.LAN_KEY = lan_key(state)
    try:
        srv = server.SERVER = server.HTTPServer((bind, port), server.Handler)
    except OSError as e:
        raise Problem(f'cannot listen on {bind}:{port} ({e.strerror}).')

    shown = this_computers_address() if bind == '0.0.0.0' else bind
    say(f'Lastbook: http://{LOCAL if bind in (LOCAL, "0.0.0.0") else bind}:{port}/', flush=True)
    if bind != LOCAL:
        if no_key:
            say(f'Other devices: http://{shown}:{port}/  (no access key: anyone who can reach this computer can open it)', flush=True)
        else:
            say(f'Other devices: http://{shown}:{port}/?key={server.LAN_KEY}  '
                f'(keep this link private; delete {state / "lan-key"} to change it)', flush=True)
    for h in hosts:
        say(f'Also answers as: http://{h}:{port}/', flush=True)
    say(f'Library: {data}', flush=True)
    say(f'State (page images, map tiles, index): {state}', flush=True)
    try:
        srv.serve_forever()
    finally:
        srv.server_close()
