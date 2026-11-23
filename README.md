# lastbook-kit

An unofficial toolkit for technical users of [Lastbook](https://github.com/Immortal-Protocols/lastbook)'s offline survival library: get a library, check it, and serve it to a browser, without the desktop app, the installers or a local AI.

**Status: early.** `lbx fetch` gets a library and `lbx serve` serves it. Checking a library is next. Work is tracked in [issues](https://github.com/jonocodes/lastbook-kit/issues), starting from the pinned [Roadmap](https://github.com/jonocodes/lastbook-kit/issues?q=is%3Aissue+label%3Aroadmap).

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

### Serving

`lbx serve [DATA]` runs upstream's server on a data folder. The default is the Small library in the data home.

- `--lan` also serves other devices on the network. They need the access link it prints.
- The data folder has to be writable, because the server keeps its page images and map tiles in `derived/`.

### Development

```sh
just test        # all tests. The Small-library ones skip unless Small is in the data home
just test-fast   # only the tests that need no library
just fetch       # get the Small library into the data home
just serve       # serve it
```

Fetch and check are tested against a tiny library on a local server, so those tests need no network.

## How it works

lastbook-kit doesn't rewrite anything. It pins an exact Lastbook commit and runs Lastbook's own browser server (`server.py`), adding only what sits around it:

```
upstream/        Lastbook at a pinned commit
lbx/fetch.py     get a library from Lastbook's manifest, check its SHA-256, unpack it
lbx/manifest.py  read Lastbook's manifest-v1.json
lbx/check.py     check a data folder against its pack-manifest.tsv
lbx/serve.py     start upstream server.py with lastbook-kit's defaults
lbx/overlay/     small patches where upstream's defaults get in the way
tests/           run against Lastbook's real Small library
```

Lastbook moves fast. The pin moves forward only when the tests pass.

### The upstream pin

`upstream/` is a git submodule, pinned to Lastbook `v1.1.16` (`5aec1667`). Clone with it:

```sh
git clone --recurse-submodules https://github.com/jonocodes/lastbook-kit.git
# or, in an existing clone:
git submodule update --init
```

To move the pin, do it on purpose, one release at a time:

1. `git -C upstream fetch --tags && git -C upstream checkout <tag>`
2. Run the full test suite, including the tests against the real Small library.
3. If they pass, commit the new pin (`git add upstream`) and update the version above. If they don't, fix the overlay or stay where you are.

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
