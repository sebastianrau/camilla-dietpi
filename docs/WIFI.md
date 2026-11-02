# Join an existing Wi-Fi network

Wi-Fi provides access to SSH and CamillaGUI. Audio still travels through USB/ADAT; it does not use Wi-Fi. The same GUI and permanent-save service work over either network interface, without changing DSP routing.

## Current hardware check — 2 November 2026

The Lenovo currently exposes `eth0` and `lo`, with no wireless network interface. PCI inspection showed only the Intel Ethernet controller; the USB inventory showed no identified Wi-Fi adapter. This does not prove every possible wireless device is absent or supported: attach the intended adapter and inspect its exact USB ID and driver.

The installed system has DietPi's `dietpi-network`, `iw` and `wpa_supplicant`. Missing entries from an ordinary user's command search can simply be an administration PATH issue. Do not install a second network manager on that evidence.

**Wi-Fi connection is not configured or tested yet.** A detected, supported adapter is the next requirement. A USB mouse labelled “2.4 GHz wireless” is not a Wi-Fi adapter.

## 1. Connect and identify the adapter

Keep Ethernet connected while inspecting hardware. Plug in the intended Wi-Fi adapter, then run as root on the Lenovo:

```sh
ip -br link
lsusb
/usr/sbin/iw dev
```

If no wireless interface appears, inspect kernel logs:

```sh
journalctl -k -b --no-pager -n 100
```

Record the adapter's USB vendor/product ID and any missing firmware or driver message. Resolve that exact requirement during maintenance; do not guess a chipset from the adapter's marketing name or install unrelated driver bundles.

## 2. Use a writable maintenance boot

Select **DietPi maintenance - writable OS** in GRUB and confirm:

```sh
findmnt /
```

Required: the real root disk, currently `/dev/sda2`, type ext4, with `rw`. Network settings changed in an ordinary protected boot would disappear on reboot. `dsp-save` does not preserve network configuration.

Keep a local screen and keyboard available during the network transition. Changing the interface carrying SSH may disconnect the session.

## 3. Configure the Wi-Fi client

Run as root:

```sh
dietpi-network
```

If the command is not on PATH, the installed script is `/boot/dietpi/dietpi-network`. The same menu is available through `dietpi-config` → **Network Options: Adapters**.

1. Enable **WiFi modules** if Wi-Fi support is disabled.
2. Select the detected wireless adapter; its name may be `wlan0` or another name. Use the actual displayed name.
3. Set the correct **Country** for the machine's location.
4. Use **Scan**, select your existing SSID and enter its password locally. Do not paste the password into chat or commit network configuration files to this repository.
5. Use **DHCP**, enable **Auto Reconnect**, and prefer **hotplug** boot mode so adapter detection does not have to complete during early boot.
6. Save the settings. Apply them when ready to test the connection.

DietPi can warn about interfaces using the same subnet or duplicate gateways. If that happens while Ethernet is connected to the same LAN, inspect the proposed settings before applying. Do not use `--force` or disable Ethernet remotely just to bypass the warning. Use the local console to perform the transition if needed.

These menus are documented in the [official DietPi network configuration guide](https://dietpi.com/docs/dietpi_tools/system_configuration/#dietpi-network). Actual labels can vary with DietPi version.

## 4. Verify the Wi-Fi address and access

On the Lenovo, substituting the actual wireless interface name:

```sh
ip -br address
/usr/sbin/iw dev
ip route
```

Confirm the adapter is associated with your SSID and has an address from your router. The Ethernet reservation `192.168.192.50` belongs to the Ethernet MAC; Wi-Fi has its own MAC and does not automatically inherit that reservation. Reserve the wireless address separately, without assigning the same IP to both active interfaces.

From the host PC, test the actual Wi-Fi address:

```sh
ssh admin@WIFI_IP
```

Open `http://WIFI_IP/gui/index.html` and verify the DSP status and button. Use the same hostname/IP for the GUI and its port-5006 save endpoint; the button derives that address from the page. The host PC must be on a network permitted to reach the Lenovo. Guest isolation can prevent access even when both devices have Wi-Fi.

Before disconnecting Ethernet, verify the wireless association and Wi-Fi address from the local console. A successful web request while Ethernet is still attached is not sufficient proof of wireless-only reachability. Disconnect Ethernet under local supervision, then reconnect from the host PC using the Wi-Fi address.

## 5. Verify persistence and audio independence

Reboot into the normal protected entry. Check:

- Wi-Fi reconnects without manual login and the GUI is reachable through its reserved wireless address.
- Root remains overlay rw with lower disk ext4 ro; settings and EFI remain ro.
- Audio starts and runs normally with Ethernet disconnected.
- Saving through the button still works without restarting DSP.
- If Wi-Fi is unavailable, DSP should still start from local settings; record any network-related boot delay separately.

Do not make DSP service startup depend on Wi-Fi or Internet availability. Retain Ethernet as a recovery option, and document any deliberate choice to disable it.
