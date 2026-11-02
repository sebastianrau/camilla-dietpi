#!/bin/sh
# Update the save helper and GUI integration, without restarting the DSP engine.
set -eu
[ "$(id -u)" -eq 0 ] || { echo 'Run as root.' >&2; exit 1; }
case "${1:-}" in
    --trial) [ "$(findmnt -n -o FSTYPE /)" = overlay ];;
    '') [ "$(findmnt -n -o FSTYPE /)" = ext4 ];;
    *) echo 'Usage: sh scripts/update-live-save.sh [--trial]' >&2; exit 1;;
esac
findmnt -n -o OPTIONS / | tr ',' '\n' | grep -qx rw
src=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
# Refuse to update a helper while a save is in progress.
exec 9>/run/dsp-state.lock
flock -n 9 || { echo 'A snapshot operation is in progress. Retry after it finishes.' >&2; exit 1; }
cp -a /usr/local/sbin/dsp-state /usr/local/sbin/dsp-state.before-live-save
install -m 755 "$src/src/dsp-state" /usr/local/sbin/dsp-state
if [ "${1:-}" = --trial ]; then
    sh "$src/scripts/install-gui-save.sh" --trial
else
    sh "$src/scripts/install-gui-save.sh"
fi
echo 'Live-save update installed. DSP was not restarted. Refresh the browser before saving.'
