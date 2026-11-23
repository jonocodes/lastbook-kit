"""Small patches over upstream's server.py, applied at start-up.

Each overlay is its own module here and says why it exists. None of them edit the upstream checkout:
they change the imported module in memory, before the server starts.

  state           the server's own files go to a state folder, not the library
  fixed_library   no setup or update API: libraries are managed with lbx fetch
  proxied         a request through a reverse proxy counts as another device
  host_names      answer under the names given with --host
  open_lan        --no-key: no access link for other devices
"""
from lbx.overlay import fixed_library, host_names, open_lan, proxied, state as state_overlay


def apply(server, state, hosts=(), no_key=False):
    """Apply the overlays to upstream's imported server module."""
    state_overlay.apply(server, state)
    fixed_library.apply(server)
    proxied.apply(server)
    host_names.apply(server, hosts)
    if no_key:
        open_lan.apply(server)
