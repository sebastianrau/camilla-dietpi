# CamillaDSP on DietPi — Lenovo M93

Eight-channel 96 kHz DSP appliance using an RME Digiface USB and Scarlett 18i20 3rd Gen over ADAT.

Start with [the installation guide](DietPi_CamillaDSP_M93_Install.md). The matching [setup ZIP](DietPi_DSP_Setup.zip) includes the installer, hardware configuration, snapshot tools, systemd units, root-overlay setup and optional GUI permanent-save button.

The guide records verified hardware results and remaining acceptance tests. See [TEST_REPORT.md](TEST_REPORT.md) for local checks and their limits. Initial setup uses -30 dB startup gain; the guide explains changing it after commissioning.

Current appliance GUI uses HTTP port 5005. Port 80 is requested but has not been implemented. The GUI save button has been verified in a RAM-overlay trial; persistent installation is pending.

Personal DSP backups are excluded from version control. Do not run the initial installer over a tuned appliance as an upgrade.
