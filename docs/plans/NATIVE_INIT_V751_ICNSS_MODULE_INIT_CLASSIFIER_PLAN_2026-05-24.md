# Native Init V751 ICNSS Module-init Classifier Plan

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_icnss_module_init_classifier_v751.py`
- scope: read-only current native capture plus V750/source/reference classifier

## Goal

Classify the V750 result at the QCACLD/HDD module initialization boundary.
V750 proved that lower-window `boot_wlan` writes successfully, but no
WLFW/service `69`, BDF, wiphy, or `wlan0` appears. V751 determines whether this
means `boot_wlan` never entered the driver, or entered the driver but stalled
before "driver loaded" / ICNSS-QMI / firmware-ready.

## Basis Evidence

- `docs/reports/NATIVE_INIT_V750_LOWER_WINDOW_BOOT_WLAN_2026-05-24.md`
- `tmp/wifi/v750-lower-window-boot-wlan/`
- `docs/reports/NATIVE_INIT_V703_ANDROID_NATIVE_BINDING_COMPARE_2026-05-24.md`

## Source References

- QCACLD `boot_wlan` callback:
  <https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m4/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_main.c#9406>
- QCACLD `__hdd_module_init`:
  <https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m4/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_main.c#9341>
- QCACLD `qcwlanstate` wait path:
  <https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m4/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_main.c#9266>
- QCACLD `DRIVER_MODULES_UNINITIALIZED` stop path:
  <https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m4/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_main.c#7947>

## Work Items

1. Parse V750 `manifest.json` and `dmesg-delta.txt`.
2. Capture current native ICNSS/WLAN sysfs surface read-only.
3. Confirm Android reference still contains ICNSS-QMI, BDF, firmware-ready, and
   `wlan0` markers.
4. Classify whether V750 reached QCACLD/HDD init and where it stalled.
5. Select a V752 gate that remains below service-manager, Wi-Fi HAL,
   scan/connect, credentials, DHCP/routes, and external ping.

## Forbidden

- no `boot_wlan` or `qcwlanstate` write
- no bind/unbind, `driver_override`, module load/unload, or `esoc0`
- no daemon, service-manager, Wi-Fi HAL, scan/connect, credentials,
  DHCP/routes, or external ping
- no boot image or partition write

## Success Criteria

- Produce `manifest.json` and `summary.md`.
- Prove whether V750 entered HDD init by detecting `wlan: Loading driver` and
  `wlan_hdd_state` evidence.
- Prove whether `driver loaded`, ICNSS-QMI, firmware-ready, wiphy, and `wlan0`
  remained absent.
- Route the next gate without widening into connection-level behavior.
