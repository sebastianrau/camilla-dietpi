# Revision 3 verification record

Updated: 1 November 2026. Original revision-2 software checks: 24 October 2026.

## Historical revision-2 checks

- 9 snapshot tests: archive save/restore; retained versions; corruption rejection; write-failure cleanup; unsafe paths/links; invalid active-config location; failed active-pointer update; combined primary/cleanup errors; snapshot selection against original checksum metadata.
- 2 ALSA descriptor tests: multiple alternate interfaces with different capture/playback counts; packed versus padded 24-bit format mapping.
- Actual CamillaDSP 4.1.3 schema validation of the initial 16/18-channel test fixture. Those fixture counts are test data, not prescribed Digiface parameters.
- Actual CamillaGUI 4.1.0 bundle talking to the actual CamillaDSP 4.1.3 binary over localhost. Browser HTML served; status reported RUNNING; 16 capture and 18 playback meter entries; selected-config API returned the expected filename. The engine used /dev/zero to /dev/null file backends for this protocol check, not physical audio.
- The two downloaded release archives matched the SHA-256 values in install-files.sh.
- 30 shell blocks in the guide and both shell scripts parsed without warnings.
- systemd-analyze verified all three units after installed executable paths were mapped to local fixtures. This checks unit syntax and basic dependencies, not a real appliance boot.
- This ZIP was extracted and its internal checksums and included unit tests were rerun.

## Test limitations

Snapshot tests use real temporary directories, tar archives, hashes and state files. They replace mount commands, systemctl calls, ownership changes and global sync with controlled substitutes. They do not prove that a partition was remounted or that a hardware service restarted.

Original revision-2 tests did not exercise hardware. On 1 November 2026 the user supplied real M93 installation evidence: UEFI/GRUB boot, resized disk and DSPSTORE, 16/18 S32_LE at 96 kHz, ADAT synchronization and eight-channel routing, protected mounts, RAM change loss across reboot, service startup, protected DSP save, 0 dB startup gain and off-machine settings backup. Network startup recovered after the explicit overlay remount workaround. Full recovery/load/power-loss tests remain unverified. The new protection helper packages these manual fixes; it has syntax checks but has not itself been executed end-to-end on the appliance.

## Reproduce included unit tests

After the install script has supplied python3 and python3-yaml, from the extracted setup folder:

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
```

The tests do not partition disks or invoke real mount/systemctl mutations. They must still be run as ordinary local software tests rather than treated as proof of appliance commissioning.

## Revision-3 local checks (1 November 2026)

- Shell syntax checked for the new protection helper; embedded Python and project Python sources parsed successfully.
- An early local unit-test attempt was blocked because the Mac Python lacked PyYAML. This was later resolved with an isolated test environment; the complete 14-test pass is recorded below.
- Fresh commissioning still uses -30 dB; the installed user's 0 dB setting is documented rather than forced onto new hardware.
- Installer does not activate protection automatically. The explicit helper requires a real writable ext4 root and an initramfs-tools/GRUB boot stack.

## GUI permanent-save extension

Two local tests pass: concurrent saves are rejected and command failures reach status; a real loopback HTTP server rejects missing/foreign browser origins and arbitrary command parameters, and accepts the fixed save action. The actual privileged save command is mocked in these tests. Shell/Python syntax is checked. Appliance trial subsequently verified at reserved IP 192.168.192.50: frontend path `_internal/build/index.html`, injected script served through the GUI, status endpoint reported successful snapshot `dsp-20261101-183504-ed93b920.tar.gz` and read-only config volume. User confirmed button operation. Persistent installation and survival of the button across reboot remain pending.

## Repository restructuring verification — 1 November 2026

Sources now live under `src/`, installers under `scripts/`, units under `systemd/`, configuration under `config/`, browser assets under `web/`, and documentation under `docs/`. Tests resolve sources relative to the repository root.

All 14 local tests pass with PyYAML 6.0.3 in an isolated environment, including snapshot/descriptor tests, HTTP origin checks, and deterministic bundle construction with complete checksum coverage. Shell syntax checks pass for all shell installers and the runtime wrapper. `tools/build_bundle.py` rebuilds the ZIP under `dist/` and its root manifest. These checks do not execute privileged installers on the appliance.
