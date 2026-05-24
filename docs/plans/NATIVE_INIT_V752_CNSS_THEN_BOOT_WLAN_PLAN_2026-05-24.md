# Native Init V752 CNSS then Boot WLAN Plan

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_cnss_then_boot_wlan_v752.py`
- scope: bounded live ordering proof below service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping

## Goal

Test the first V751 next-gate candidate: run the lower modem window, start the
Android Wi-Fi companion stack through `cnss_diag` and `cnss-daemon`, then execute
a bounded `boot_wlan` observe window. The purpose is to determine whether this
ordering advances native from HDD init into driver-loaded, ICNSS-QMI,
firmware-ready, WLFW/BDF, wiphy, or `wlan0`.

## Basis Evidence

- `docs/reports/NATIVE_INIT_V750_LOWER_WINDOW_BOOT_WLAN_2026-05-24.md`
- `docs/reports/NATIVE_INIT_V751_ICNSS_MODULE_INIT_CLASSIFIER_2026-05-24.md`
- `tmp/wifi/v750-lower-window-boot-wlan/`
- `tmp/wifi/v751-icnss-module-init-classifier/`

## Gate Contract

- `V490` SELinux policy-load proof must be current for this boot.
- `V731`/`V732` firmware-mounted modem holder prerequisites must remain valid.
- helper must be `/cache/bin/a90_android_execns_probe` with marker
  `a90_android_execns_probe v124`.
- `a90_wlanbootctl` must be `/cache/bin/a90_wlanbootctl` with marker
  `a90_wlanbootctl v2`.
- live action requires `--allow-cnss-then-boot-wlan --assume-yes`.

## Work Items

1. Run plan and preflight without mutations.
2. Refresh current-boot `selinuxfs`/V490 prerequisites if preflight blocks.
3. Mount firmware partitions read-only and confirm modem firmware visibility.
4. Hold `subsys_modem` without touching `esoc0` and wait for QRTR RX.
5. Start `qrtr-ns,rmt_storage,tftp_server,pd-mapper,cnss_diag,cnss-daemon`.
6. Run `a90_wlanbootctl boot-observe` for a bounded window.
7. Capture post-boot WLAN, QRTR, ICNSS, MHI, and dmesg markers.
8. Reboot cleanup and verify native health.

## Forbidden

- no service-manager, Wi-Fi HAL, `wificond`, supplicant, hostapd, scan/connect,
  credentials, DHCP/routes, or external ping
- no bind/unbind, `driver_override`, module load/unload, `esoc0`, or subsystem
  state writes
- no `qcwlanstate` writes
- no boot image or partition writes

## Success Criteria

- Produce `manifest.json` and `summary.md`.
- Prove the companion stack starts and remains postflight-safe.
- Prove whether `boot_wlan` after CNSS companions advances beyond V751's HDD
  init stall.
- Record forbidden-action booleans and reboot cleanup evidence.
- Select the next gate based on observed driver progression, not blind retry.

## Source References

- QCACLD `boot_wlan` callback:
  <https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m4/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_main.c#9406>
- QCACLD `__hdd_module_init`:
  <https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m4/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_main.c#9341>
- QCACLD `qcwlanstate` wait path:
  <https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m4/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_main.c#9266>
