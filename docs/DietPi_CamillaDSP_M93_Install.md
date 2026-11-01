# DietPi DSP on Lenovo M93 — reviewed installation procedure

Revision 3 • 1 November 2026

This revision incorporates the M93 installation and protected-boot fixes verified on 1 November 2026. It replaces the earlier procedure. It closes missing account/package/file-creation steps, removes guessed audio settings, improves save failure handling, and supplies the application scripts as files in **`DietPi_DSP_Setup.zip`**. Read this guide and use the matching revision-3 ZIP together.

## What you will build

**Scarlett 18i20 3rd Gen ⇄ ADAT ⇄ Digiface USB ⇄ Lenovo M93 running CamillaDSP.** Eight channels each way at 96 kHz use four optical cables. The Scarlett is the clock master; the Digiface follows Optical Input 1.

| Component | Selected configuration |
|---|---|
| Computer | Your Lenovo M93/M93p, preferably at least 4 GB RAM |
| OS | DietPi Native PC x86-64, Debian 13 Trixie |
| Services | systemd |
| DSP / GUI | CamillaDSP 4.1.3 / CamillaGUI 4.1.0 |
| Audio | ALSA directly; no desktop, PipeWire or JACK |
| OS protection | `overlayroot`, writable upper layer in RAM |
| Saved DSP settings | Separate 1 GiB ext4 partition, normally read-only |
| Runtime DSP settings | `/run/camilladsp`, in RAM |
| Permanent DSP save | `sudo dsp-save`; briefly interrupts audio |
| OS/app changes | One writable maintenance boot, then normal reboot |

Normal operation is intended to tolerate loss of mains. **Keep power on during installation, partitioning, saves, firmware work and updates.** BIOS “Power On after AC loss” starts the PC; the services start DSP automatically. There is no hardware bypass or speaker-protection limiter in this procedure.

### What has and has not been tested

The helper scripts have local software tests. The release checksums, GUI command-line startup, DSP config schema and service syntax were checked. Mount operations, systemd service lifecycle and the physical audio device are not available in that test environment: tests substitute those operations. The user has now verified M93 installation, eight independent channels at 96 kHz, external clock sync, protected startup, RAM-only OS changes, DSP save under protection, and backup to the Mac. USB/clock recovery, sustained load and power-loss acceptance tests remain open. See the installation record below; this is not full commissioning.

### Files and terminology

Download this guide and the matching `DietPi_DSP_Setup.zip` to your Mac. In the repository the ZIP is under `dist/`; standalone downloads may be copied from their actual download location. Preserve the folders when extracting the ZIP. The ZIP contains:

| File (inside its source folder) | Purpose |
|---|---|
| `install-files.sh` | Installs required packages, verified release binaries, helper files and units; does not partition or activate protection |
| `configure-dsp.py` | Prompts for actual ALSA card, stream parameters and clock selector; creates initial config |
| `dsp-state` / `run-dsp` | Snapshot management / hardware and engine startup |
| Three `.service` files | Settings restore, DSP and GUI units |
| `gui.yml` | GUI paths and local WebSocket configuration |
| `configure-protection.sh` / `overlay-remount.conf` | Explicit writable-boot protection setup and tested root-remount workaround |
| `SHA256SUMS` | Internal file-integrity checklist |
| `TEST_REPORT.md` | What was checked and remaining hardware checks |

**Commands marked “Mac” run on your Mac. All other command blocks run on the Lenovo in a root shell.** `YOUR_DSP_IP` means the Lenovo address shown on your screen/router; it cannot be known in advance. No card names or channel counts in this guide are claimed to describe hardware we have not inspected.

## 1. Prepare the installer and BIOS

Back up anything on the target disk. The DietPi installer images the whole disk and erases its contents.

The concrete default path here is **BIOS/CSM boot**, supported by this generation of ThinkCentre. If you deliberately keep UEFI-only mode, use DietPi's separate UEFI installer instructions and the matching USB-writing method; do not mix its image with the BIOS procedure.

1. On your Mac open <https://dietpi.com/> → Downloads → **Native PC for BIOS/CSM** → **Installer image**, based on **Trixie**. Do not choose the direct-write/live disk image or a Raspberry Pi image.
2. Check the download's SHA-256 against the value supplied by DietPi. On a Mac run `shasum -a 256` followed by the actual downloaded image path; the compressed image and extracted image have different hashes, so compare the same file the publisher hashes.
3. Write the BIOS/CSM installer to a spare USB stick with an image-writing tool that supports that downloaded format. DietPi documents Rufus on Windows. For a Mac, use raw image writing for the BIOS image, such as balenaEtcher; select the image and the USB stick, then flash and verify. **Do not extrapolate this to DietPi's UEFI image:** DietPi documents problems with Etcher for UEFI images.
4. Connect screen, keyboard and Ethernet to the Lenovo. Enter Setup, normally F1. Enable legacy/CSM boot for this path, disable Secure Boot if needed, allow keyboardless boot, and set AC power recovery to **Power On** rather than Last State. Labels vary by BIOS revision.
5. Use the boot menu, normally F12, and select the installer USB in the matching boot mode.
6. Follow the Clonezilla-based DietPi installer: choose the supplied image and then the **internal SSD by its size/model**. Confirm only after checking the target. Let the installer finish and shut down.
7. Remove the installer USB and boot from the internal disk.

Official installer reference: <https://dietpi.com/docs/install/>. If the available download or bootloader differs from this path, resolve that before partition changes or overlay activation.

## 2. Finish first boot and create remote access

Log in locally using DietPi's initial credentials, normally `root` / `dietpi` unless you preconfigured another password. Complete the first-run wizard, including initial updates and changed passwords. Choose a minimal installation without a desktop/media server. Let the first-run process finish fully; it resizes the original image's root filesystem.

Install the basic administration tools and create an explicit user:

```sh
apt update
apt install --no-install-recommends -y sudo openssh-client unzip nano less util-linux
adduser admin
usermod -aG sudo admin
hostnamectl set-hostname dsp
ip -br address
```

`adduser` asks for the admin password. If that account already exists, inspect `id admin` and skip its creation. Use Ethernet DHCP and reserve the shown address/MAC in your router. No guessed static address is supplied.

DietPi normally has Dropbear SSH enabled. Keep it for now; OpenSSH is optional. `openssh-client` above also provides the remote `scp` executable. On your Mac test:

```sh
ssh admin@YOUR_DSP_IP
```

In that SSH session:

```sh
sudo -i
id -u
cat /etc/os-release
uname -m
uname -r
findmnt /
```

Required: UID `0`, `VERSION_CODENAME=trixie`, architecture `x86_64`, and a real disk-backed root filesystem at this stage. Keep the local screen available.

Reboot once now, reconnect and run `sudo -i` again. This completes first boot before partitioning and brings any newly installed kernel into use. If these prerequisites differ, do not continue by guessing.

## 3. Make the DSP settings partition

DietPi's native installer copies an existing partition layout rather than offering a Debian-style custom partition screen. This is why a separate partition operation is needed. It can be performed from any suitable live environment; **GParted is the documented method here, not a software dependency of CamillaDSP**. You may reuse the installer stick by rewriting it after DietPi installation is complete.

1. Download GParted Live from <https://gparted.org/livecd.php>, verify its checksum and write it to USB.
2. Shut down DietPi with `poweroff`. Boot GParted Live from USB.
3. Select the internal disk by model/size. Find the DietPi **ext4 root partition**, and verify it is unmounted. Do not modify EFI/boot partitions or move the beginning of root.
4. Right-click root → Resize/Move. Keep **Free space preceding unchanged**. Set **Free space following** to **1024 MiB** (or greater if desired). Leave root comfortably larger than its used space; 16 GiB total root size is a practical minimum target for this appliance.
5. Apply the shrink. If root cannot be shrunk, or another partition occupies the space, inspect the layout first. Do not delete another partition or move a boot partition to force this recipe.
6. Select the new unallocated space → New → ext4 → label **DSPSTORE**, MiB alignment. Create and apply. On an MBR disk, check a free primary-partition slot exists; the common layout permits this, but not every previously modified disk will.
7. Shut down GParted, remove USB and boot DietPi. Reconnect SSH and enter `sudo -i`.

Verify the label identifies exactly one partition:

```sh
lsblk -o NAME,SIZE,MODEL,FSTYPE,LABEL,MOUNTPOINTS
blkid -t LABEL=DSPSTORE -o device
```

If there is exactly one correct ext4 entry, generate the mount entry from its actual UUID:

```sh
STORE_DEV=$(blkid -L DSPSTORE)
test -b "$STORE_DEV"
test "$(blkid -s TYPE -o value "$STORE_DEV")" = ext4
STORE_UUID=$(blkid -s UUID -o value "$STORE_DEV")
printf 'Settings partition: %s  UUID=%s\n' "$STORE_DEV" "$STORE_UUID"
mkdir -p /srv/dsp-store
```

Inspect that output. Then append the fstab entry **once**, only if `/srv/dsp-store` has no existing entry:

```sh
if grep -Eq '[[:space:]]/srv/dsp-store[[:space:]]' /etc/fstab; then
    echo 'An entry already exists. Inspect it with: nano /etc/fstab'
else
    printf 'UUID=%s /srv/dsp-store ext4 ro,noatime 0 0\n' "$STORE_UUID" >> /etc/fstab
fi
systemctl daemon-reload
mount /srv/dsp-store
findmnt /srv/dsp-store
```

Required: the correct **separate ext4 filesystem**, `ro`. It deliberately has no automatic boot-time filesystem-check pass here; any repair after an interrupted write is a maintenance/recovery operation. Do not use `nofail` to hide a missing settings volume.

## 4. Copy and install the setup bundle

On your Mac, from the folder where you downloaded the ZIP:

```sh
scp -O dist/DietPi_DSP_Setup.zip admin@YOUR_DSP_IP:/home/admin/
```

`-O` selects legacy SCP so this does not depend on a separate SFTP server in Dropbear. Use your real address in place of `YOUR_DSP_IP`.

On the Lenovo as root:

```sh
mkdir -p /root/dietpi-dsp
unzip /home/admin/DietPi_DSP_Setup.zip -d /root/dietpi-dsp
cd /root/dietpi-dsp
sha256sum -c SHA256SUMS
less scripts/install-files.sh
sh scripts/install-files.sh
```

All internal hashes must pass. The script installs the pinned DSP/GUI releases after checking their published hashes; it installs ALSA, Python YAML and required runtime/admin packages; it creates the `dsp` account; it copies the scripts and service units to their final locations. It **does not start services, partition disks, erase settings or enable the root overlay**.

Expected ending: `Files installed. Services and root overlay have NOT been enabled.` If anything fails, stop at that failure. `--version` and GUI `--help` are executed by the installer; a successful download alone is not considered an installation check.

This is an initial installation script, not an upgrade manager. Do not rerun it over a tuned appliance without a backup and a writable maintenance boot.

## 5. Configure firmware, cables and Scarlett routing

On your Mac/Windows machine, use RME's current firmware tool to enable Digiface USB **Class Compliant mode**. Then connect the Digiface directly to the Lenovo with USB.

In Focusrite Control, set your Scarlett 18i20 3rd Gen to **96 kHz, Dual ADAT and Internal clock**. Make four optical connections:

| From | To |
|---|---|
| Scarlett OUT carrying ADAT 1–4 at 96 kHz | Digiface IN 1 |
| Scarlett OUT carrying ADAT 5–8 at 96 kHz | Digiface IN 2 |
| Digiface OUT 1 | Scarlett IN for ADAT 1–4 |
| Digiface OUT 2 | Scarlett IN for ADAT 5–8 |

Use the labels/manual for the Scarlett's physical port order. In its routing, send the intended DAW playback channels to ADAT; route the ADAT returns to the intended analogue outputs. Remove a parallel dry DAW-to-monitor path. Do not route ADAT returns back into their own sends.

For commissioning, leave monitors muted and send one low-level DAW test signal at a time. RME's CC mode defaults to Internal clock, so its optical input clock must be selected on Linux, not assumed to carry over from normal Mac driver settings.

## 6. Select the actual audio parameters

Run the supplied configuration program:

```sh
configure-dsp
```

It performs these steps interactively:

1. Lists the detected ALSA cards; choose the **Digiface USB**, not Lenovo onboard audio.
2. Displays that card's USB streaming descriptor and alternate-interface choices.
3. For capture, choose a listed channel/format combination supporting **96000 Hz**. Confirm its rates.
4. Do the same for playback. The headphone pair may make playback channel count differ from capture. **There is no hardcoded 16/18 or S32_LE assumption.**
5. Lists the ALSA controls. Read the line for the clock-source selector and enter its `numid` number.
6. Displays that control's enum items. Enter the enum index labelled **Optical Input 1** and confirm it. Do not infer the index from the input's printed number.
7. Sets the clock control, writes the hardware settings and initial eight-channel pass-through YAML, and runs the real engine's schema check.

The script translates ALSA format names to CamillaDSP format names, including the different packed/padded 24-bit names. If your descriptor/control differs from the parser's supported form, it stops rather than inventing values. Capture the following and use those actual outputs to finish configuration:

```sh
cat /proc/asound/cards
cat /proc/asound/card*/stream0
amixer -c ACTUAL_CARD_ID controls
```

`ACTUAL_CARD_ID` is the card ID shown in the first output. This is the only fallback case needing hardware-specific interpretation. You cannot fully prefill audio hardware settings without those observations.

The generated files are:

| File | Role |
|---|---|
| `/etc/default/camilladsp-hardware` | Stable card ID, clock selector and fixed startup gain `-30 dB` |
| `/run/camilladsp/configs/startup.yml` | Eight-channel pass-through; unused outputs silent |
| `/run/camilladsp/state.yml` | Selected config and fader/mute state |
| `/etc/camilladsp/gui.yml` | Installed GUI paths/API settings |

**Do not reboot yet:** `/run` is RAM and no snapshot exists. If configuration was interrupted after creating the initial files, inspect them before rerunning. Only during this first, unsaved setup may you remove `/run/camilladsp` to start over; never do this to a running tuned configuration.

## 7. Prove actual audio, then make the first saved snapshot

With speakers muted, run:

```sh
setpriv --reuid=dsp --regid=audio --init-groups /opt/camilla/bin/camilladsp \
    -a 127.0.0.1 -p 1234 \
    -s /run/camilladsp/state.yml --gain=-30
```

Required: no rejected rate/channel/format errors. Schema validation alone does not prove that ALSA accepts a combination. Send a low-level signal through each of the eight DAW channels separately and verify the matching processed return. Confirm Digiface synchronization and that unused outputs are silent. Ctrl+C stops this foreground test.

No settings have been written permanently until you run:

```sh
dsp-state save --initial
cat /srv/dsp-store/active.json
findmnt /srv/dsp-store
```

Required: snapshot filename plus checksum, and settings volume returned to `ro`. `--initial` is only for this stage with services stopped; later use `dsp-save`.

Test archive restoration before enabling services. The following removes **only the temporary copy** and reloads the saved one:

```sh
rm -rf /run/camilladsp
dsp-state restore
/opt/camilla/bin/camilladsp -c /run/camilladsp/configs/startup.yml
```

Required: restored snapshot and valid config. Do not continue to automatic startup unless this works.

## 8. Enable services and test remote control

The settings restore unit intentionally refuses to overwrite a nonempty working directory. The manual test left one, so clear it once while services are still stopped:

```sh
rm -rf /run/camilladsp
systemctl daemon-reload
systemctl enable dsp-settings.service camilladsp.service camillagui.service
systemctl start dsp-settings.service
systemctl start camilladsp.service camillagui.service
systemctl status dsp-settings.service camilladsp.service camillagui.service --no-pager
```

Expected: settings unit `active (exited)`, DSP and GUI `active (running)`. Read errors with:

```sh
journalctl -u dsp-settings -u camilladsp -u camillagui -b -n 100 --no-pager
```

Open on Mac/iPhone: **`http://YOUR_DSP_IP:5005/gui/index.html`**. Confirm running status and meters. Close the browser and confirm audio continues. The WebSocket API is bound to localhost; keep GUI port 5005 on your trusted LAN, without internet port forwarding.

The DSP startup wrapper waits for the card to appear. Once it does, an invalid clock selector produces a visible error rather than silently waiting forever. It drops privileges with `setpriv`, avoiding a PAM login step that could reset the systemd real-time limits. A running process is not proof of external clock lock or valid audio.

Reboot now while the OS is still writable. Confirm all three units, selected config, GUI and audio return without login. This separates ordinary startup problems from later overlay issues.

## 9. Logging, swap and automatic maintenance

Run `dietpi-software` → Log System and select **DietPi-RAMlog mode 1**. Mode 2 periodically saves logs and is not used here. Configure journald explicitly:

```sh
mkdir -p /etc/systemd/journald.conf.d
cat > /etc/systemd/journald.conf.d/dsp.conf <<'EOF'
[Journal]
Storage=volatile
RuntimeMaxUse=32M
RuntimeKeepFree=64M
EOF
systemctl restart systemd-journald
```

Run `dietpi-drive_manager` → select the filesystem containing the DietPi swap file → Swapfile → disable/set size to zero. In `/etc/fstab`, comment any separate disk-swap entry. Then:

```sh
swapoff -a
swapon --show
```

Expected: no entries. Test this again after reboot.

Edit DietPi's actual config file:

```sh
nano /boot/dietpi.txt
```

Set the existing assignments to:

```ini
CONFIG_CHECK_DIETPI_UPDATES=0
CONFIG_CHECK_APT_UPDATES=0
```

This prevents background DietPi/APT checks; updates will be done manually in maintenance mode. It is more precise than assuming every DietPi version exposes the same menu. Do not disable NTP solely for read-only operation: time and logs should remain useful, while audio startup has no network dependency in the supplied units.

Inspect installed APT timers and disable those that exist:

```sh
for timer in apt-daily.timer apt-daily-upgrade.timer; do
    if systemctl list-unit-files "$timer" --no-legend | grep -q "$timer"; then
        systemctl disable --now "$timer"
    fi
done
systemctl list-timers --all
```

Disable any separately installed automatic-upgrade service you deliberately added. Preserve DietPi's required boot/network/RAMlog services.

## 10. Activate the root RAM overlay

### Check the actual boot stack first

```sh
dpkg-query -W -f='${Package} ${Status}\n' initramfs-tools initramfs-tools-core 2>/dev/null
dpkg-query -W -f='${Package} ${Status}\n' dracut dracut-core 2>/dev/null || true
ls -l /boot/initrd.img-*
test -f /boot/grub/grub.cfg
```

Continue only with an **initramfs-tools-generated boot image and GRUB**. If an installed Dracut stack owns the boot image, stop before changing boot files; installing a package does not make overlayroot compatible with a different generator. This guide targets the checked Trixie/initramfs-tools path.

### Prepare protection with the revision-3 helper

Run from the extracted bundle in a real, writable root boot (not an overlay):

```sh
cd /root/dietpi-dsp
sh scripts/configure-protection.sh
```

The helper does not reboot. It checks the boot stack, installs BusyBox/overlayroot, explicitly enables BusyBox in the initramfs, and includes the overlay module. On this M93, the original initramfs lacked `grep`; overlayroot consequently reported no driver even though the module was present.

It adds `0 0` to four-field tmpfs fstab entries: DietPi accepted those entries, but overlayroot marked them malformed. It backs up fstab and GRUB defaults, sets separate boot/EFI mount policies to `ro`, and sets a five-second GRUB menu. Review other data mounts separately.

It installs `/etc/systemd/system/systemd-remount-fs.service.d/overlay.conf`. On the checked single-root M93 layout, systemd's ordinary remount reapplied overlay creation options and failed with `No changes allowed in reconfigure`, leaving `/` read-only and breaking services including DHCP. The workaround remounts the overlay explicitly with `mount -i -n -o remount,rw overlayroot /`; in non-overlay maintenance mode it runs the ordinary systemd helper. Reassess this workaround if adding separate `/usr` or other early mounts.

The overlay configuration is:

```ini
overlayroot="tmpfs:swap=0,recurse=0"
```

`recurse=0` leaves DSPSTORE as a real separate ext4 volume. **Do not add `rw` to the normal GRUB kernel command line.** In the hardware installation it made the lower disk root writable. Keep normal boot's `ro`; the service workaround makes only the RAM overlay writable.

The helper adds **DietPi maintenance - writable OS** through `/etc/grub.d/42_dsp_maintenance`, using Debian's `/vmlinuz` and `/initrd.img` links so it follows kernel updates. It requires those links to exist. Protected boot remains the default with the existing `GRUB_DEFAULT=0`; check this setting if your GRUB policy differs. If an older manual maintenance entry exists in `40_custom`, remove that entry in maintenance mode to avoid duplicates.

The helper rebuilds initramfs and GRUB. Confirm its listing includes BusyBox, grep, overlay.ko and the overlayroot startup script. Verify the selected normal GRUB entry loads the rebuilt kernel/initrd:

```sh
grep -E '^[[:space:]]*(linux|initrd)' /boot/grub/grub.cfg | head -12
cat /etc/overlayroot.local.conf
findmnt -o TARGET,SOURCE,FSTYPE,OPTIONS
```

Separate boot/EFI mounts must be writable during boot-file updates if they hold affected files. In the observed layout `/boot` lives on root and `/boot/efi` is separate; rebuilding the root-resident GRUB configuration did not require changing EFI files. After any boot maintenance, return separate boot/EFI mounts to `ro`.

Reboot with a screen and keyboard still attached. If boot fails, edit the GRUB entry with **e**, append **`overlayroot=disabled`** to its `linux` line and boot with Ctrl+X/F10. This is a one-boot recovery override, not a permanent configuration change.

## 11. Prove read-only operation and persistence

After the protected boot:

```sh
findmnt /
findmnt /media/root-ro
findmnt /srv/dsp-store
findmnt -o TARGET,SOURCE,FSTYPE,OPTIONS
swapon --show
```

Required:

- `/` is overlay. It appears writable because applications write to RAM.
- Its lower disk root, normally `/media/root-ro`, is `ro`.
- Its upper layer is tmpfs/RAM.
- `/srv/dsp-store` is separate ext4 and `ro`, not another overlay.
- Separate boot/data partitions have no unintended `rw` mounts, and disk swap is absent.

Test an unsaved OS change:

```sh
touch /etc/dsp-overlay-test
reboot
```

The file must disappear, while SSH and automatic DSP startup still work.

Then make a small identifiable change in the GUI, **save its YAML file, select that file as active**, run `dsp-save` and reboot. The change must return. This specifically proves saving works after root protection is active.

## 12. Daily use: adjust, apply, save

1. Open CamillaGUI and edit filters/routing.
2. Apply the change to hear it.
3. Save the configuration to a named YAML file in the GUI's config directory. Select that file as active. Applying alone does not save a file.
4. Keep referenced FIR files in the configured coefficients directory. Relative paths such as `../coeffs/filter.wav` are resolved from the config directory; absolute paths must remain under `/run/camilladsp/coeffs` for this appliance.
5. In SSH run `sudo dsp-save` (or `dsp-save` inside a root shell).
6. Wait for completion and check that DSP has resumed and `/srv/dsp-store` is `ro`.

`dsp-save` stops GUI and DSP briefly, validates the selected file, writes a versioned archive and checksum, switches the active pointer, remounts read-only and restarts the services. A failure reports an error and attempts cleanup. It **does not** commit OS changes, application files or arbitrary RAM contents. It requires the supplied settings-restore unit and both application services to be active; fix a failed service before saving normally.

Volume and mute changes affect the running engine immediately. Snapshots include fader/mute state. On startup **main gain is deliberately overridden by `STARTUP_GAIN_DB=-30`**, while saved mute state is retained: if you saved muted, it can boot muted. `dsp-save` restarts the engine, so it also resets main volume to the fixed startup gain. To use 0 dB permanently, mute monitors, boot maintenance mode, confirm real root is writable, and edit `/etc/default/camilladsp-hardware` to set `STARTUP_GAIN_DB=0`. Reboot normally and verify gain. This is a 30 dB increase from commissioning gain; check gain structure and clipping. Fresh configurations deliberately retain the safer -30 dB commissioning default.

### Optional: Save permanently button in CamillaGUI

The setup bundle includes `install-gui-save.sh`, `dsp-save-button.js`, `dsp-save-web.py`, and `dsp-save-web.service`. This is a local extension of the pinned GUI, not an upstream CamillaGUI feature.

**Current appliance status:** the button was installed and tested in the RAM overlay. The user confirmed it works; its status endpoint reported successful snapshot `dsp-20261101-183504-ed93b920.tar.gz` and a read-only settings partition. **Persistent button installation is still pending:** the trial files and enabled unit disappear on reboot, while the saved DSP snapshot remains on DSPSTORE.

For an optional protected-mode trial, extract the current ZIP and run as root:

```sh
sh scripts/install-gui-save.sh --trial
```

For permanent installation, boot **DietPi maintenance - writable OS**, enter a root shell, and confirm `/` is real ext4 `rw`. Transfer/extract the current ZIP again after entering maintenance: files copied into the previous RAM overlay do not survive reboot. From the extracted current bundle, run:

```sh
cd /root/dietpi-dsp
sh scripts/install-gui-save.sh
```

The installer checks for exactly one frontend `build/index.html`, backs it up, inserts an external script, and enables a separate fixed-action save service. It does not run a save. If frontend discovery fails, inspect the installed bundle rather than guessing a path. Reboot normally, check protected mounts, and refresh the browser (hard refresh if needed).

The bottom-right **Save permanently** button prompts before running the existing `dsp-save`. First save the YAML in the GUI and select it as active. Unsaved editor changes are not included. Audio pauses and startup gain is reapplied exactly as with the SSH command. The button reports success only after `dsp-save` completes. Do not repeatedly click if connection status is uncertain; inspect the service logs.

The save service runs independently of CamillaGUI so stopping the GUI during a snapshot does not kill the save operation. Its API is plain HTTP on port **5006**, alongside GUI port 5005. Both must remain on the trusted LAN without internet forwarding. There is no additional login: LAN GUI users can trigger saves. Browser requests must come from the GUI's matching hostname on port 5005; foreign/missing origins and arbitrary command parameters are rejected. This browser-origin check is not authentication against other LAN clients. Duplicate saves are rejected while one is running.

Diagnostics:

```sh
systemctl status dsp-save-web --no-pager -l
journalctl -u dsp-save-web -b -n 50 --no-pager
```

A GUI bundle replacement can remove the injected button; rerun the installer in maintenance mode after confirming compatibility. To remove the extension, in maintenance mode disable `dsp-save-web.service` and remove the `<script src="dsp-save-button.js"></script>` tag from the installed GUI `build/index.html`.

## 13. OS or application maintenance

Do not run an upgrade in normal overlay mode and assume it persists.

1. Reboot and select **DietPi maintenance - writable OS**.
2. If the entry is unavailable, edit the normal entry with **e**, append `overlayroot=disabled` to the `linux` line, then boot with Ctrl+X/F10. The next ordinary boot remains protected.
3. Verify `findmnt /` shows the real disk filesystem. Run `mount -o remount,rw /` if necessary.
4. Make the intended Linux/package/service changes. For kernel/bootloader work, temporarily remount any separate boot/EFI mount `rw` too.
5. Finish updates and rebuild initramfs/GRUB if required. Keep the local overlay config enabled for normal boots.
6. Reboot normally and verify the protections again.

The small DSP settings partition remains independent; OS updates should not erase it. Keep an offline disk image before major changes. Do not modify the mounted overlay's lower root directly as a shortcut to saving.

## 14. Backups, snapshot selection and recovery

Create a settings backup on the Lenovo:

```sh
tar -C /srv/dsp-store -czf /home/admin/dsp-settings-backup.tar.gz active.json snapshots
chown admin:admin /home/admin/dsp-settings-backup.tar.gz
chmod 600 /home/admin/dsp-settings-backup.tar.gz
```

On your Mac:

```sh
scp -O admin@YOUR_DSP_IP:/home/admin/dsp-settings-backup.tar.gz .
```

Copying it off the Lenovo is what makes this backup durable; `/home` is also covered by the RAM overlay. Take a complete **offline disk image** as well, because a settings archive cannot restore the OS or bootloader.

List retained snapshots and free space:

```sh
sudo dsp-state list
df -h /srv/dsp-store
```

To select a known-good older snapshot, stop audio and choose its exact filename from that listing:

```sh
systemctl stop camillagui camilladsp
dsp-state select --snapshot EXACT_FILENAME_FROM_THE_LIST.tar.gz
reboot
```

This command checks the archive against its saved sidecar checksum, updates the pointer, returns the volume to read-only, and selects it for the next boot. It does not pretend to restore the running RAM copy in place. If selection fails, inspect the error before rebooting; you can restart the two services to resume the current RAM config.

Snapshots are not automatically pruned. Export older ones before removing them in an explicit writable settings-volume session; preserve the active archive, its `.json` sidecar and at least one older tested pair. Large FIR coefficients can fill 1 GiB quickly.

If root boot breaks, use the one-boot GRUB override from section 10. If boot files or the disk are damaged, restore your offline disk image. After any interrupted settings write, check/repair that ext4 partition **unmounted from a live environment** before trusting it.

## 15. Acceptance checklist

Do not mark the appliance commissioned until these pass:

| Test | Pass condition |
|---|---|
| Eight independent channels at 96 kHz | Correct returns, no accidental dry/double/feedback path |
| Normal reboot | Saved preset, GUI and DSP return without login/browser |
| Protected reboot | Root lower disk and settings/boot volumes are read-only |
| Unsaved OS change | Disappears after reboot |
| DSP save after protection | Survives reboot; settings partition returns to RO |
| No internet, then no Ethernet | Audio starts from local files; no browser/network dependency |
| AC removal/restoration during normal RO operation | Lenovo powers on and audio returns |
| Digiface absent at boot, connected later | Device detected and configured |
| USB disconnect/reconnect | Audio recovers or a concrete recovery gap is identified |
| Scarlett off at boot, later on | External clock and 96 kHz audio recover |
| ADAT clock lost/restored | No lasting stall or wrong clock source |
| Sustained actual DSP load | No persistent underruns/clipping at chosen buffer |

The supplied systemd policy restarts an exited process. It cannot guarantee recovery if the engine remains alive but stalled. If the real USB/clock tests show that behaviour, add a status-aware watchdog and test it; do not mistake silence for a failure or claim that syntax checks prove recovery. Immediate manual recovery is `sudo systemctl restart camilladsp`.

Commission at 512-sample chunks; then try 256 and 128. At 96 kHz 256 samples last 2.67 ms, but total round-trip latency also contains USB/device buffering and filter delay. Measure it rather than reporting block duration as latency.

## Observed M93 installation record — 1 November 2026

- DietPi 10.8.2, Debian 13 Trixie, kernel `6.12.113+deb13-amd64`; actual installed boot is **UEFI + GRUB**, despite the original BIOS default instructions. Do not reinstall to change a working boot mode.
- Samsung 238.5 GiB SSD: `/dev/sda1` EFI, `/dev/sda2` root, `/dev/sda3` 1 GiB ext4 DSPSTORE. Labels/UUIDs in this record are observations, not portable defaults.
- Digiface ID `USB24324903`: 16 capture / 18 playback channels, `S32_LE` at 96000 Hz. Sync Source numid 17, enum 1 (`Input 1`); actual source Input 1, current rate 96000, Input 1 and Input 2 both Sync.
- Eight individual channels passed; DSP/GUI restart automatically. A saved filter remained after service restart; protected saving succeeded. Confirm saved-filter return after reboot as a separate acceptance observation if not already done.
- Final verified normal mounts: `/` overlay rw, `/media/root-ro` ext4 ro, `/media/root-rw` tmpfs, DSPSTORE/EFI ro, no swap and no failed units.
- An unsaved `/etc` file disappeared across reboot. Startup gain changed permanently to **0 dB**. Settings archive copied to Mac.
- The IP is reserved in the router at **192.168.192.50**. CamillaGUI: **http://192.168.192.50:5005/gui/index.html**. Earlier DHCP addresses in the recovery conversation are obsolete.
- Audio started during a network timeout. Physically disconnected-network boot is still a separate test.
- Open: disconnected-network boot, USB/device/clock recovery, sustained load, offline disk image, AC recovery, and review of the machine's kernel update notice in maintenance mode. Maintenance-menu selection itself still needs an explicit verification.

## Audit changes and sources

Revision 2 fixes these specific omissions in the earlier guide:

- Explicit first login, `admin` account, sudo and SCP setup.
- Required editors/unzip/runtime packages and executable permissions.
- A matched setup ZIP instead of ambiguous “create this file” instructions.
- Interactive real ALSA parameters instead of guessed channel counts/formats.
- Clock waiting separated from invalid-selector errors.
- Actual DietPi update keys and a read-only settings-volume check.
- Per-snapshot integrity records, directory flushes and improved failure reporting.
- A checked rollback command and a complete off-machine backup procedure.
- Clearer service-restore sequencing and the saved-mute/startup-gain behaviour.
- Explicit limits on test evidence: no physical boot/audio claims.

Project references used during review:

- DietPi installer: <https://dietpi.com/docs/install/>
- DietPi runtime/settings keys: <https://dietpi.com/docs/usage/> and <https://github.com/MichaIng/DietPi/blob/master/dietpi.txt>
- DietPi RAMlog: <https://dietpi.com/docs/software/log_system/>
- Overlay integration status: <https://github.com/MichaIng/DietPi/issues/8298>
- Overlayroot package/source: <https://packages.debian.org/trixie/overlayroot>
- GParted manual: <https://gparted.org/display-doc.php?name=help-manual>
- CamillaDSP release: <https://github.com/HEnquist/camilladsp/releases/tag/v4.1.3>
- ALSA format mapping: <https://github.com/HEnquist/camilladsp/blob/v4.1.3/backend_alsa.md>
- CamillaGUI release: <https://github.com/HEnquist/camillagui-backend/releases/tag/v4.1.0>
- RME clock control/manual: <https://rme-audio.de/downloads/dface_usb_e.pdf>
- Scarlett optical I/O: <https://userguides.focusrite.com/hc/en-gb/articles/23031280130706-Scarlett-18i20-3rd-Gen-hardware-features>
