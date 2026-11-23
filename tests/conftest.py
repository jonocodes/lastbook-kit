import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def run_lbx(*args, env=None, **kw):
    """Run `python -m lbx` as a separate process, as a person would."""
    e = {**os.environ, **(env or {})}
    return subprocess.run([sys.executable, '-m', 'lbx', *map(str, args)], cwd=ROOT, env=e,
                          capture_output=True, text=True, **kw)


@pytest.fixture(scope='session')
def small():
    """The real Small library's data folder (LastbookData/), from LASTBOOK_KIT_DATA."""
    base = os.environ.get('LASTBOOK_KIT_DATA')
    if not base:
        pytest.skip('LASTBOOK_KIT_DATA is not set: no Small library to test against')
    for p in (Path(base) / 'small' / 'LastbookData', Path(base) / 'LastbookData', Path(base)):
        if (p / 'library-data').is_dir():
            return p
    pytest.skip(f'no Small library under LASTBOOK_KIT_DATA ({base})')


def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


@pytest.fixture(scope='session')
def small_server(small):
    """`lbx serve` on the Small library, on a free loopback port. Yields the base URL."""
    port = free_port()
    proc = subprocess.Popen([sys.executable, '-m', 'lbx', 'serve', str(small), '--port', str(port), '--no-index'],
                            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    base = f'http://127.0.0.1:{port}'
    deadline = time.monotonic() + 60
    while True:
        try:
            urllib.request.urlopen(base + '/', timeout=2).read()
            break
        except OSError:
            if proc.poll() is not None or time.monotonic() > deadline:
                proc.kill()
                pytest.fail('lbx serve did not start:\n' + (proc.stdout.read() if proc.stdout else ''))
            time.sleep(0.3)
    yield base
    proc.terminate()
    proc.wait(timeout=10)
