"""`lbx serve` against the real Small library. Skipped unless LASTBOOK_KIT_DATA is set."""
import json
import urllib.request

import pytest

pytestmark = pytest.mark.small


def get(url):
    with urllib.request.urlopen(url, timeout=30) as r:
        return r.status, r.read()


def test_serves_the_app(small_server):
    status, body = get(small_server + '/')
    assert status == 200
    assert b'<html' in body.lower()


def test_lists_the_guides(small_server):
    status, body = get(small_server + '/api/topics')
    assert status == 200
    assert len(json.loads(body)) >= 10
