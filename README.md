# lastbook-kit

An unofficial toolkit for technical users of [Lastbook](https://github.com/Immortal-Protocols/lastbook)'s offline survival library: get a library, check it, and serve it to a browser, without the desktop app, the installers or a local AI.

**Status: planning.** There's no code yet. Work is tracked in [issues](https://github.com/jonocodes/lastbook-kit/issues), starting from the pinned [Roadmap](https://github.com/jonocodes/lastbook-kit/issues?q=is%3Aissue+label%3Aroadmap).

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

## How it will work

The first version doesn't rewrite anything. It pins an exact Lastbook commit and runs Lastbook's own browser server (`server.py`), adding only what sits around it:

```
upstream/        Lastbook at a pinned commit
lbx/fetch.py     get a library from Lastbook's manifest, check its SHA-256, unpack it
lbx/check.py     check a data folder against its pack-manifest.tsv
lbx/serve.py     start upstream server.py with lastbook-kit's defaults
lbx/overlay/     small patches where upstream's defaults get in the way
tests/           run against Lastbook's real Small library
```

Lastbook moves fast. The pin moves forward only when the tests pass.

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
