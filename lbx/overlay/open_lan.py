"""--no-key: other devices on the network need no access link.

Why: upstream's --lan asks every other device for a key once, through a link printed at start-up. On a
network you trust (a household, a field kit) that's a step people get stuck on. Off unless asked for.
"""


def apply(server):
    server.Handler.lan_ok = lambda self: True
