"""Small patches over upstream's server.py, applied at start-up.

Each overlay is its own module here and says why it exists. None of them edit
the upstream checkout: they change the imported module in memory.
"""


def apply(server, **options):
    """Apply the overlays to upstream's imported server module."""
