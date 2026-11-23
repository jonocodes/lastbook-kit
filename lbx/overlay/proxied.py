"""A request that came through a proxy counts as coming from another device.

Why: upstream decides "this computer" by the connection's address. Behind a reverse proxy on the same
computer every request comes from 127.0.0.1, so every visitor would skip the access key and reach the
parts meant for this computer only (setup, updates, notes). A request carrying a forwarding header is
treated as coming from elsewhere. The header is never trusted the other way: it can't make a request local.
"""
FORWARDING = ('Forwarded', 'X-Forwarded-For', 'X-Real-IP')
ELSEWHERE = ('192.0.2.1', 0)      # TEST-NET-1 (RFC 5737): never this computer


def apply(server):
    Handler = server.Handler
    upstream_parse_request = Handler.parse_request

    def parse_request(self):
        ok = upstream_parse_request(self)
        if ok and any(self.headers.get(h) for h in FORWARDING):
            self.client_address = ELSEWHERE
        return ok

    Handler.parse_request = parse_request
