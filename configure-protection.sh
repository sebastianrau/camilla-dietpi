#!/bin/sh
# Explicit maintenance operation: prepare root protection; never reboots.
set -eu
[ "$(id -u)" -eq 0 ] || { echo 'Run as root.' >&2; exit 1; }
[ "$(findmnt -n -o FSTYPE /)" = ext4 ] || { echo 'Boot with overlayroot=disabled first.' >&2; exit 1; }
findmnt -n -o OPTIONS / | tr ',' '\n' | grep -qx rw
[ -f /boot/grub/grub.cfg ]
dpkg-query -W -f='${Status}' initramfs-tools | grep -q 'install ok installed'
for pkg in dracut dracut-core; do
    if dpkg-query -W -f='${Status}' "$pkg" 2>/dev/null | grep -q 'install ok installed'; then
        echo 'Dracut installed; inspect the boot stack first.' >&2; exit 1
    fi
done
apt install --no-install-recommends -y busybox initramfs-tools overlayroot python3
cp -a /etc/fstab /etc/fstab.before-dsp-protection
cp -a /etc/default/grub /etc/default/grub.before-dsp-protection
python3 - <<'PY'
from pathlib import Path
p = Path('/etc/fstab')
lines = []
for line in p.read_text().splitlines():
    body, sep, comment = line.partition('#')
    fields = body.split()
    if len(fields) == 4 and fields[2] == 'tmpfs':
        fields += ['0', '0']
        line = ' '.join(fields) + (' #' + comment if sep else '')
    elif fields and len(fields) not in (5, 6):
        raise SystemExit('Inspect malformed fstab line: ' + line)
    if len(fields) >= 4 and fields[1] in ('/boot', '/boot/efi'):
        opts = [x for x in fields[3].split(',') if x not in ('rw', 'ro')]
        fields[3] = ','.join(opts + ['ro'])
        line = ' '.join(fields) + (' #' + comment if sep else '')
    lines.append(line)
p.write_text('\n'.join(lines) + '\n')
p = Path('/etc/default/grub')
lines = p.read_text().splitlines()
for key, value in [('GRUB_TIMEOUT_STYLE', 'menu'), ('GRUB_TIMEOUT', '5')]:
    lines = [l for l in lines if not l.startswith(key + '=')]
    lines.append(f'{key}={value}')
# A standalone rw in the kernel command line also makes the lower disk writable.
for line in lines:
    if line.startswith(('GRUB_CMDLINE_LINUX=', 'GRUB_CMDLINE_LINUX_DEFAULT=')):
        if 'rw' in line.split('=', 1)[1].strip('\"\'').split():
            raise SystemExit('Remove standalone rw from GRUB command line, then rerun.')
p.write_text('\n'.join(lines) + '\n')
PY
printf 'BUSYBOX=y\n' > /etc/initramfs-tools/conf.d/dsp-busybox
grep -qxF overlay /etc/initramfs-tools/modules || printf '\noverlay\n' >> /etc/initramfs-tools/modules
printf 'overlayroot="tmpfs:swap=0,recurse=0"\n' > /etc/overlayroot.local.conf
mkdir -p /etc/systemd/system/systemd-remount-fs.service.d
install -m 644 "$(dirname "$0")/overlay-remount.conf" /etc/systemd/system/systemd-remount-fs.service.d/overlay.conf
# Use Debian's current-kernel links so maintenance follows kernel updates.
[ -e /vmlinuz ] && [ -e /initrd.img ] || { echo 'Missing kernel symlinks; inspect before creating maintenance entry.' >&2; exit 1; }
ROOT_UUID=$(findmnt -n -o UUID /)
[ -n "$ROOT_UUID" ]
cat > /etc/grub.d/42_dsp_maintenance <<GRUB
#!/bin/sh
exec tail -n +3 \$0
menuentry 'DietPi maintenance - writable OS' --id dietpi-maintenance {
    insmod gzio
    insmod part_gpt
    insmod part_msdos
    insmod ext2
    search --no-floppy --fs-uuid --set=root $ROOT_UUID
    linux /vmlinuz root=UUID=$ROOT_UUID rw fsck.repair=yes net.ifnames=0 overlayroot=disabled
    initrd /initrd.img
}
GRUB
chmod 755 /etc/grub.d/42_dsp_maintenance
systemctl daemon-reload
findmnt --verify
update-initramfs -u -k all
update-grub
grub-script-check /boot/grub/grub.cfg
lsinitramfs "/boot/initrd.img-$(uname -r)" | grep -E '/(busybox|grep)$|overlay\.ko|scripts/init-bottom/overlayroot'
echo 'Prepared. Inspect boot entries, then reboot manually. Verify lower root is ro.'
