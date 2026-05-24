# Native Init V750 Lower-window Boot WLAN Plan

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_lower_window_boot_wlan_v750.py`
- scope: bounded live proof below service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping

## Goal

Test the only remaining useful `boot_wlan` path selected by V749: execute a
fixed-target `boot_wlan` write inside the proven firmware-mounted modem holder
and lower companion window.

This is not a Wi-Fi connection attempt. It is a pre-connection readiness proof
for WLFW/service `69`, BDF, wiphy, and `wlan0`.

## Basis Evidence

- `docs/reports/NATIVE_INIT_V749_NONBIND_TRIGGER_SELECTOR_2026-05-24.md`
- `tmp/wifi/v749-nonbind-trigger-selector/`
- `tmp/wifi/v731-firmware-mounted-modem-holder/`
- `tmp/wifi/v732-cnss2-mhi-holder-window/`
- `tmp/wifi/v750-v401-current-run/`
- `tmp/wifi/v750-v490-current-run/`

## Live Sequence

1. Confirm current native version, selftest, helper SHA, and `a90_wlanbootctl`
   SHA.
2. Ensure current-boot `selinuxfs` and SELinux policy-load prerequisites exist.
3. Mount Android firmware partitions read-only through the existing V584/V733
   path.
4. Hold only `subsys_modem`; do not open `esoc0`.
5. Wait for `qrtr: Modem QMI Readiness RX`.
6. Start lower companions only:
   `qrtr-ns,rmt_storage,tftp_server,pd-mapper`.
7. Run `a90_wlanbootctl boot-observe <bounded seconds>`.
8. Capture `qcwlanstate`, `/dev/wlan`, QRTR, MHI/QCA6390, WLFW/BDF, wiphy,
   `wlan0`, and dmesg markers.
9. Reboot as cleanup and verify native `version`/`status`.

## Forbidden

- no service-manager, `cnss-daemon`, Wi-Fi HAL, wificond, supplicant, hostapd
- no scan/connect/link-up
- no credential use
- no DHCP, route changes, or external ping
- no bind/unbind, `driver_override`, module load/unload, `esoc0`, or
  `qcwlanstate` write
- no boot image, Android partition, or persistent filesystem write

## Success Criteria

- `boot_wlan` write executes only inside the lower-ready window.
- Firmware mounts, `subsys_modem` holder, QRTR RX/TX, lower companion contract,
  and reboot cleanup pass.
- Output classifies whether the write advances:
  - `wlan0`/wiphy;
  - WLFW/BDF/service `69`;
  - control surface only;
  - or no lower progress.
- All connection-level actions remain false in the manifest.
