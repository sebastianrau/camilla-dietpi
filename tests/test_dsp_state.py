import hashlib
import importlib.machinery
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import yaml

loader = importlib.machinery.SourceFileLoader('dspstate', str((Path(__file__).resolve().parents[1] / 'src' / 'dsp-state')))
spec = importlib.util.spec_from_loader(loader.name, loader)
m = importlib.util.module_from_spec(spec)
loader.exec_module(m)


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.store = self.base / 'store'
        self.runtime = self.base / 'runtime'
        self.store.mkdir()
        (self.runtime / 'configs').mkdir(parents=True)
        (self.runtime / 'coeffs').mkdir()
        (self.runtime / 'configs' / 'test.yml').write_text('test: initial\n')
        (self.runtime / 'coeffs' / 'filter with spaces.txt').write_text('1.0\n')
        (self.runtime / 'state.yml').write_text(yaml.safe_dump({
            'config_path': str(self.runtime / 'configs' / 'test.yml')}))
        self.calls = []
        self.patches = [patch.object(m, 'STORE', self.store),
                        patch.object(m, 'RUNTIME', self.runtime),
                        patch.object(m, 'run', self.record),
                        patch.object(m.os, 'sync'),
                        patch.object(m.shutil, 'chown')]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def record(self, *args):
        self.calls.append(args)

    def test_save_restore_and_version_retention(self):
        m.save(initial=True)
        first = m.checked_archive()
        self.assertEqual(hashlib.sha256(first.read_bytes()).hexdigest(),
                         json.loads((self.store / 'active.json').read_text())['sha256'])
        import shutil
        shutil.rmtree(self.runtime)
        m.restore()
        self.assertEqual((self.runtime / 'configs' / 'test.yml').read_text(), 'test: initial\n')
        self.assertEqual((self.runtime / 'coeffs' / 'filter with spaces.txt').read_text(), '1.0\n')
        (self.runtime / 'configs' / 'test.yml').write_text('test: changed\n')
        m.save()
        self.assertNotEqual(m.checked_archive(), first)
        self.assertTrue(first.exists())
        self.assertEqual(self.calls[-1], ('mount', '-o', 'remount,ro', str(self.store)))
        self.assertFalse(any(call[0] == 'systemctl' for call in self.calls))

    def test_live_archive_uses_frozen_copy_without_service_mutations(self):
        original = m.write_snapshot
        def changed_after_capture(source):
            (self.runtime / 'configs/test.yml').write_text('test: later edit\n')
            return original(source)
        with patch.object(m, 'write_snapshot', side_effect=changed_after_capture):
            m.save()
        with tarfile.open(m.checked_archive()) as archive:
            self.assertEqual(archive.extractfile('configs/test.yml').read(), b'test: initial\n')
        self.assertFalse(any(c[0] == 'systemctl' for c in self.calls))

    def test_changing_runtime_rejected_before_store_is_writable(self):
        original = m.runtime_fingerprint
        counter = [0]
        def fingerprint(root):
            result = original(root)
            if root == self.runtime:
                counter[0] += 1
                result['changing'] = counter[0]
            return result
        with patch.object(m, 'runtime_fingerprint', side_effect=fingerprint):
            with self.assertRaisesRegex(RuntimeError, 'changed'):
                m.save()
        self.assertFalse(any(c[0] in ('mount', 'systemctl') for c in self.calls))
        self.assertFalse((self.store / 'active.json').exists())

    def test_corruption_rejected(self):
        m.save(initial=True)
        m.checked_archive().write_bytes(b'corrupt')
        with self.assertRaisesRegex(RuntimeError, 'checksum'):
            m.checked_archive()

    def test_write_failure_preserves_pointer_and_cleans_up(self):
        m.save(initial=True)
        pointer = (self.store / 'active.json').read_bytes()
        self.calls.clear()
        with patch.object(m, 'write_snapshot', side_effect=OSError('disk full')):
            with self.assertRaisesRegex(OSError, 'disk full'):
                m.save()
        self.assertEqual((self.store / 'active.json').read_bytes(), pointer)
        self.assertEqual(self.calls[-1], ('mount', '-o', 'remount,ro', str(self.store)))
        self.assertFalse(any(call[0] == 'systemctl' for call in self.calls))

    def test_unsafe_tar_rejected_before_extraction(self):
        for name, kind in [('../escape', tarfile.REGTYPE),
                           ('configs/link', tarfile.SYMTYPE)]:
            archive = self.base / 'unsafe.tar.gz'
            with tarfile.open(archive, 'w:gz') as t:
                info = tarfile.TarInfo(name)
                info.type = kind
                info.linkname = '/etc/shadow'
                t.addfile(info)
            dest = self.base / 'extracted'
            dest.mkdir(exist_ok=True)
            with self.assertRaisesRegex(RuntimeError, 'Unsafe'):
                m.extract_checked(archive, dest)
            self.assertFalse(any(dest.iterdir()))

    def test_external_active_config_rejected(self):
        (self.runtime / 'state.yml').write_text('config_path: /etc/passwd\n')
        with self.assertRaisesRegex(RuntimeError, 'inside'):
            m.check_runtime()

    def test_pointer_failure_preserves_old_active_and_returns_readonly(self):
        m.save(initial=True)
        pointer = (self.store / 'active.json').read_bytes()
        original_replace = m.os.replace
        def replace(source, dest):
            if Path(dest) == self.store / 'active.json':
                raise OSError('pointer write failed')
            return original_replace(source, dest)
        with patch.object(m.os, 'replace', side_effect=replace):
            with self.assertRaisesRegex(OSError, 'pointer write failed'):
                m.save()
        self.assertEqual((self.store / 'active.json').read_bytes(), pointer)
        self.assertFalse((self.store / 'active.json.tmp').exists())
        self.assertIn(('mount', '-o', 'remount,ro', str(self.store)), self.calls)

    def test_both_primary_and_cleanup_error_are_reported(self):
        def command(*args):
            self.calls.append(args)
            if args[:3] == ('mount', '-o', 'remount,ro'):
                raise OSError('remount failed')
        with patch.object(m, 'run', side_effect=command):
            with patch.object(m, 'write_snapshot', side_effect=OSError('disk full')):
                with self.assertRaisesRegex(RuntimeError, 'disk full.*remount failed'):
                    m.save()

    def test_snapshot_select_checks_original_sidecar(self):
        m.save(initial=True)
        first = m.checked_archive()
        (self.runtime / 'configs/test.yml').write_text('test: newer\n')
        m.save(initial=True)
        m.select_snapshot(first.name)
        self.assertEqual(m.checked_archive(), first)
        first.write_bytes(b'corrupted')
        with self.assertRaisesRegex(RuntimeError, 'checksum'):
            m.select_snapshot(first.name)

    def test_symlink_settings_rejected(self):
        (self.runtime / 'coeffs/shortcut').symlink_to('/etc/passwd')
        with self.assertRaisesRegex(RuntimeError, 'Unsupported'):
            m.check_runtime()


if __name__ == '__main__':
    unittest.main()
