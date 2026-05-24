# Native Init V749 Non-bind Trigger Selector Plan

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_nonbind_trigger_selector_v749.py`
- scope: read-only current native capture plus host-side evidence classifier

## Goal

Turn the V748 non-bind trigger selection into a concrete next live gate without
starting Wi-Fi HAL or attempting connection. The selector compares three
remaining control surfaces:

- `fs_ready`, source-backed in some Qualcomm CNSS2 trees;
- `/sys/kernel/boot_wlan/boot_wlan`;
- `/sys/wifi/qcwlanstate`.

## Basis Evidence

- `tmp/wifi/v749-nonbind-trigger-selector-preflight/`
- `tmp/wifi/v749-nonbind-trigger-selector/`
- `tmp/wifi/v508-wlan-boot-run-20260521-100318/summary.md`
- `docs/reports/NATIVE_INIT_V513_DUAL_HAL_DRIVER_STATE_ON_2026-05-21.md`
- `docs/reports/NATIVE_INIT_V514_ICNSS_MODULE_READINESS_2026-05-21.md`
- `docs/reports/NATIVE_INIT_V748_NONBIND_POWERUP_TRIGGER_2026-05-24.md`

## Source References

- Qualcomm CNSS2 `fs_ready` sysfs source:
  <https://android.googlesource.com/kernel/msm/+/53f9955dd5876826f623fb9a1a736cfe36bec176/drivers/net/wireless/cnss2/main.c>
- QCACLD `qcwlanstate`/driver start source:
  <https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m4/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_main.c>

## Work Items

1. Capture current native `a90_wlanbootctl status`.
2. Capture read-only WLAN control surfaces, ICNSS/QCA driver paths, and selected
   module parameters.
3. Check whether `fs_ready` exists in the current native sysfs surface.
4. Compare V508 standalone `boot_wlan` and V513 standalone `qcwlanstate` results.
5. Select or reject a V750 live gate while keeping connection-level work blocked.

## Forbidden

- no write to `fs_ready`, `boot_wlan`, `qcwlanstate`, bind/unbind, or driver state
- no service-manager or Wi-Fi HAL start
- no scan/connect/link-up
- no credentials, DHCP, route change, or external ping
- no boot image or partition write

## Success Criteria

- Produce read-only `manifest.json` and `summary.md`.
- Confirm whether `fs_ready` is a current-native surface or Android-handoff-only
  candidate.
- Select a V750 gate that is still below Wi-Fi HAL/connect and based on current
  evidence, not a blind retry.
