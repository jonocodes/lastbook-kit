# lastbook-kit

An unofficial toolkit for technical users of [Lastbook](https://github.com/Immortal-Protocols/lastbook)'s offline survival library: get a library, check it, and serve it to a browser, without the desktop app, the installers or a local AI.

**Status: early but working.** `lbx fetch` gets a library, `lbx check` checks it and `lbx serve` serves it. Work is tracked in [issues](https://github.com/jonocodes/lastbook-kit/issues), starting from the pinned [Roadmap](https://github.com/jonocodes/lastbook-kit/issues?q=is%3Aissue+label%3Aroadmap).

> Not affiliated with Lastbook. Problems with Lastbook's own code or libraries belong [upstream](https://github.com/Immortal-Protocols/lastbook/issues).

## Why

Lastbook's curation is the valuable part:
- **Hand-picked documents and videos**, with sources and checksums.
- **A full-text search index**, down to the page.
- **Guides** for urgent needs that point at exact pages.
- **Offline maps** with place search.

The upstream project wraps that data in signed desktop apps for non-technical people, which is the right call for them. It's harder for technical users who just want to hand the data to someone and run it anywhere.

lastbook-kit keeps Lastbook's data exactly as it's published and swaps the delivery:

- **For technical users.** Python and a browser. No per-distro packages, no Docker.
- **No LLM.** Keyword search is enough, and Lastbook's interface already falls back to listing the best pages when no model is set up.
- **Still a web interface,** for the guides, reader, videos, encyclopedias and the map.
- **Data and machinery stay separate.** How libraries travel (mirrors, torrents, original sources) is one concern. How they're used is another.

## Use it

**With uv** (Linux, macOS, Windows; Python 3.12 to 3.14):

```sh
git clone --recurse-submodules https://github.com/jonocodes/lastbook-kit.git
cd lastbook-kit
uv run lbx fetch small      # download (7.7 GB), check and unpack the Small library
uv run lbx serve            # serve it at http://127.0.0.1:8890/
```

`uv run` installs everything on first use. On NixOS, use the dev shell below, which puts the libraries the PyPI wheels expect on the library path.

**With Nix** (Linux x86_64 and aarch64):

```sh
nix run 'git+https://github.com/jonocodes/lastbook-kit?submodules=1' -- fetch small
nix run 'git+https://github.com/jonocodes/lastbook-kit?submodules=1' -- serve
nix develop      # or `direnv allow`: Python, uv and just, for working on lastbook-kit
```

The `github:` form doesn't work, because it leaves out the `upstream/` submodule.

### Getting a library

`lbx fetch small|medium|all` reads Lastbook's [manifest](https://downloads.lastbook.org/manifest-v1.json) and downloads the pack's zip. It checks the size and SHA-256, unpacks the zip beside any existing library, and switches it in with a rename. The library it replaces is kept as `LastbookData.old-<time>`.

- **Stopped downloads resume.** Run the same command again. A dropped connection is retried on its own.
- **`--zip PATH`** uses a zip you got some other way: a torrent, a friend or a drive. It's matched to the manifest by size and checked by SHA-256. Give a manifest file with `--manifest` when offline.
- **`--dest DIR`** puts `LastbookData/` in `DIR`. The default is `<data home>/<pack>/`, where the data home is `$LASTBOOK_KIT_DATA`, else `~/.local/share/lastbook-kit`.
- **`--download-only`** and **`--keep-zip`** keep the zip, for passing on.

### Checking a library

`lbx check [DATA]` checks every file against the library's own `pack-manifest.tsv`: size and SHA-256, or sizes only with `--quick`. It exits 1 if anything is missing or changed, so it can run in scripts. It's useful after copying a library to a drive or getting one from someone else. The full check of Small takes seconds.

Files the server writes while it runs (`derived/cache/`, `derived/geo/tilecache/`, `derived/index/`) are ignored. Other files that aren't in the pack are listed, but they aren't an error. `lbx fetch` runs the quick check before it switches a new library in.

### Serving

`lbx serve [DATA]` runs upstream's server on a data folder. The default is the Small library in the data home. It differs from running upstream's `server.py` directly in a few ways, each a small overlay in `lbx/overlay/` that says why it exists:

- **The library stays as published.** Page images, map tiles, the search index and the access key go to a state folder, by default `~/.local/state/lastbook-kit/serve/<pack>-<hash>/`. A library can be on a read-only drive. `--state DIR` picks another place, and `--state DATA/derived` gives upstream's behaviour back.
- **No setup or update API.** Libraries are managed with `lbx fetch`, and the server makes no requests of its own. There's no local AI, so Chat lists the best-matching pages.
- **A request through a reverse proxy counts as another device.** It needs the access link like any other.

Who can open it:

| Option | Listens on | Other devices |
|---|---|---|
| (none) | `127.0.0.1` | none |
| `--lan` | `0.0.0.0` | with the access link it prints |
| `--bind ADDR` | `ADDR` | with the access link |
| `--no-key` (with `--lan` or `--bind`) | | anyone who can reach this computer. Only on a network you trust |

Upstream answers only to `localhost` and bare IP addresses, a defence against DNS rebinding. `--host NAME` adds a name, such as `lastbook.local` or the name a reverse proxy uses. Repeat it for more names.

### Development

```sh
just test            # all tests. The Small-library ones skip unless Small is in the data home
just test-fast       # only the tests that need no library
just ui              # drive the web interface on Small in Chromium; screenshots in artifacts/screenshots/
just fetch           # get the Small library into the data home
just serve           # serve it
just bump-upstream <tag>   # move the upstream pin and run everything against it
```

Fetch, check and the serve overlays are tested against a tiny library on loopback, so those tests need no network and run in CI. The tests in `tests/test_small.py` and `just ui` run the real server on the real Small library. Outside the Nix dev shell, `just ui` needs Node and `npx playwright-core install chromium`, or `CHROME=<path to Chromium>`.

## How it works

lastbook-kit doesn't rewrite anything. It pins an exact Lastbook commit and runs Lastbook's own browser server (`server.py`), adding only what sits around it:

```
upstream/        Lastbook at a pinned commit
lbx/fetch.py     get a library from Lastbook's manifest, check its SHA-256, unpack it
lbx/manifest.py  read Lastbook's manifest-v1.json
lbx/check.py     check a data folder against its pack-manifest.tsv
lbx/serve.py     start upstream server.py with lastbook-kit's defaults
lbx/overlay/     small patches where upstream's defaults get in the way: state folder,
                 no setup/update API, proxied requests, host names, no access key
tests/           a tiny library for fast tests, and the real Small library (test_small.py)
tests/ui/        drives the web interface in Chromium and keeps screenshots
```

Lastbook moves fast. The pin moves forward only when the tests pass.

### The upstream pin

`upstream/` is a git submodule, pinned to Lastbook `v1.1.16` (`5aec1667`). Clone with it:

```sh
git clone --recurse-submodules https://github.com/jonocodes/lastbook-kit.git
# or, in an existing clone:
git submodule update --init
```

To move the pin, do it on purpose, one release at a time, with Small in the data home:

```sh
just bump-upstream v1.1.17
```

That checks out the tag, updates the version above, and runs every test plus `just ui` against the real Small library. Small must be there, or the tests fail rather than skip. If everything passes, look at the screenshots and commit `upstream` and `README.md`. If anything fails, fix the overlay, or go back with `git checkout README.md && git submodule update`.

Upstream isn't bumped automatically. It merged about 150 PRs in its first 10 days.

A rewrite of the backend over Lastbook's data files is possible, since all of it is plain SQLite plus Kiwix ZIM files. It's parked until the thin layer proves too thin. See [docs/findings.md](docs/findings.md).

## The data

A Lastbook library is a folder (`LastbookData/`) of PDFs, web pages, videos, Kiwix ZIM encyclopedias and a few SQLite databases. They're published as zips with SHA-256 checksums in [`manifest-v1.json`](https://downloads.lastbook.org/manifest-v1.json):

| Library | Size |
|---|---|
| Small | 7.7 GB |
| Medium | 67.5 GB |
| All | 388 GB |

The data is the same on every OS and CPU. Details are in [docs/findings.md](docs/findings.md).

## Related projects

| Project | What it is |
|---|---|
| [Lastbook](https://github.com/Immortal-Protocols/lastbook) | The upstream project: library, desktop apps, browser server |
| [lastbook-hotspot](https://github.com/andrepcg/lastbook-hotspot) | Serves a Lastbook library from a small Wi-Fi board. Pins upstream and wraps `server.py`, the same pattern as here |
| [enzimo/lastbook](https://github.com/enzimo/lastbook) | A fork that runs Lastbook as a self-hosted web service and merges upstream daily |
| [Ark](https://github.com/jonnyace/ark) | A full rewrite (Rust, Svelte, Tauri, an offline browser app) that imports Lastbook libraries |
| [Kiwix](https://kiwix.org/) | The ZIM format and readers behind Lastbook's encyclopedias |

## Name

`lastbook-` because this runs Lastbook's code on Lastbook's data and should be easy to find for people who use it. If the backend is ever rewritten, the project gets a name of its own.

## License

MIT, as upstream. Library content keeps its publishers' own terms, listed in each library's sources page.
