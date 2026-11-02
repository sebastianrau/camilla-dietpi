# Troubleshooting the DSP appliance

Start with the symptom below. Keep listening levels low while investigating audio. Collect evidence before changing several settings at once; save a working preset only after checking the result.

## A filter has no audible effect

A named filter must also be referenced by a Pipeline filter step on the channel being heard. Check that the step is enabled, apply the configuration, and verify the active file. Then check the external ADAT device's listening-output source: a dry monitoring path can conceal the processed return.

Applying, writing YAML and saving permanently are separate actions. See [the operating workflow](OPERATIONS.md#edit-a-filter-and-make-it-permanent).

## Sound is metallic, hollow or distorted

1. Temporarily reduce GUI main gain to −30 dB without saving. Watch whether the clipped-sample counter increases during playback.
2. Bypass the suspected filter step and apply. If the sound clears, inspect its settings and gain.
3. Inspect external ADAT device routing. Avoid mixing a direct/DAW signal with the delayed ADAT return, and avoid feeding the returns back into their sends.
4. Check clock/rate and logs below.

The user's “tin box” incident was resolved by correcting routing. That observation does not mean every future distortion has the same cause.

**Lenovo, root shell; IDs below are for this inspected Digiface:**

```sh
amixer -c USB24324903 cget numid=18
amixer -c USB24324903 cget numid=20
amixer -c USB24324903 cget numid=1
amixer -c USB24324903 cget numid=4
journalctl -u camilladsp -b --no-pager -n 80
```

Expected: current source `Input 1`, rate `96000`, and both input controls at enum `Sync`. A single startup underrun is different evidence from repeated underruns during playback. If warnings continue under sustained load, inspect processing load and buffer settings before drawing a latency conclusion.

## Volume resets when saving

`dsp-save` restarts the engine. The startup wrapper reapplies the configured gain, currently 0 dB on this appliance. GUI volume is not the permanent startup-gain setting. This behavior and the maintenance procedure are explained in [Operations](OPERATIONS.md#volume-mute-and-startup-gain).

## Permission denied, or systemctl cannot reach the system bus

Check the prompt and run `id -u`. Administration commands in this guide require a root shell:

```sh
sudo -i
```

If `systemctl` still fails as root, collect `ps -p 1 -o pid,comm,args` and `systemctl is-system-running`. Do not infer a broken systemd installation from an ordinary-user error alone. The remote admin account is not configured for passwordless sudo.

## SSH or the GUI is unreachable

The reserved address is `192.168.192.50`. The current GUI uses **5005**, not 80 or 443. Try the full URL <http://192.168.192.50:5005/gui/index.html>.

At the local console, inspect:

```sh
ip -br link
ip -br address
systemctl --failed --no-pager
```

Ethernet may be up with a different address after DHCP changes. In the installation recovery, repeated DHCPDECLINE messages accompanied a read-only overlay root. Check root mount state before changing DHCP or assigning a guessed static IP.

## Boot waits for ifup and no console is available

Wait for the job to time out if possible. When login becomes available, collect:

```sh
findmnt /
journalctl -b -u ifup@eth0 -u systemd-remount-fs --no-pager -n 80
```

If normal boot cannot reach a usable shell, select the maintenance entry in GRUB or use `overlayroot=disabled` on its `linux` line. See [maintenance instructions](OPERATIONS.md#enter-maintenance-mode). Avoid repeated forced power-offs while the filesystem may be writable.

## Root is ext4 rather than overlay

In a deliberate maintenance boot this is expected. In an intended protected boot inspect:

```sh
cat /proc/cmdline
cat /etc/overlayroot.local.conf
cat /run/initramfs/overlayroot.log
```

A one-boot `overlayroot=disabled` option disables protection. Otherwise use the initramfs log to diagnose failure; the package being installed does not prove the selected initrd activated it.

## Overlayroot says no filesystem driver exists

The original image included the overlay module but lacked `grep`/BusyBox. Its detection script reported no driver even though the module worked after boot. The current protection helper installs BusyBox, enables it in initramfs and includes the overlay module.

During a writable maintenance boot, verify/rebuild using the documented helper rather than repeatedly appending kernel options. Check the selected image:

```sh
lsinitramfs /boot/initrd.img-$(uname -r) | grep -E '/(busybox|grep)$|overlay\.ko|scripts/init-bottom/overlayroot'
```

The image must include the utilities, driver and startup script. Compare its name with the GRUB entry actually used.

## Root overlay is read-only and services fail

The observed symptom was `/` as overlay `ro`, followed by RAMlog, clock, networking and remount failures. The journal showed `overlay: No changes allowed in reconfigure`. The ordinary remount command was reapplying overlay creation options.

For temporary recovery **only when `/` is already an overlay**, run as root:

```sh
mount -i -n -o remount,rw overlayroot /
findmnt /
findmnt /media/root-ro
```

The overlay should become `rw`; its disk lower layer must remain `ro`. This command does not make a persistent boot fix. The current setup supplies `systemd/overlay-remount.conf`; install persistent OS changes in a maintenance boot.

Do not add standalone `rw` to the normal kernel command line. In the actual installation that also made the lower root writable. Maintenance mode intentionally uses `rw` with the overlay disabled; normal protected mode does not.

## fstab parse errors

Inspect line numbers with `nl -ba /etc/fstab`. While protected, this is overlayroot's generated file; the original disk configuration must be corrected during maintenance. DietPi's original four-field tmpfs entries needed explicit dump/check fields `0 0` for overlayroot's parser.

The protection helper normalizes those entries. After editing in maintenance mode, run `findmnt --verify --verbose` and `systemctl daemon-reload`. A successful normal boot must still be checked against the mount table in [Operations](OPERATIONS.md#verify-protection-and-startup).

## update-grub cannot resolve overlayroot

You ran it in protected mode. Changes to `/etc/default/grub` there are temporary, and GRUB's disk probing can fail against the overlay. Boot maintenance, confirm `/` is real ext4 `rw`, then repeat the intended edit and `update-grub`.

## Save button is absent or reports failure

The trial installation disappears on reboot. A new GUI bundle may also replace the injected HTML. For persistent installation, use the optional installer in maintenance mode as described in [the installation guide](DietPi_CamillaDSP_M93_Install.md#optional-save-permanently-button-in-camillagui).

Refresh the GUI, then inspect as root:

```sh
systemctl status dsp-save-web camillagui camilladsp --no-pager -l
journalctl -u dsp-save-web -b -n 50 --no-pager
findmnt /srv/dsp-store
```

The browser currently needs port 5006 as well as GUI port 5005. The updated endpoint permits GUI HTTP ports 80 and 5005. Other ports require updating origin validation. A network error during a save does not prove it failed: check status before retrying. Use `dsp-save` through SSH if the button is unavailable, and read its final result.

## Audio does not recover after USB or clock interruption

First check the card exists with `cat /proc/asound/cards`, then synchronization and the DSP journal. The service restarts an exited process but cannot detect every live-but-stalled engine. USB/clock recovery remains an acceptance test.

After restoring hardware and clock, immediate manual recovery is:

```sh
systemctl restart camilladsp
```

This reapplies the startup gain and may interrupt audio. Record the failure conditions; do not treat a manual restart as proof of automatic recovery.
