"""lbx serve and its overlays, on a tiny library. Everything listens on loopback only.

A client connecting from 127.0.0.2 counts as another device to upstream (it only trusts 127.0.0.1 and ::1),
so the access-key rules can be tested without listening on the network.
"""
import os
import re
import stat

import pytest

import fakepack
from conftest import lbx_serve, request, run_lbx


@pytest.fixture
def lib(tmp_path):
    return fakepack.make_library(tmp_path / 'lib')


def snapshot(root):
    return {p.relative_to(root).as_posix(): (p.stat().st_size, p.stat().st_mtime_ns) for p in root.rglob('*')}


def test_serves_a_read_only_library_and_leaves_it_as_published(lib, tmp_path):
    before = snapshot(lib)
    modes = {p: p.stat().st_mode for p in [lib, *lib.rglob('*')]}
    for p in modes:
        p.chmod(stat.S_IMODE(modes[p]) & ~0o222)
    state = tmp_path / 'state'
    try:
        with lbx_serve(lib, '--state', state) as (base, _):
            assert request(base, '/')[0] == 200
            assert request(base, '/api/topics')[0] == 200
    finally:
        for p, m in modes.items():
            p.chmod(stat.S_IMODE(m))
    assert snapshot(lib) == before
    assert (state / 'index' / 'semantic.sqlite').is_file()      # upstream would have written it into derived/index/


def test_state_defaults_to_the_xdg_state_folder(lib, tmp_path, monkeypatch):
    monkeypatch.setenv('XDG_STATE_HOME', str(tmp_path / 'xdg'))
    with lbx_serve(lib) as (base, log):
        assert request(base, '/')[0] == 200
    states = list((tmp_path / 'xdg' / 'lastbook-kit' / 'serve').iterdir())
    assert len(states) == 1 and states[0].name.startswith('lib-')
    assert f'State (page images, map tiles, index): {states[0]}' in log.read_text()


def test_host_names_are_refused_unless_given(lib, tmp_path):
    with lbx_serve(lib, '--state', tmp_path / 's', '--host', 'lastbook.local') as (base, _):
        port = base.rsplit(':', 1)[1]
        assert request(base, '/', {'Host': f'lastbook.local:{port}'})[0] == 200
        assert request(base, '/', {'Host': 'LASTBOOK.local.'})[0] == 200
        assert request(base, '/', {'Host': 'elsewhere.example'})[0] == 403
        assert request(base, '/', {'Host': 'localhost'})[0] == 200


def test_setup_and_update_are_off(lib, tmp_path):
    with lbx_serve(lib, '--state', tmp_path / 's') as (base, _):
        for path in ('/api/setup/status', '/api/update/state', '/api/%73etup/status'):
            assert request(base, path)[0] == 404, path
        assert request(base, '/api/update/check', method='POST')[0] == 404


def test_a_proxied_request_is_another_device(lib, tmp_path):
    with lbx_serve(lib, '--state', tmp_path / 's') as (base, _):
        assert request(base, '/')[0] == 200
        for h in ('X-Forwarded-For', 'Forwarded', 'X-Real-IP'):
            assert request(base, '/', {h: '203.0.113.9'})[0] == 403, h


def test_other_devices_need_the_access_link(lib, tmp_path):
    state = tmp_path / 's'
    with lbx_serve(lib, '--state', state, bind='127.0.0.2') as (base, log):
        key = (state / 'lan-key').read_text().strip()
        assert oct((state / 'lan-key').stat().st_mode & 0o777) == '0o600'
        assert f'?key={key}' in log.read_text()
        other = dict(source='127.0.0.2')
        assert request(base, '/', **other)[0] == 403
        assert request(base, '/?key=wrong', **other)[0] == 403
        status, headers, _ = request(base, f'/?key={key}', **other)
        assert status == 302 and 'sg_key=' in headers.get('Set-Cookie', '')
        cookie = {'Cookie': f'sg_key={key}'}
        assert request(base, '/', cookie, **other)[0] == 200
        assert request(base, '/api/topics', cookie, **other)[0] == 200


def test_no_key_lets_other_devices_in(lib, tmp_path):
    with lbx_serve(lib, '--state', tmp_path / 's', '--no-key', bind='127.0.0.2') as (base, log):
        assert request(base, '/', source='127.0.0.2')[0] == 200
        assert 'no access key' in log.read_text()
        assert not (tmp_path / 's' / 'lan-key').exists()


def test_bind_takes_an_address(lib):
    r = run_lbx('serve', lib, '--bind', 'lastbook.local')
    assert r.returncode == 2 and 'IPv4 address' in r.stderr


def test_preflight_passes_when_the_compiled_packages_load():
    from lbx import serve
    serve.preflight()


def test_preflight_names_what_cannot_load_and_what_it_breaks(monkeypatch):
    from lbx import serve
    from lbx.errors import Problem
    monkeypatch.setattr(serve, 'NEEDED', {'numpy': 'PDF page images', 'no_such_module_xyz': 'encyclopedias'})
    with pytest.raises(Problem) as e:
        serve.preflight()
    msg = str(e.value)
    assert 'no_such_module_xyz' in msg and 'encyclopedias' in msg
    assert 'numpy' not in msg.split('\n', 1)[1]          # only what failed is listed


def test_preflight_on_nixos_points_at_the_dev_shell(monkeypatch):
    from lbx import serve
    from lbx.errors import Problem
    monkeypatch.setattr(serve, 'NEEDED', {'no_such_module_xyz': 'encyclopedias'})
    monkeypatch.setattr(serve, 'on_nixos', lambda: True)
    monkeypatch.delenv('IN_NIX_SHELL', raising=False)
    with pytest.raises(Problem, match='nix develop'):
        serve.preflight()
