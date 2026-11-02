import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import quickjs

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('gui_assets', ROOT / 'tools/install_gui_assets.py')
assets = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assets)


class EditorSaveTests(unittest.TestCase):
    def context(self, fail='', filename='test.yml'):
        ctx = quickjs.Context()
        ctx.eval('''
          var window = globalThis;
          var calls = [], outcome, failurePath = '';
          var editor = {state: {currentConfigFile: 'test.yml', unsavedChanges: true,
            undoRedo: {current: () => ({filters: {unsaved: {gain: -6}}})}},
            setState: (value) => Object.assign(editor.state, value)};
          var fetch = async (path, options) => {
            calls.push({path, body: JSON.parse(options.body)});
            return {ok: path !== failurePath, status: 500,
              text: async () => path === failurePath ? 'write failed' : 'OK'};
          };
        ''')
        ctx.eval('failurePath = ' + json.dumps(fail))
        ctx.eval('editor.state.currentConfigFile = ' + json.dumps(filename))
        ctx.eval((ROOT / 'web/dsp-editor-bridge.js').read_text())
        ctx.eval('camillaDspRegisterEditor(editor); camillaDspSaveYaml().then(x => outcome = x, e => outcome = "ERROR:" + e.message)')
        while ctx.execute_pending_job():
            pass
        return ctx

    def test_saves_unsaved_editor_then_selects_active(self):
        ctx = self.context()
        calls = json.loads(ctx.eval('JSON.stringify(calls)'))
        self.assertEqual([c['path'] for c in calls], ['/api/saveconfigfile', '/api/setactiveconfigfile'])
        self.assertEqual(calls[0]['body']['config']['filters']['unsaved']['gain'], -6)
        self.assertEqual(ctx.eval('outcome'), 'test.yml')
        self.assertFalse(ctx.eval('editor.state.unsavedChanges'))

    def test_failure_stops_sequence_and_preserves_dirty_state(self):
        for failed, count in [('/api/saveconfigfile', 1), ('/api/setactiveconfigfile', 2)]:
            ctx = self.context(fail=failed)
            self.assertTrue(ctx.eval('outcome').startswith('ERROR:'))
            self.assertEqual(ctx.eval('calls.length'), count)
            self.assertTrue(ctx.eval('editor.state.unsavedChanges'))

    def test_missing_filename_does_not_write(self):
        ctx = self.context(filename=None)
        self.assertEqual(ctx.eval('calls.length'), 0)
        self.assertTrue(ctx.eval('outcome').startswith('ERROR:'))

    def test_button_does_not_request_snapshot_when_yaml_fails(self):
        ctx = quickjs.Context()
        ctx.eval('''
          var window = globalThis, handler, posts = 0;
          var document = {getElementById: () => null, body: {append: () => {}},
            createElement: () => ({style: {}, setAttribute: () => {}, append: () => {},
              addEventListener: (name, fn) => {handler = fn;}})};
          window.location = {href: 'http://dsp/gui/index.html'};
          var URL = function() {this.port = '';};
          var setTimeout = () => 1, clearTimeout = () => {};
          window.confirm = () => true;
          window.camillaDspSaveYaml = async () => {throw new Error('disk full');};
          var fetch = async (url, options) => {
            if (options.method === 'POST') posts++;
            return {ok: true, json: async () => ({running: false, ok: null})};
          };
        ''')
        ctx.eval((ROOT / 'web/dsp-save-button.js').read_text())
        while ctx.execute_pending_job():
            pass
        ctx.eval('handler()')
        while ctx.execute_pending_job():
            pass
        self.assertEqual(ctx.eval('posts'), 0)

    def test_asset_patch_is_idempotent_and_rejects_unknown_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build = root / 'build'
            (build / 'assets').mkdir(parents=True)
            index = build / 'index.html'
            index.write_text('<script type="module" src="./assets/index.js"></script><body></body>')
            module = build / 'assets/index.js'
            original = 'class App {constructor(){' + assets.HOOK + ';}}'
            module.write_text(original)
            assets.install_assets(root, ROOT)
            first = index.read_text()
            assets.install_assets(root, ROOT)
            self.assertEqual(first, index.read_text())
            self.assertEqual(module.read_text().count('window.camillaDspRegisterEditor(this)'), 1)
            self.assertIn('dsp-editor-bridge=1', first)
            module.write_text('unknown build')
            with self.assertRaises(RuntimeError):
                assets.install_assets(root, ROOT)
            self.assertEqual(first, index.read_text())
