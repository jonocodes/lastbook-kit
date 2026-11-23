from lbx import upstream


def test_finds_upstream():
    root = upstream.root()
    assert (root / 'server.py').is_file()
    assert (root / 'web' / 'index.html').is_file()


def test_explains_a_missing_checkout(tmp_path, monkeypatch):
    monkeypatch.setenv('LBX_UPSTREAM', str(tmp_path))
    try:
        upstream.root()
    except upstream.NotFound as e:
        assert 'git submodule update --init' in str(e)
    else:
        raise AssertionError('expected NotFound')
