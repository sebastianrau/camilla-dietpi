# Using and maintaining the DSP appliance

This is the operating manual for the installed Lenovo. For a fresh installation, use [the installation guide](DietPi_CamillaDSP_M93_Install.md). For faults, use [troubleshooting](TROUBLESHOOTING.md).

## Current access and installation status

| Item | Current value |
|---|---|
| Router reservation | `192.168.192.50` |
| CamillaGUI | <http://192.168.192.50/gui/index.html> |
| host PC SSH command | `ssh -i ~/.ssh/dsp_admin_ed25519 admin@192.168.192.50` |
| Permanent-save endpoint | HTTP port `5006`, used by the GUI button |
| Startup main gain | `0 dB` on this appliance; fresh setup defaults to `−30 dB` |
| Normal boot | Protected OS with temporary writes in RAM |
| Maintenance boot | Real root disk writable, selected from GRUB |

Port 80, the combined-save editor bridge and the restart-free snapshot helper survived the protected reboot on 2 November. Before reboot the user confirmed a save without audible interruption. After reboot, the save endpoint was ready, DSP reported RUNNING at 96 kHz with zero clipped samples, and protected mounts were correct. The user subsequently confirmed the combined save also worked without interruption in protected mode.

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
5. Choose a YAML filename in the GUI once if this configuration has no filename. With the updated integration, **Save permanently** writes the current editor to that file and selects it as active before requesting a snapshot. It includes unapplied editor changes and applies them through the GUI API without restarting the service.
6. For the SSH fallback or the older button, first save the YAML and select it as active manually, then run `dsp-save` in a root SSH shell.
7. Wait for success, then confirm audio resumes. Reboot once after a significant change to check that the intended filter returns.

These actions have different effects:

| Action | Effect |
|---|---|
| Apply | Changes the running engine |
| Save YAML | Writes the configuration file into RAM |
| Select active file | Chooses the file the snapshot/startup workflow uses |
| Updated Save permanently button | Saves editor YAML, selects it as active, then requests a snapshot |
| SSH `dsp-save` or original button | Archives already-saved files, state and coefficients to DSPSTORE |

Saving no longer stops DSP or GUI. The helper copies the archived files into a private RAM directory and compares file hashes before and after copying and validation. If concurrent edits prevent a stable capture, it retries up to three times and reports failure rather than silently saving inconsistent files. It validates the copied selected YAML, then writes only the frozen copy to DSPSTORE with the same checksum and pointer protections as before.

Do not change configuration files or upload coefficients while saving. Staging needs extra RAM roughly proportional to the settings and coefficient files, and compression/validation use CPU. Large FIR collections should be tested under actual load; leaving the process running does not by itself prove zero underruns. Current running state comes from the runtime state file captured with the other files. Main startup gain remains overridden only on a later engine start.

The button's success message means the command completed. Confirm audio and filter behavior separately; a saved valid file does not prove correct routing or acceptable sound.

## Volume, mute and startup gain

The GUI volume changes the running DSP immediately. Saving now leaves that volume unchanged. Every DSP start overrides main gain using `STARTUP_GAIN_DB` in `/etc/default/camilladsp-hardware`. A service restart or reboot resets main volume to that configured value; the updated save action does not. Saved mute state is retained, so the DSP can return muted.

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

- Test physically disconnected-network boot and USB/external-device/ADAT clock loss and recovery.
- Test sustained DSP load and clipping with actual filters.
- Make an offline disk image before AC-loss/recovery testing.
- Review the kernel update notice in maintenance mode and verify the maintenance entry still loads a valid kernel/initrd afterward.
