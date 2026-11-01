#!/usr/bin/env python3
"""Build the installable bundle with stable ZIP metadata and an integrity manifest."""
import hashlib
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRS = ('docs', 'scripts', 'src', 'systemd', 'config', 'web', 'tests', 'tools')


def build(root=ROOT):
    paths = [root / 'README.md', root / 'requirements-dev.txt']
    for directory in SOURCE_DIRS:
        paths.extend(p for p in (root / directory).rglob('*')
                     if p.is_file() and '__pycache__' not in p.parts
                     and p.suffix not in ('.pyc', '.pyo'))
    paths.sort(key=lambda p: p.relative_to(root).as_posix())
    manifest = ''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(root).as_posix()}\n'
                       for p in paths)
    (root / 'SHA256SUMS').write_text(manifest)
    destination = root / 'dist' / 'DietPi_DSP_Setup.zip'
    destination.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in paths + [root / 'SHA256SUMS']:
            name = path.relative_to(root).as_posix()
            info = zipfile.ZipInfo(name, date_time=(2026, 11, 1, 0, 0, 0))
            info.create_system = 3
            mode = 0o755 if path.suffix == '.sh' or name in ('src/dsp-state', 'src/run-dsp') else 0o644
            info.external_attr = (0o100000 | mode) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
    return destination


if __name__ == '__main__':
    print(build())
