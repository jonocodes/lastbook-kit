"""The lbx command."""
import argparse
import sys

from lbx import __version__, manifest, paths
from lbx.errors import Problem


def main(argv=None):
    ap = argparse.ArgumentParser(prog='lbx', description='Get, check and serve Lastbook libraries.')
    ap.add_argument('--version', action='version', version=f'lbx {__version__}')
    sub = ap.add_subparsers(dest='command', required=True)

    f = sub.add_parser('fetch', help="get a library from Lastbook's manifest, check it and unpack it")
    f.add_argument('pack', help='small, medium or all')
    f.add_argument('--dest', help='folder to put LastbookData/ in (default: <data home>/<pack>)')
    f.add_argument('--zip', action='append', default=[], metavar='PATH',
                   help='use a zip you already have instead of downloading it. It is still checked against the manifest')
    f.add_argument('--keep-zip', action='store_true', help='keep the downloaded zip after unpacking')
    f.add_argument('--download-only', action='store_true', help='download and check the zip, but do not unpack it')
    f.add_argument('--manifest', help=f'manifest URL or file (default: {manifest.URL}, or LBX_MANIFEST)')

    s = sub.add_parser('serve', help="serve a data folder to a browser with upstream's server.py")
    s.add_argument('data', nargs='?', help='the data folder (LastbookData/). Default: the Small library in the data home')
    s.add_argument('--port', type=int, default=8890)
    s.add_argument('--lan', action='store_true', help='also serve other devices on this network, with an access link')
    s.add_argument('--no-index', action='store_true', help='do not update the semantic index in the background')

    a = ap.parse_args(argv)
    try:
        if a.command == 'fetch':
            from lbx import fetch
            fetch.fetch(a.pack, dest=a.dest, zips=a.zip, keep_zip=a.keep_zip,
                        download_only=a.download_only, manifest_source=a.manifest)
        elif a.command == 'serve':
            from lbx import serve
            serve.run(a.data or paths.library('small'), port=a.port, lan=a.lan, no_index=a.no_index)
    except Problem as e:
        print(f'lbx: {e}', file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print('\nlbx: stopped.', file=sys.stderr)
        return 130
    return 0
