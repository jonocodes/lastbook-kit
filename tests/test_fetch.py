"""lbx fetch against a tiny pack on a local server. No network."""
import json
import stat
import zipfile

import pytest

import fakepack
from conftest import run_lbx
from lbx import fetch
from lbx.errors import Problem

ZIP = 'Lastbook-Small-test.zip'


@pytest.fixture
def pack(tmp_path):
    """(zip bytes, the library it came from, installed bytes)."""
    lib = fakepack.make_library(tmp_path / 'src')
    z = fakepack.zip_library(lib, tmp_path / ZIP)
    return z.read_bytes(), lib, fakepack.installed_bytes(lib)


def write_manifest(tmp_path, server, pack, **kw):
    data, _, installed = pack
    m = tmp_path / 'manifest.json'
    m.write_text(json.dumps(fakepack.manifest(server.url, ZIP, data, installed, **kw)))
    return str(m)


def same_tree(a, b):
    files = lambda root: {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}
    return files(a) == files(b)


def quiet(*a, **k):
    pass


def test_fetches_checks_and_unpacks(tmp_path, pack):
    dest = tmp_path / 'dest'
    with fakepack.Server({ZIP: pack[0]}) as s:
        lib = fetch.fetch('small', dest=dest, manifest_source=write_manifest(tmp_path, s, pack), say=quiet)
    assert lib == dest / 'LastbookData'
    assert same_tree(lib, pack[1])
    assert sorted(p.name for p in dest.iterdir()) == ['LastbookData']   # zip and staging folder are gone


def test_resumes_when_the_connection_drops(tmp_path, pack):
    with fakepack.Server({ZIP: pack[0]}, drop_after=100_000, drops=2) as s:
        lib = fetch.fetch('small', dest=tmp_path / 'dest', manifest_source=write_manifest(tmp_path, s, pack), say=quiet)
        ranges = [r for _, r in s.zip_requests()]
    assert ranges == [None, 'bytes=100000-', 'bytes=200000-']
    assert same_tree(lib, pack[1])


def test_resumes_a_partial_file_from_an_earlier_run(tmp_path, pack):
    dest = tmp_path / 'dest'
    dest.mkdir()
    (dest / (ZIP + '.partial')).write_bytes(pack[0][:123_456])
    with fakepack.Server({ZIP: pack[0]}) as s:
        fetch.fetch('small', dest=dest, manifest_source=write_manifest(tmp_path, s, pack), say=quiet)
        assert s.zip_requests() == [(ZIP, 'bytes=123456-')]


def test_starts_again_when_the_server_ignores_range(tmp_path, pack):
    dest = tmp_path / 'dest'
    dest.mkdir()
    (dest / (ZIP + '.partial')).write_bytes(b'x' * 1000)       # not even the right bytes
    with fakepack.Server({ZIP: pack[0]}, ignore_range=True) as s:
        lib = fetch.fetch('small', dest=dest, manifest_source=write_manifest(tmp_path, s, pack), say=quiet)
    assert same_tree(lib, pack[1])


def test_refuses_a_zip_whose_sha256_is_wrong(tmp_path, pack):
    dest = tmp_path / 'dest'
    with fakepack.Server({ZIP: pack[0]}) as s:
        with pytest.raises(Problem, match='does not match its SHA-256'):
            fetch.fetch('small', dest=dest, manifest_source=write_manifest(tmp_path, s, pack, sha='0' * 64), say=quiet)
    assert not (dest / 'LastbookData').exists()
    assert (dest / (ZIP + '.bad')).is_file()


def test_uses_a_zip_from_elsewhere_and_keeps_it(tmp_path, pack):
    mine = tmp_path / 'from-a-friend.zip'                     # renamed on the way: matched by size, then SHA-256
    mine.write_bytes(pack[0])
    with fakepack.Server({}) as s:
        lib = fetch.fetch('small', dest=tmp_path / 'dest', zips=[mine],
                          manifest_source=write_manifest(tmp_path, s, pack), say=quiet)
        assert s.zip_requests() == []
    assert same_tree(lib, pack[1])
    assert mine.is_file()


def test_refuses_a_zip_from_elsewhere_that_is_not_the_pack(tmp_path, pack):
    other = tmp_path / 'other.zip'
    other.write_bytes(b'not it')
    with fakepack.Server({}) as s:
        with pytest.raises(Problem, match='is not one of the small library'):
            fetch.fetch('small', dest=tmp_path / 'dest', zips=[other],
                        manifest_source=write_manifest(tmp_path, s, pack), say=quiet)


def test_download_only_keeps_the_zip_and_unpacks_nothing(tmp_path, pack):
    dest = tmp_path / 'dest'
    with fakepack.Server({ZIP: pack[0]}) as s:
        fetch.fetch('small', dest=dest, download_only=True, manifest_source=write_manifest(tmp_path, s, pack), say=quiet)
    assert sorted(p.name for p in dest.iterdir()) == [ZIP]


def test_replaces_a_library_and_keeps_the_old_one_aside(tmp_path, pack):
    dest = tmp_path / 'dest'
    (dest / 'LastbookData').mkdir(parents=True)
    (dest / 'LastbookData' / 'old-marker').write_text('old')
    with fakepack.Server({ZIP: pack[0]}) as s:
        lib = fetch.fetch('small', dest=dest, manifest_source=write_manifest(tmp_path, s, pack), say=quiet)
    assert same_tree(lib, pack[1])
    old = [p for p in dest.iterdir() if p.name.startswith('LastbookData.old-')]
    assert len(old) == 1 and (old[0] / 'old-marker').read_text() == 'old'


@pytest.mark.parametrize('name', ['LastbookData/../evil.txt', '/etc/evil', 'elsewhere/file.txt', 'C:/evil', 'LastbookData\\evil'])
def test_refuses_members_outside_the_library(tmp_path, name):
    lib = fakepack.make_library(tmp_path / 'src')
    z = fakepack.zip_library(lib, tmp_path / 'bad.zip', extra=[(name, b'boo')])
    with pytest.raises(Problem):
        fetch.members(z)


def test_refuses_links(tmp_path):
    lib = fakepack.make_library(tmp_path / 'src')
    link = zipfile.ZipInfo('LastbookData/link')
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    z = fakepack.zip_library(lib, tmp_path / 'bad.zip', extra=[(link.filename, link)])
    with pytest.raises(Problem, match='link'):
        fetch.members(z)


def test_refuses_a_zip_bigger_than_the_manifest_says(tmp_path):
    lib = fakepack.make_library(tmp_path / 'src')
    z = fakepack.zip_library(lib, tmp_path / 'big.zip', extra=[('LastbookData/padding', bytes(3 << 20))])
    fetch.members(z, installed_bytes=fakepack.installed_bytes(lib) + (3 << 20))     # as it says: fine
    with pytest.raises(Problem, match='more than'):
        fetch.members(z, installed_bytes=fakepack.installed_bytes(lib))


def test_names_the_known_packs_when_asked_for_another(tmp_path, pack):
    with fakepack.Server({}) as s:
        with pytest.raises(Problem, match='Known: small, medium'):
            fetch.fetch('huge', dest=tmp_path, manifest_source=write_manifest(tmp_path, s, pack), say=quiet)


def test_cli(tmp_path, pack):
    with fakepack.Server({ZIP: pack[0]}) as s:
        r = run_lbx('fetch', 'small', '--dest', tmp_path / 'dest', env={'LBX_MANIFEST': write_manifest(tmp_path, s, pack)})
    assert r.returncode == 0, r.stderr
    assert 'library is ready' in r.stdout
    assert 'lbx serve' in r.stdout
