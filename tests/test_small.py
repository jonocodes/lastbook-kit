"""The real thing against the real Small library: the gate for moving the upstream pin.

Skipped unless Small is in the data home (`lbx fetch small`). See the README's "The upstream pin".
"""
import json
import shutil
import urllib.parse

import pytest

from conftest import request
from lbx import check

pytestmark = pytest.mark.small

VIDEO = '/videos/first-aid/How_to_use_a_Tourniquet_to_Control_Life-Threatening_Bleeding [k98ilfQmUWw].mp4'
CERT_MANUAL = 'ed5bac0a81b009'      # CERT Basic Training Participant Manual (2019), 268 pages


def get_json(base, path):
    status, _, body = request(base, path)
    assert status == 200, path
    return json.loads(body)


def tile(lat, lon, z):
    import math
    n = 2 ** z
    x = int((lon + 180) / 360 * n)
    y = int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)
    return f'/api/map/tile/{z}/{x}/{y}'


# ---------------------------------------------------------------- lbx check ----

def test_check_finds_a_changed_file(small, tmp_path):
    """A copy of Small made of links to the real files, except one changed copy. The real library isn't touched."""
    entries = check.read_manifest(small)
    victim = min((e for e in entries if e.path.startswith('library-data/') and e.bytes > 1000), key=lambda e: e.bytes)
    shadow = tmp_path / 'LastbookData'
    for e in entries + [check.Entry(check.MANIFEST, 0, '', '')]:
        p = shadow / e.path
        p.parent.mkdir(parents=True, exist_ok=True)
        if e.path == victim.path:
            shutil.copyfile(small / e.path, p)
            data = bytearray(p.read_bytes())
            data[len(data) // 2] ^= 0xFF
            p.write_bytes(data)
        else:
            p.symlink_to(small / e.path)
    assert check.check(shadow, quick=True).ok
    r = check.check(shadow)
    assert not r.ok and r.wrong_hash == [victim.path]


# ---------------------------------------------------------------- lbx serve ----

def test_answers(small_server):
    lib = get_json(small_server, '/api/library')
    assert lib['pdfs'] >= 140 and lib['videos'] >= 40
    assert len(lib['zims']) == 2
    status = get_json(small_server, '/api/assistant/status')
    assert status['online'] is False                 # no AI: Chat lists pages instead


def test_serves_the_app(small_server):
    status, _, body = request(small_server, '/')
    assert status == 200 and b'<html' in body.lower()


def test_lists_the_guides(small_server):
    topics = get_json(small_server, '/api/topics')
    assert {'water', 'hurt', 'power', 'food'} <= {t['id'] for t in topics}


def test_search_finds_the_canning_guides(small_server):
    found = get_json(small_server, '/api/find?q=boil+water')
    titles = [r['title'] for r in found['results'][:10]]
    assert any('Boiling Water Canners' in t for t in titles), titles
    assert any('HomeCan' in t for t in titles), titles


def test_place_search(small_server):
    places = get_json(small_server, '/api/places?q=94110')
    assert places and places[0]['kind'] == 'ZIP code area'
    towns = get_json(small_server, '/api/places?q=Sacramento')
    assert any(p['detail'].startswith('Sacramento County') for p in towns)


@pytest.mark.parametrize('z', [6, 9, 12])
def test_map_tiles_have_data(small_server, z):
    status, _, body = request(small_server, tile(38.58, -121.49, z))      # Sacramento
    assert status == 200
    assert len(body) > 1000, f'zoom {z}: {len(body)} bytes'


def test_an_encyclopedia_article_opens(small_server):
    status, headers, body = request(small_server, '/zim/mdwiki_en_all_maxi_2025-11.zim/A/Cholera')
    assert status == 200 and headers['Content-Type'].startswith('text/html')
    assert b'Cholera' in body and len(body) > 50_000


def test_a_video_answers_a_byte_range(small_server):
    status, headers, body = request(small_server, urllib.parse.quote(VIDEO), {'Range': 'bytes=1000000-1000999'})
    assert status == 206
    assert headers['Content-Range'].startswith('bytes 1000000-1000999/')
    assert len(body) == 1000


def test_a_pdf_page_renders(small_server):
    status, headers, body = request(small_server, f'/api/page/{CERT_MANUAL}/135.png')
    assert status == 200 and body.startswith(b'\x89PNG')
    text = get_json(small_server, f'/api/page/{CERT_MANUAL}/135')
    assert 'bleach' in json.dumps(text).lower()


def test_the_library_is_left_as_published(small, small_server):
    """After everything above, the library folder still matches its manifest, with nothing added."""
    request(small_server, tile(38.58, -121.49, 6))
    r = check.check(small, quick=True)
    assert r.ok and r.extra == []
