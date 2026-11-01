import importlib.util
import json
from pathlib import Path
import threading
import time
import unittest
from http.client import HTTPConnection
from unittest.mock import patch
from http.server import ThreadingHTTPServer

spec = importlib.util.spec_from_file_location('save_web', Path(__file__).with_name('dsp-save-web.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class SaveTests(unittest.TestCase):
    def test_single_save_and_failure_report(self):
        state = m.SaveState()
        entered, release = threading.Event(), threading.Event()
        def command(*args, **kwargs):
            self.assertEqual(args[0], ['/usr/local/sbin/dsp-save'])
            entered.set()
            release.wait(3)
            return type('Result', (), {'returncode': 1, 'stdout': '', 'stderr': 'volume still writable'})()
        with patch.object(m.subprocess, 'run', side_effect=command):
            self.assertTrue(state.start())
            self.assertTrue(entered.wait(2))
            self.assertFalse(state.start())
            release.set()
            deadline = time.monotonic() + 3
            while state.snapshot()['running'] and time.monotonic() < deadline:
                time.sleep(.01)
        self.assertFalse(state.snapshot()['ok'])
        self.assertIn('volume still writable', state.snapshot()['message'])

    def test_http_origin_validation_and_fixed_action(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), m.Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        def request(method, origin, body=None):
            conn = HTTPConnection('127.0.0.1', server.server_port)
            headers = {'Host': 'dsp.local:5006', 'Content-Type': 'application/json'}
            if origin:
                headers['Origin'] = origin
            conn.request(method, '/save', body=body, headers=headers)
            response = conn.getresponse()
            code, data = response.status, response.read()
            conn.close()
            return code, data
        try:
            with patch.object(m.state, 'start', return_value=True) as start:
                self.assertEqual(request('POST', 'http://evil.example:5005', '{}')[0], 403)
                self.assertEqual(request('POST', None, '{}')[0], 403)
                self.assertEqual(request('POST', 'http://dsp.local:5005', '{"cmd":"id"}')[0], 400)
                start.assert_not_called()
                self.assertEqual(request('POST', 'http://dsp.local:5005', '{}')[0], 202)
                start.assert_called_once()
                self.assertEqual(request('GET', 'http://dsp.local:5005')[0], 200)
        finally:
            server.shutdown()
            server.server_close()
            worker.join()


if __name__ == '__main__':
    unittest.main()
