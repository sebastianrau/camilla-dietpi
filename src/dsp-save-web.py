#!/usr/bin/env python3
"""LAN-only fixed-action save endpoint; no arbitrary command execution."""
import json
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit


class SaveState:
    def __init__(self):
        self.lock = threading.Lock()
        self.result = {'running': False, 'ok': None, 'message': 'Ready'}

    def start(self):
        with self.lock:
            if self.result['running']:
                return False
            self.result = {'running': True, 'ok': None, 'message': 'Saving; audio and GUI will restart…'}
        threading.Thread(target=self.save, daemon=True).start()
        return True

    def save(self):
        try:
            # No timeout/kill: interrupting dsp-save can prevent its cleanup.
            run = subprocess.run(['/usr/local/sbin/dsp-save'], capture_output=True, text=True)
            result = {'running': False, 'ok': run.returncode == 0,
                      'message': (run.stdout + run.stderr)[-12000:] or 'Save returned no output'}
        except Exception as error:
            result = {'running': False, 'ok': False, 'message': str(error)}
        with self.lock:
            self.result = result

    def snapshot(self):
        with self.lock:
            return dict(self.result)


state = SaveState()


class Handler(BaseHTTPRequestHandler):
    def allowed_origin(self):
        try:
            origin = urlsplit(self.headers.get('Origin', ''))
            target = urlsplit('http://' + self.headers.get('Host', ''))
            # Only the existing GUI on the same host may invoke or inspect saves.
            # Origin is mandatory; cross-site forms, null origins and other ports fail.
            if (origin.scheme == 'http' and (origin.port or 80) in (80, 5005)
                    and target.port == 5006 and origin.hostname
                    and origin.hostname == target.hostname
                    and not origin.username and not origin.password
                    and not origin.path and not origin.query and not origin.fragment):
                return self.headers['Origin']
        except ValueError:
            pass
        return None

    def reply(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        origin = self.allowed_origin()
        if origin:
            self.send_header('Access-Control-Allow-Origin', origin)
            self.send_header('Vary', 'Origin')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def authorized(self):
        if not self.allowed_origin():
            self.reply(403, {'message': 'Only the CamillaGUI origin is allowed'})
            return False
        if self.path != '/save':
            self.reply(404, {'message': 'Not found'})
            return False
        return True

    def do_OPTIONS(self):
        if not self.authorized():
            return
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', self.allowed_origin())
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Vary', 'Origin')
        self.end_headers()

    def do_GET(self):
        if self.authorized():
            self.reply(200, state.snapshot())

    def do_POST(self):
        if not self.authorized():
            return
        if (self.headers.get('Content-Type') != 'application/json'
                or self.headers.get('Content-Length') != '2'
                or self.headers.get('Transfer-Encoding')):
            self.reply(400, {'message': 'Expected empty JSON object'})
            return
        if self.rfile.read(2) != b'{}':
            self.reply(400, {'message': 'No save parameters are accepted'})
            return
        started = state.start()
        self.reply(202 if started else 409, state.snapshot())


if __name__ == '__main__':
    ThreadingHTTPServer(('0.0.0.0', 5006), Handler).serve_forever()
