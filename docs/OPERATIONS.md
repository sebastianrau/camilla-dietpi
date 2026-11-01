# Using and maintaining the DSP appliance

This is the operating manual for the installed Lenovo. For a fresh installation, use [the installation guide](DietPi_CamillaDSP_M93_Install.md). For faults, use [troubleshooting](TROUBLESHOOTING.md).

## Current access and installation status

| Item | Current value |
|---|---|
| Router reservation | `192.168.192.50` |
| CamillaGUI | <http://192.168.192.50:5005/gui/index.html> |
| host PC SSH command | `ssh -i ~/.ssh/dsp_admin_ed25519 admin@192.168.192.50` |
| Permanent-save endpoint | HTTP port `5006`, used by the GUI button |
| Startup main gain | `0 dB` on this appliance; fresh setup defaults to `−30 dB` |
| Normal boot | Protected OS with temporary writes in RAM |
| Maintenance boot | Real root disk writable, selected from GRUB |

Port 80 is requested but **not implemented**. The save button worked in a temporary RAM-overlay trial; persistent installation remains pending. A reboot removes the trial button installation. It does not remove snapshots already saved on DSPSTORE.

## Understand the audio path

Your DAW or other source sends audio through a compatible external device's ADAT outputs. The external device can be any interface, converter or mixer that meets the channel, rate and clock requirements; no specific brand is required. The Digiface receives it, CamillaDSP processes it, and the Digiface sends it back through ADAT to the external ADAT device's selected analogue outputs.

At 96 kHz, each optical connection carries four channels in this configuration. Two optical cables carry eight sends; two more carry eight returns. The external ADAT device supplies the clock, and the Digiface follows Input 1. Both connected input banks were observed synchronized at 96000 Hz.

The Digiface exposes 16 capture and 18 playback channels at this rate, even though this setup uses eight audio paths. The ALSA stream must use the hardware's complete channel count; the mixer determines which channels are used. Do not reduce ALSA channel counts to eight just because you use eight signals.

For each listening output, select the intended processed ADAT return. A simultaneous direct/DAW monitoring path can mix delayed and undelayed copies, creating hollow or metallic sound. The reported “tin box” sound on this installation was resolved by correcting routing.

## Understand what survives a reboot

| Location or change | What happens on normal reboot |
|---|---|
| Unsaved GUI edits | Lost unless written to YAML and included in a snapshot |
| YAML and coefficients under `/run/camilladsp` | Replaced with the saved snapshot |
| OS files edited in normal overlay mode | Lost; changes exist in RAM |
| Snapshot under `/srv/dsp-store` | Retained on its separate disk partition |
| OS files edited during maintenance boot | Retained on the root disk |
| Backup copied to the host PC | Retained independently of the Lenovo |

The root overlay presents a writable filesystem to applications. Its lower layer is the real SSD, mounted read-only; its upper layer is RAM. This lets programs operate normally while avoiding ordinary OS writes to the SSD. The separate settings partition is deliberately outside this overlay so a save can reach real storage.

`dsp-save` saves DSP data only. It does not preserve installed packages, GUI modifications, SSH configuration or Linux configuration changed in the overlay.

## Edit a filter and make it permanent

1. Open CamillaGUI and select the configuration you intend to edit.
2. Create or edit the filter in **Filters**.
3. Reference it in a **Filter** step in **Pipeline**, on the correct channel. A filter definition alone does not put it in the audio path.
4. Apply the configuration and listen at a controlled level. Check output meters and clipping.
5. Save the configuration to a named YAML file in the GUI, and select that file as active. Button labels may vary with the GUI view; verify the active filename.
6. Click the optional **Save permanently** button, or run `dsp-save` in a root SSH shell.
7. Wait for success, then confirm audio resumes. Reboot once after a significant change to check that the intended filter returns.

These actions have different effects:

| Action | Effect |
|---|---|
| Apply | Changes the running engine |
| Save YAML | Writes the configuration file into RAM |
| Select active file | Chooses the file the snapshot/startup workflow uses |
| Save permanently / `dsp-save` | Archives the selected file, state and coefficients to DSPSTORE |

Saving pauses audio because the helper stops the GUI and DSP to take a consistent snapshot. It validates the selected configuration, writes an archive and checksum, updates the active pointer, returns the partition to read-only, then restarts DSP and GUI. If saving fails, read the error rather than assuming settings are durable.

The button's success message means the command completed. Confirm audio and filter behavior separately; a saved valid file does not prove correct routing or acceptable sound.

## Volume, mute and startup gain

The GUI volume changes the running DSP immediately. Every DSP start overrides main gain using `STARTUP_GAIN_DB` in `/etc/default/camilladsp-hardware`. Therefore a permanent save, service restart or reboot resets the main volume to that configured value. Saved mute state is retained, so the DSP can return muted.

This appliance was changed from commissioning gain −30 dB to 0 dB. That is a 30 dB increase. A filter with positive gain can still clip at 0 dB main gain; use meters and suitable headroom rather than assuming 0 dB is always clean.

To change the fixed gain, mute the listening outputs, boot maintenance mode, confirm real root is writable, edit the existing `STARTUP_GAIN_DB` assignment and reboot normally. Do not expect `dsp-save` to preserve edits to that OS file made in protected mode.

## SSH: host PC commands and Lenovo commands

**On the host PC** (Windows, Linux or macOS), open a local terminal with an OpenSSH client available:

```sh
ssh -i ~/.ssh/dsp_admin_ed25519 admin@192.168.192.50
```

**Inside the Lenovo SSH session**, become root for administration:

```sh
sudo -i
```

A prompt beginning `admin@dsp` is an ordinary Lenovo user. `root@dsp` is the Lenovo root shell. Neither is the host PC. A command using `~/Documents` while at `root@dsp` points to `/root/Documents` on the Lenovo.

The SSH key for this Lenovo is separate from the host PC's GitHub key. Do not put either private key into this repository.

## Enter maintenance mode

1. Reboot with a local screen and keyboard available.
2. In GRUB select **DietPi maintenance - writable OS**. This starts the same OS with the overlay disabled.
3. Connect through SSH and enter `sudo -i`.
4. Run `findmnt /`. Proceed only when it shows the real disk, currently `/dev/sda2`, type `ext4`, with `rw`.
5. Make the intended OS changes. Keep power on until maintenance completes.
6. Reboot into the normal default entry and verify protection again.

If the maintenance entry is unavailable, press **e** on the normal GRUB entry. Find the line beginning `linux`, append a space and `overlayroot=disabled`, then boot with **Ctrl+X** or **F10**. Do not type this option into a shell or add it to the `initrd` line. It applies to this boot only.

An overlay root that shows `rw` is still protected mode. It is **not** a writable maintenance boot. Never edit `/media/root-ro` directly to make permanent changes.

The originally installed manual maintenance entry pins a kernel filename. The current protection helper generates a maintenance entry using `/vmlinuz` and `/initrd.img` links. Inspect the actual entry before replacing/removing kernels; avoid duplicate entries if migrating from the manual version.

## Verify protection and startup

Run as root on the Lenovo:

```sh
findmnt /
findmnt /media/root-ro
findmnt /media/root-rw
findmnt /srv/dsp-store
findmnt /boot/efi
swapon --show
systemctl --failed --no-pager
systemctl is-active dsp-settings camilladsp camillagui
```

| Check | Required normal result |
|---|---|
| `/` | `overlay`, `rw` |
| `/media/root-ro` | Real disk `ext4`, `ro` |
| `/media/root-rw` | `tmpfs`, `rw` |
| `/srv/dsp-store` | Separate `ext4`, `ro` |
| `/boot/efi` | `vfat`, `ro` on this machine |
| Swap | No output |
| Failed units | Zero |
| DSP settings, engine and GUI | Three `active` results |

These checks establish filesystem/service state. Audio, synchronization and recovery need their own tests.

## Back up settings to the host PC

**Lenovo, root shell:**

```sh
tar -C /srv/dsp-store -czf /home/admin/dsp-settings-backup.tar.gz active.json snapshots
chown admin:admin /home/admin/dsp-settings-backup.tar.gz
chmod 600 /home/admin/dsp-settings-backup.tar.gz
```

**host PC, a separate Terminal tab:**

```sh
scp -O -i ~/.ssh/dsp_admin_ed25519 admin@192.168.192.50:/home/admin/dsp-settings-backup.tar.gz ~/Documents/camilla-dsp-setup/
```

Use an existing destination directory on your host PC; `~/Documents/camilla-dsp-setup/` is an example. Windows users can substitute a quoted absolute Windows path. Copy before rebooting: `/home/admin` on the protected Lenovo is also in the RAM overlay. The host PC copy survives independently. This filename overwrites the previous local backup; rename older copies first if you want to retain multiple exports. DSPSTORE itself keeps versioned snapshots until explicitly pruned.

A settings backup restores DSP snapshots, not Debian, GRUB or installed applications. Make a complete offline disk image as a separate recovery measure. Personal backups are excluded by `.gitignore` and do not belong in the public repository.

## Remaining work

- Install the save button permanently in maintenance mode and verify it after reboot.
- Implement the requested HTTP port 80 change together with the button's origin validation; changing the GUI port alone breaks button requests.
- Test physically disconnected-network boot and USB/external-device/ADAT clock loss and recovery.
- Test sustained DSP load and clipping with actual filters.
- Make an offline disk image before AC-loss/recovery testing.
- Review the kernel update notice in maintenance mode and verify the maintenance entry still loads a valid kernel/initrd afterward.
