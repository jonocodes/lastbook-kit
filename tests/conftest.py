import contextlib
import http.client
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.parse
from pathlib import Path

import pytest

from lbx import paths

ROOT = Path(__file__).resolve().parents[1]


def pytest_configure(config):
    """Servers started by tests keep their state in a temporary folder, never in the real ~/.local/state."""
    os.environ['XDG_STATE_HOME'] = tempfile.mkdtemp(prefix='lbx-test-state-')


def run_lbx(*args, env=None, **kw):
    """Run `python -m lbx` as a separate process, as a person would."""
    e = {**os.environ, **(env or {})}
    return subprocess.run([sys.executable, '-m', 'lbx', *map(str, args)], cwd=ROOT, env=e,
                          capture_output=True, text=True, **kw)


@pytest.fixture(scope='session')
def small():
    """The real Small library's data folder: <data home>/small/LastbookData (see lbx.paths)."""
    lib = paths.library('small')
    if not (lib / 'library-data').is_dir():
        pytest.skip(f'no Small library at {lib}. Get it with: lbx fetch small')
    return lib


def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def request(base, path='/', headers=None, source='127.0.0.1', method='GET'):
    """(status, headers, body) for one request, made from the given loopback address."""
    u = urllib.parse.urlsplit(base)
    c = http.client.HTTPConnection(u.hostname, u.port, source_address=(source, 0), timeout=30)
    try:
        c.request(method, path, headers=headers or {})
        r = c.getresponse()
        return r.status, dict(r.getheaders()), r.read()
    finally:
        c.close()


@contextlib.contextmanager
def lbx_serve(data, *args, bind='127.0.0.1', log=None):
    """`lbx serve` in its own process on a free port. Yields (base URL, path of its output)."""
    port = free_port()
    log = Path(log or tempfile.mkstemp(suffix='.log')[1])
    with open(log, 'w') as out:
        proc = subprocess.Popen([sys.executable, '-m', 'lbx', 'serve', str(data), '--port', str(port), '--no-index',
                                 *(['--bind', bind] if bind != '127.0.0.1' else []), *map(str, args)],
                                cwd=ROOT, stdout=out, stderr=subprocess.STDOUT, text=True)
    base = f'http://{bind}:{port}'
    deadline = time.monotonic() + 60
    try:
        while True:
            try:
                request(base, '/', source=bind)
                break
            except OSError:
                if proc.poll() is not None or time.monotonic() > deadline:
                    pytest.fail('lbx serve did not start:\n' + log.read_text())
                time.sleep(0.2)
        yield base, log
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.fixture(scope='session')
def small_server(small, tmp_path_factory):
    """`lbx serve` on the Small library, with its state in a temporary folder. Yields the base URL."""
    with lbx_serve(small, '--state', tmp_path_factory.mktemp('small-state')) as (base, _):
        yield base
