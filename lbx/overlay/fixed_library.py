"""No setup or update API. The library is managed with lbx fetch.

Why: /api/setup/ can download and switch libraries and the local AI, and /api/update/ asks Lastbook's
website for a newer app. Both belong to the desktop app, and the browser interface hides them. lbx serve
serves a library that lbx fetch put in place, so they answer 404 and the server makes no requests of its own.
"""
import urllib.parse

OFF = ('/api/setup/', '/api/update/')


def apply(server):
    Handler = server.Handler
    for verb in ('do_GET', 'do_HEAD', 'do_POST'):
        upstream = getattr(Handler, verb)

        def handle(self, upstream=upstream):
            try:
                path = urllib.parse.unquote(urllib.parse.urlsplit(self.path).path)
            except ValueError:
                path = ''
            if path.startswith(OFF):
                return self.send_json({'error': 'not in lbx serve: libraries are managed with lbx fetch'}, 404)
            return upstream(self)

        setattr(Handler, verb, handle)
