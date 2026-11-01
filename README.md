# CamillaDSP on DietPi — Lenovo M93

Eight-channel 96 kHz DSP appliance using an RME Digiface USB connected over ADAT to a compatible external interface, converter or mixer. No specific external interface brand is required.

## Choose the right document

| You want to… | Read |
|---|---|
| Install a new appliance | [Installation guide](docs/DietPi_CamillaDSP_M93_Install.md) |
| Use filters, save, back up or enter maintenance | [Operating manual](docs/OPERATIONS.md) |
| Diagnose sound, boot, network or save failures | [Troubleshooting](docs/TROUBLESHOOTING.md) |
| Understand test evidence and remaining gaps | [Verification report](docs/TEST_REPORT.md) |

Start with [the installation guide](docs/DietPi_CamillaDSP_M93_Install.md). The matching [setup ZIP](dist/DietPi_DSP_Setup.zip) includes the installer, hardware configuration, snapshot tools, systemd units, root-overlay setup and optional GUI permanent-save button.

The guide records verified hardware results and remaining acceptance tests. See [TEST_REPORT.md](docs/TEST_REPORT.md) for local checks and their limits. Initial setup uses -30 dB startup gain; the guide explains changing it after commissioning.

Current appliance GUI uses HTTP port 5005. Port 80 is requested but has not been implemented. The GUI save button has been verified in a RAM-overlay trial; persistent installation is pending.

## How persistence works

Normal boot combines a read-only OS disk with a writable RAM overlay. Programs can write normally, but those OS changes disappear at reboot. DSP presets use a separate, normally read-only partition: `dsp-save` briefly stops audio, validates and archives the selected configuration, then restarts the services.

For a filter change, **apply → save YAML → select active file → save permanently**. For Linux/package changes, boot the writable maintenance entry instead. The GUI's ordinary YAML save and the permanent-save button serve different purposes.

The audio path is external ADAT device ADAT sends → Digiface capture → CamillaDSP → Digiface playback → external ADAT device ADAT returns. The documented topology uses the external ADAT device as clock master at 96 kHz. Listening to a parallel dry path as well as the return can create a hollow or metallic sound.

Personal DSP backups are excluded from version control. Do not run the initial installer over a tuned appliance as an upgrade.

## Project layout

| Folder | Contents |
|---|---|
| `docs/` | Installation guide and verification record |
| `scripts/` | Initial installation and optional feature installers |
| `src/` | Hardware configuration, snapshot management and runtime helpers |
| `systemd/` | Service units and root-remount drop-in |
| `config/` | CamillaGUI backend configuration |
| `web/` | GUI permanent-save button |
| `tests/` | Local software tests |
| `tools/` | Reproducible setup-bundle builder |
| `dist/` | Generated installation ZIP |

Installers resolve files relative to the project root, so keep the extracted directory structure intact. Run `sh scripts/install-files.sh` for a fresh installation only.

## Development

```sh
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements-dev.txt
python3 -m unittest discover -s tests -p 'test_*.py'
python3 tools/build_bundle.py
```

The builder refreshes `SHA256SUMS` and `dist/DietPi_DSP_Setup.zip`. The ZIP preserves the repository's source folders and includes the checksum manifest at its root. Verify an extracted bundle there with `sha256sum -c SHA256SUMS`.
