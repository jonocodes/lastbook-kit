# Findings

What we learned about Lastbook's data and code, and when. Everything was checked on the Small library (`Lastbook-Small-20261113.zip`, SHA-256 OK) and upstream `main` around 2026-11-21, unless a row says otherwise. Re-check before relying on it, because upstream changes daily.

## How libraries are made and shipped

- Libraries are plain zips of a data folder. `https://downloads.lastbook.org/manifest-v1.json` lists each one with its size and SHA-256.
- `packaging/build_packs.py` builds them from a snapshot of the maintainer's own collection. The tools that fetch the content aren't in the public repo.
- Every catalog record (`library-data/catalog.json`) keeps its `source_url`, `final_url`, `retrieved_at` and SHA-256.
- 96 files (0.45 GB) ship with their outbound links stripped (`how = stripped` in `pack-manifest.tsv`), so they no longer match the originals.
- Download speed: Small comes at about 99 MB/s, but Medium and All at about 1.2 MB/s per connection. All (388 GB) takes days. Upstream issues `#51` and `#124` and PRs `#135`, `#172` and `#275` work on torrents and mirrors.
- The optional local AI model is a separate 17 GB download from Hugging Face. It's in neither the libraries nor the Docker image.

## What's in Small

| Content | Size | Comes from |
|---|---|---|
| Kiwix ZIM encyclopedias (mdwiki, Appropedia) | 2.9 GB | download.kiwix.org. The same files: byte sizes match |
| Videos (41) | 2.2 GB | YouTube |
| PDFs and web pages (~190) | 0.75 GB | About 100 publisher sites (FEMA, WHO, Hesperian, USDA, FAO…) |
| Maps | 1.7 GB | Built by the maintainer from OpenStreetMap, USGS, Census and others. No single source |
| Search index, extracted text, transcripts | ~0.1 GB | Generated |

## Re-downloading from the original sources

A random sample of 30 unmodified documents, fetched from their original URLs about 4 weeks after collection:
- **28 were byte-identical.**
- **1 had changed** (FAO).
- **1 failed to download** (FEMA).

The Kiwix files can be fetched from Kiwix's mirrors. The YouTube videos can't be fetched reliably: re-downloads aren't byte-identical, and YouTube blocks bulk downloads. The maps and indexes exist only in Lastbook's libraries.

## Everything is SQLite

Each of these opens with Python's standard `sqlite3` module:

| File | Contents |
|---|---|
| `library-data/search.sqlite` | Full-text search table `pages` over 12,750 pages from 270 documents. A search answers in about 1 ms |
| `derived/geo/places.sqlite` | `place` + full-text search `place_fts`: 222k places from USGS GNIS and the Census |
| `derived/geo/national.sqlite` | `feat` with a spatial index: 4.1M features (water, roads, waterways, places). Geometry is zlib-compressed integer arrays |
| `derived/geo/water.sqlite` | Water features and resources |
| `derived/geo/terrain.sqlite` | PNG tiles, by z/x/y |

**The map:** `server.py` cuts tiles on request (`/api/map/tile/z/x/y`, JSON) in pure Python. `web/map.js` draws them on a 2D canvas with no map library. Terrain, crops and aerial layers come as image tiles.

**ZIM files** are Kiwix's format, with pages and images in zstd- or xz-compressed chunks. Python 3.14 reads them with the standard library alone: header, chunks and the `X/listing/titleOrdered/v1` title list (tested on Appropedia). Only full-text search inside a ZIM (`X/fulltext/xapian`) needs compiled code (`libzim`).

## What has compiled parts

| Part | Used for |
|---|---|
| `libzim` | ZIM reading and search |
| `pypdfium2` + numpy | Rendering PDF pages as images. Browsers can show PDFs themselves |
| `poppler-utils` (`pdftotext`) | Building the index. Not needed to read a library |
| Native app shells (WKWebView, WebView2, WebKitGTK + a GStreamer plugin) | The desktop apps only |
| llama.cpp runner | Local AI only |

`libzim`, `pypdfium2` and numpy all publish ready-made packages for Linux x86_64/aarch64, macOS and Windows. Upstream's server needs only `packaging/linux/requirements_linux.txt`: `libzim==3.13.1` (below 4, because of renamed calls), numpy, beautifulsoup4 and pypdfium2.

Upstream's Docker image (PR `#33`) was estimated at about 100 MB compressed and about 300 MB loaded. Not measured yet.

## Existing pieces upstream

- **`tools/libq.py`** (97 lines, standard library only, tested in `app.tests.test_libq`). A read-only search, title, page and table-of-contents tool over a data folder. Only its `zim` command needs `libzim`.
- **`server.py --lan`.** The browser version of the app, documented in `docs/LIBRARY-SERVER.md`. It needs an access key (`?key=`) and refuses requests under a host name (a reverse proxy gets 403).
- **Contribution rules** (`CONTRIBUTING.md`): no network except to the hosts on their approved list, no listening port in the app, plain words.

## Survey of forks (2026-11-22)

- **Forks:** 358. 13 had commits of their own on their main branch, mostly country versions (Spain, Germany, Netherlands, Brazil, Italy, Europe).
- **Branches:** about 1,000 across the forks, scanned by name. The relevant ones are in the README's related projects.
- **None of them** reads unmodified Lastbook data with a minimal toolchain.
