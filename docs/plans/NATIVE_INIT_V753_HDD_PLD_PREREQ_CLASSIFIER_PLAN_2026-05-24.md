# Native Init V753 HDD/PLD Prerequisite Classifier Plan

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_hdd_pld_prereq_classifier_v753.py`
- scope: read-only current native capture plus V752/source/reference classifier

## Goal

V752 proved that starting `cnss_diag` and `cnss-daemon` before bounded
`boot_wlan` still stops at the HDD/qcwlanstate boundary. V753 classifies the
remaining gap using read-only evidence only: whether native has an explicit
HDD/PLD/register-driver failure, whether any driver-success marker appeared, and
whether the current post-cleanup native surface remains before netdev/wiphy.

## Basis Evidence

- `docs/reports/NATIVE_INIT_V752_CNSS_THEN_BOOT_WLAN_2026-05-24.md`
- `tmp/wifi/v752-cnss-then-boot-wlan/manifest.json`
- `tmp/wifi/v752-cnss-then-boot-wlan/native/dmesg-delta.txt`
- `tmp/wifi/v752-cnss-then-boot-wlan/native/boot-wlan-observe-after-cnss.txt`
- `docs/reports/NATIVE_INIT_V703_ANDROID_NATIVE_BINDING_COMPARE_2026-05-24.md`

## Source Model

The Android QCACLD source orders the static `boot_wlan` path as:

```text
__hdd_module_init
  -> wlan_hdd_state_ctrl_param_create
  -> pld_init
  -> hdd_init
  -> wlan_hdd_register_driver
  -> "wlan: driver loaded"
```

Therefore native evidence that reaches `wlan_hdd_state` but lacks
driver-loaded, ICNSS-QMI, firmware-ready, WLFW/BDF, wiphy, and `wlan0` only
places the blocker between the early HDD entry and register-driver completion.
V753 determines whether current evidence narrows that further without another
trigger attempt.

## Work Items

1. Validate V752 decision and safety envelope.
2. Parse V752 marker counts for HDD entry, success markers, and failure markers.
3. Capture current native version/status/selftest and WLAN/ICNSS/MHI surfaces.
4. Confirm the device remains contained: no wiphy, `wlan0`, service-manager, Wi-Fi
   HAL, scan/connect, credentials, DHCP/routes, or external ping.
5. Decide whether the next unit can target an explicit failure or must add
   instrumentation around HDD/PLD/register-driver boundaries.

## Forbidden

- no `boot_wlan`, `qcwlanstate`, bind/unbind, `driver_override`, module
  load/unload, subsystem state, `esoc0`, or daemon state writes
- no service-manager, Wi-Fi HAL, `wificond`, supplicant, hostapd, scan/connect,
  credentials, DHCP/routes, or external ping
- no boot image or partition writes

## Success Criteria

- Produce `manifest.json` and `summary.md`.
- Confirm V752 stayed in the safety envelope and reached HDD entry.
- Confirm whether explicit HDD/PLD/register-driver failure markers are present.
- Confirm whether current native still lacks wiphy/`wlan0`.
- Select V754 as either explicit-failure repair or instrumentation design.

## Source References

- QCACLD `__hdd_module_init`:
  <https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m4/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_main.c#9341>
- QCACLD `boot_wlan` callback:
  <https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m4/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_main.c#9406>
- QCACLD `qcwlanstate` wait path:
  <https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m4/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_main.c#9266>
- QCACLD driver ops:
  <https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m4/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_driver_ops.c>
