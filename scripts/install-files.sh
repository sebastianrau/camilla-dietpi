#!/bin/sh
# Initial installation only. Does not partition disks or enable the overlay.
set -eu
[ "$(id -u)" -eq 0 ] || { echo 'Run as root.' >&2; exit 1; }
[ "$(uname -m)" = x86_64 ] || { echo 'This bundle is for x86_64.' >&2; exit 1; }
. /etc/os-release
[ "${VERSION_CODENAME:-}" = trixie ] || { echo 'This guide targets Debian Trixie.' >&2; exit 1; }
[ "$(findmnt -n -o FSTYPE /)" != overlay ] || { echo 'Use a writable maintenance boot.' >&2; exit 1; }
for service in camilladsp camillagui; do
    if systemctl is-active --quiet "$service"; then
        echo "Stop $service before changing its installed files." >&2
        exit 1
    fi
done
src=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
apt update
apt install --no-install-recommends -y \
    alsa-utils libasound2t64 curl ca-certificates tar python3 python3-yaml \
    util-linux nano less sudo openssh-client
getent group audio >/dev/null || groupadd --system audio
if ! id dsp >/dev/null 2>&1; then
    useradd --system --no-create-home --gid audio --shell /usr/sbin/nologin dsp
fi
usermod -a -G audio dsp
mkdir -p /root/camilla-downloads /opt/camilla/bin /opt/camilla/gui /etc/camilladsp /etc/modules-load.d
chmod 755 /opt/camilla /opt/camilla/bin /opt/camilla/gui /etc/camilladsp
cd /root/camilla-downloads
curl -fL https://github.com/HEnquist/camilladsp/releases/download/v4.1.3/camilladsp-linux-amd64.tar.gz -o camilladsp-linux-amd64.tar.gz
printf '%s\n' '55f5ec2ed80fcc79a543672f9f89ace4557d290d80584ef31ee0442111bd0b11  camilladsp-linux-amd64.tar.gz' | sha256sum -c -
tar -xzf camilladsp-linux-amd64.tar.gz -C /opt/camilla/bin
chmod 755 /opt/camilla/bin/camilladsp
curl -fL https://github.com/HEnquist/camillagui-backend/releases/download/v4.1.0/bundle_linux_amd64.tar.gz -o bundle_linux_amd64.tar.gz
printf '%s\n' '86fd3cde575038f312ede7bad0910dc5e46b974cafc048c26115ec3cb9f54792  bundle_linux_amd64.tar.gz' | sha256sum -c -
tar -xzf bundle_linux_amd64.tar.gz -C /opt/camilla/gui
/opt/camilla/bin/camilladsp --version
/opt/camilla/gui/camillagui_backend/camillagui_backend --help
install -m 755 "$src/src/dsp-state" /usr/local/sbin/dsp-state
install -m 755 "$src/src/configure-dsp.py" /usr/local/sbin/configure-dsp
install -m 755 "$src/src/run-dsp" /opt/camilla/bin/run-dsp
cat > /usr/local/sbin/dsp-save <<'EOF'
#!/bin/sh
exec /usr/local/sbin/dsp-state save
EOF
chmod 755 /usr/local/sbin/dsp-save
for unit in dsp-settings.service camilladsp.service camillagui.service; do
    install -m 644 "$src/systemd/$unit" "/etc/systemd/system/$unit"
done
if [ ! -f /etc/camilladsp/gui.yml ]; then
    install -m 644 "$src/config/gui.yml" /etc/camilladsp/gui.yml
fi
printf '%s\n' snd-usb-audio > /etc/modules-load.d/camilladsp.conf
modprobe snd-usb-audio
systemctl daemon-reload
echo 'Files installed. Services and root overlay have NOT been enabled.'
echo 'Continue with the settings volume, hardware configuration and first snapshot steps in the guide.'
