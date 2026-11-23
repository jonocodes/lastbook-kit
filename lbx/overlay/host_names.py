"""Answer under the host names given with --host.

Why: upstream refuses any Host header that isn't localhost or a bare IP address. That's its defence
against DNS rebinding, but it means a reverse proxy or a name on the local network (lastbook.local)
gets 403 (#1). Only the names given are added. Any other name is still refused.
"""
import urllib.parse


def apply(server, hosts):
    allowed = {h.lower().rstrip('.') for h in hosts}
    if not allowed:
        return
    Handler = server.Handler
    upstream_host_ok = Handler.host_ok

    def host_ok(self):
        try:
            name = urllib.parse.urlsplit('//' + (self.headers.get('Host') or '')).hostname or ''
        except ValueError:
            name = ''
        return name.rstrip('.') in allowed or upstream_host_ok(self)

    Handler.host_ok = host_ok
