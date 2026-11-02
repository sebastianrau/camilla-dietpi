#!/bin/sh
# Default: writable maintenance boot. --trial permits an overlay-only test.
set -eu
[ "$(id -u)" -eq 0 ] || { echo 'Run as root.' >&2; exit 1; }
case "${1:-}" in
    --trial)
        [ "$(findmnt -n -o FSTYPE /)" = overlay ] || { echo '--trial requires the protected overlay boot.' >&2; exit 1; }
        echo 'TRIAL: installation is in RAM and disappears after reboot.'
        ;;
    ''|--port80)
        [ "$(findmnt -n -o FSTYPE /)" = ext4 ] || { echo 'Select the GRUB maintenance entry first, or use --trial.' >&2; exit 1; }
        ;;
    *) echo 'Usage: sh install-gui-save.sh [--trial | --port80]' >&2; exit 1;;
esac
findmnt -n -o OPTIONS / | tr ',' '\n' | grep -qx rw
src=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
# Restrict discovery to this pinned bundle; refuse ambiguous frontend paths.
python3 "$src/tools/install_gui_assets.py" "$src"
install -m 755 "$src/src/dsp-save-web.py" /opt/camilla/bin/dsp-save-web.py
install -m 644 "$src/systemd/dsp-save-web.service" /etc/systemd/system/dsp-save-web.service
if [ "${1:-}" = --port80 ]; then
    python3 - <<'PYPORT'
from pathlib import Path
import shutil
import yaml
p = Path('/etc/camilladsp/gui.yml')
config = yaml.safe_load(p.read_text())
if config.get('ssl_certificate') or config.get('ssl_private_key'):
    raise SystemExit('TLS is configured; inspect before switching to plain HTTP.')
backup = p.with_name('gui.yml.before-port80')
if not backup.exists():
    shutil.copy2(p, backup)
config['port'] = 80
p.write_text(yaml.safe_dump(config, sort_keys=False))
PYPORT
    mkdir -p /etc/systemd/system/camillagui.service.d
    cat > /etc/systemd/system/camillagui.service.d/port80.conf <<'PORTUNIT'
[Service]
AmbientCapabilities=CAP_NET_BIND_SERVICE
CapabilityBoundingSet=CAP_NET_BIND_SERVICE
NoNewPrivileges=true
PORTUNIT
fi
systemctl daemon-reload
systemctl enable dsp-save-web.service
systemctl restart dsp-save-web.service
if [ "${1:-}" = --port80 ]; then
    systemctl restart camillagui.service
    echo 'GUI HTTP port is now 80. Open http://YOUR_DSP_IP/gui/index.html'
fi
echo 'Installed. Refresh CamillaGUI. Port 5006 must be reachable only on the trusted LAN, like the GUI port.'
if [ "${1:-}" = --trial ]; then
    echo 'Test now without rebooting. Saved DSP snapshots persist; the button installation does not.'
else
    echo 'Reboot normally and verify protected mounts before testing a permanent save.'
fi
