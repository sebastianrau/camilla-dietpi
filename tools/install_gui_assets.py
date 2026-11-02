#!/usr/bin/env python3
"""Install pinned GUI editor bridge, refusing unknown frontend layouts."""
from pathlib import Path
import shutil
import sys

HOOK = 'this.saveAndApplyConfig=this.saveAndApplyConfig.bind(this)'
PATCHED = HOOK + ',window.camillaDspRegisterEditor(this)'


def install_assets(root, source):
    choices = [p for p in root.rglob('index.html') if p.parent.name == 'build']
    if len(choices) != 1:
        raise RuntimeError(f'Expected one build/index.html; found {choices}')
    index = choices[0]
    text = index.read_text()
    candidates = []
    for asset in (index.parent / 'assets').glob('*.js'):
        content = asset.read_text()
        if HOOK in content:
            candidates.append((asset, content))
    if len(candidates) != 1 or candidates[0][1].count(HOOK) != 1:
        raise RuntimeError('Unsupported GUI build: expected one editor constructor hook. No assets changed.')
    if '</body>' not in text:
        raise RuntimeError('GUI has no closing body tag')
    asset, content = candidates[0]
    # Keep first-install originals for recovery.
    for path in (asset, index):
        backup = path.with_name(path.name + '.before-dsp-save')
        if not backup.exists():
            shutil.copy2(path, backup)
    if PATCHED not in content:
        asset.write_text(content.replace(HOOK, PATCHED))
    # Cache-bust the module after patching the same hashed upstream filename.
    import re
    text = re.sub(r'(src="\./assets/' + re.escape(asset.name) + r')(?:\?[^" ]*)?"',
                  r'\1?dsp-editor-bridge=1"', text)
    for name in ('dsp-editor-bridge.js', 'dsp-save-button.js'):
        shutil.copyfile(source / 'web' / name, index.parent / name)
    # Replace the original button tag, or append both on first installation.
    for name in ('dsp-editor-bridge.js', 'dsp-save-button.js'):
        text = re.sub(r'<script src="' + re.escape(name) + r'(?:\?[^" ]*)?"></script>', '', text)
    tags = '<script src="dsp-editor-bridge.js?v=2"></script><script src="dsp-save-button.js?v=3"></script>'
    index.write_text(text.replace('</body>', tags + '</body>'))
    return index


if __name__ == '__main__':
    print('Editor save bridge installed in', install_assets(
        Path('/opt/camilla/gui/camillagui_backend'), Path(sys.argv[1])))
