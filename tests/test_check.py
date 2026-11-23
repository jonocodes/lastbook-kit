"""lbx check on a tiny library, and on the real Small library when it's there."""
import pytest

import fakepack
from conftest import run_lbx
from lbx import check
from lbx.errors import Problem

PDF = 'library-data/documents/guide.pdf'
VIDEO = 'library-data/videos/first-aid/How to: stop bleeding [abc123].mp4'


@pytest.fixture
def lib(tmp_path):
    return fakepack.make_library(tmp_path)


def test_a_clean_library_passes(lib):
    r = check.check(lib)
    assert r.ok
    assert r.entries == len(fakepack.FILES) + 1     # + pack.json
    assert (r.missing, r.wrong_size, r.wrong_hash, r.extra) == ([], [], [], [])


def test_a_changed_byte_fails_the_full_check_but_not_the_quick_one(lib):
    p = lib / PDF
    data = bytearray(p.read_bytes())
    data[1000] ^= 0xFF
    p.write_bytes(data)
    assert check.check(lib, quick=True).ok
    r = check.check(lib)
    assert not r.ok and r.wrong_hash == [PDF]


def test_a_short_file_fails(lib):
    p = lib / VIDEO
    p.write_bytes(p.read_bytes()[:-1])
    r = check.check(lib, quick=True)
    assert not r.ok and r.wrong_size == [(VIDEO, 300_000, 299_999)]


def test_a_missing_file_fails(lib):
    (lib / PDF).unlink()
    r = check.check(lib)
    assert not r.ok and r.missing == [PDF]


def test_files_the_server_writes_are_ignored_and_others_reported(lib):
    for rel in ('derived/cache/abc-1-360.png', 'derived/geo/tilecache/n1/3/1/2.json',
                'derived/index/semantic.sqlite', 'derived/lan-key'):
        (lib / rel).parent.mkdir(parents=True, exist_ok=True)
        (lib / rel).write_text('x')
    (lib / 'library-data' / 'notes.txt').write_text('mine')
    r = check.check(lib)
    assert r.ok
    assert r.extra == ['library-data/notes.txt']


def test_no_manifest_is_a_problem(tmp_path):
    with pytest.raises(Problem, match='no pack-manifest.tsv'):
        check.check(tmp_path)


def test_a_manifest_row_outside_the_library_is_a_problem(lib):
    with open(lib / check.MANIFEST, 'a') as f:
        f.write('../outside.txt\t1\t' + '0' * 64 + '\tclone\t\n')
    with pytest.raises(Problem, match='names a file oddly'):
        check.check(lib)


def test_cli_exit_codes(lib, tmp_path):
    ok = run_lbx('check', lib)
    assert ok.returncode == 0 and ok.stdout.startswith('OK: all 5 files')
    (lib / PDF).unlink()
    bad = run_lbx('check', lib, '--quick')
    assert bad.returncode == 1
    assert 'Missing (1):' in bad.stdout and 'NOT OK' in bad.stdout
    none = run_lbx('check', tmp_path / 'nowhere')
    assert none.returncode == 2


@pytest.mark.small
def test_the_small_library_passes(small):
    r = check.check(small)
    assert r.ok, (r.missing[:5], r.wrong_size[:5], r.wrong_hash[:5])
    assert r.entries > 800
