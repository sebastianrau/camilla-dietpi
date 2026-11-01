#!/bin/sh
# Default: writable maintenance boot. --trial permits an overlay-only test.
set -eu
[ "$(id -u)" -eq 0 ] || { echo 'Run as root.' >&2; exit 1; }
case "${1:-}" in
    --trial)
        [ "$(findmnt -n -o FSTYPE /)" = overlay ] || { echo '--trial requires the protected overlay boot.' >&2; exit 1; }
        echo 'TRIAL: installation is in RAM and disappears after reboot.'
        ;;
    '')
        [ "$(findmnt -n -o FSTYPE /)" = ext4 ] || { echo 'Select the GRUB maintenance entry first, or use --trial.' >&2; exit 1; }
        ;;
    *) echo 'Usage: sh install-gui-save.sh [--trial]' >&2; exit 1;;
esac
findmnt -n -o OPTIONS / | tr ',' '\n' | grep -qx rw
src=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
# Restrict discovery to this pinned bundle; refuse ambiguous frontend paths.
python3 - "$src" <<'PY'
import shutil
import sys
from pathlib import Path
root = Path('/opt/camilla/gui/camillagui_backend')
choices = [p for p in root.rglob('index.html') if p.parent.name == 'build']
if len(choices) != 1:
    raise SystemExit(f'Expected one frontend build/index.html; found {choices}. Inspect paths before installing.')
index = choices[0]
text = index.read_text()
marker = '<script src="dsp-save-button.js"></script>'
if marker not in text:
    if '</body>' not in text:
        raise SystemExit('Frontend has no closing body tag')
    backup = index.with_name('index.html.before-dsp-save')
    if not backup.exists():
        shutil.copy2(index, backup)
    index.write_text(text.replace('</body>', marker + '</body>'))
shutil.copyfile(Path(sys.argv[1]) / 'web' / 'dsp-save-button.js', index.parent / 'dsp-save-button.js')
print('Save button installed in', index)
PY
install -m 755 "$src/src/dsp-save-web.py" /opt/camilla/bin/dsp-save-web.py
install -m 644 "$src/systemd/dsp-save-web.service" /etc/systemd/system/dsp-save-web.service
systemctl daemon-reload
systemctl enable --now dsp-save-web.service
echo 'Installed. Refresh CamillaGUI. Port 5006 must be reachable only on the trusted LAN, like port 5005.'
if [ "${1:-}" = --trial ]; then
    echo 'Test now without rebooting. Saved DSP snapshots persist; the button installation does not.'
else
    echo 'Reboot normally and verify protected mounts before testing a permanent save.'
fi
