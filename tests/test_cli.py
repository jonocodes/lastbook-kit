from lbx import __version__

from conftest import run_lbx


def test_version():
    r = run_lbx('--version')
    assert r.returncode == 0
    assert r.stdout.strip() == f'lbx {__version__}'


def test_serve_refuses_a_folder_that_is_not_a_library(tmp_path):
    r = run_lbx('serve', tmp_path)
    assert r.returncode == 2
    assert 'not a Lastbook data folder' in r.stderr
    assert 'Traceback' not in r.stderr


def test_serve_says_how_to_get_upstream_when_it_is_missing(tmp_path):
    (tmp_path / 'library-data').mkdir()
    r = run_lbx('serve', tmp_path, env={'LBX_UPSTREAM': str(tmp_path / 'nowhere')})
    assert r.returncode == 2
    assert 'git submodule update --init' in r.stderr
