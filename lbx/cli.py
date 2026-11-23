"""The lbx command."""
import argparse
import sys

from lbx import __version__
from lbx.errors import Problem


def main(argv=None):
    ap = argparse.ArgumentParser(prog='lbx', description='Get, check and serve Lastbook libraries.')
    ap.add_argument('--version', action='version', version=f'lbx {__version__}')
    sub = ap.add_subparsers(dest='command', required=True)

    s = sub.add_parser('serve', help="serve a data folder to a browser with upstream's server.py")
    s.add_argument('data', help='the data folder (LastbookData/, holding library-data/ and derived/)')
    s.add_argument('--port', type=int, default=8890)
    s.add_argument('--lan', action='store_true', help='also serve other devices on this network, with an access link')
    s.add_argument('--no-index', action='store_true', help='do not update the semantic index in the background')

    a = ap.parse_args(argv)
    try:
        if a.command == 'serve':
            from lbx import serve
            serve.run(a.data, port=a.port, lan=a.lan, no_index=a.no_index)
    except Problem as e:
        print(f'lbx: {e}', file=sys.stderr)
        return 2
    return 0
