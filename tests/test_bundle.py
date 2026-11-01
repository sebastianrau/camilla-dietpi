import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('bundle', ROOT / 'tools' / 'build_bundle.py')
bundle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bundle)


class BundleTests(unittest.TestCase):
    def test_reproducible_archive_has_complete_manifest_and_install_sources(self):
        # Build in isolation so tests do not alter the release artifact.
        import shutil
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in bundle.SOURCE_DIRS:
                shutil.copytree(ROOT / name, root / name, ignore=shutil.ignore_patterns('__pycache__'))
            for name in ('README.md', 'requirements-dev.txt'):
                shutil.copyfile(ROOT / name, root / name)
            path = bundle.build(root)
            first = path.read_bytes()
            self.assertEqual(first, bundle.build(root).read_bytes())
            with zipfile.ZipFile(path) as archive:
                entries = archive.namelist()
                checks = archive.read('SHA256SUMS').decode().splitlines()
                self.assertEqual(len(checks), len(entries) - 1)
                for line in checks:
                    digest, name = line.split('  ', 1)
                    self.assertEqual(digest, hashlib.sha256(archive.read(name)).hexdigest())
                for name in ('scripts/install-files.sh', 'src/dsp-state', 'config/gui.yml',
                             'systemd/overlay-remount.conf', 'web/dsp-save-button.js'):
                    self.assertIn(name, entries)
                self.assertFalse(any('backup' in name or '.git/' in name for name in entries))
