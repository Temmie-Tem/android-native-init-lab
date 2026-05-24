# Native Init V754 HDD/PLD Traceability Selector Plan

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_hdd_pld_traceability_selector_v754.py`
- scope: read-only tracefs/kallsyms/ftrace capability selector

## Goal

V753 showed that existing dmesg evidence cannot distinguish `pld_init`,
`hdd_init`, and `wlan_hdd_register_driver` as the stall point. V754 determines
whether the next observability unit can use tracefs/ftrace/kallsyms, or whether
we need a different instrumentation route before any new Wi-Fi trigger.

## Basis Evidence

- `docs/reports/NATIVE_INIT_V753_HDD_PLD_PREREQ_CLASSIFIER_2026-05-24.md`
- `tmp/wifi/v753-hdd-pld-prereq-classifier/manifest.json`
- `docs/reports/NATIVE_INIT_V159_TRACEFS_FEASIBILITY_2026-05-08.md`
- `docs/reports/NATIVE_INIT_V200_DEBUG_OBSERVABILITY_2026-05-12.md`

## Work Items

1. Validate V753 as the input classifier.
2. Capture current `tracefs full` read-only state.
3. Capture `/proc/filesystems`, `/proc/mounts`, `/proc/config.gz`, and tracefs
   control-file readability without mounting or writing.
4. Capture bounded target function hits from `/proc/kallsyms`.
5. If tracefs is already mounted, check target hits in
   `available_filter_functions` read-only.
6. Route V755 to either bounded tracefs mount/filter proof or non-ftrace
   instrumentation.

## Target Functions

- `wlan_boot_cb`
- `wlan_hdd_state_ctrl_param_create`
- `pld_init`
- `hdd_init`
- `wlan_hdd_register_driver`
- `icnss_register_driver`
- `icnss_wlan_enable`

## Forbidden

- no tracefs/debugfs mount
- no ftrace control writes
- no `boot_wlan`, `qcwlanstate`, bind/unbind, module, or subsystem writes
- no service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or
  external ping
- no boot image or partition writes

## Success Criteria

- Produce `manifest.json` and `summary.md`.
- Confirm tracefs support and mount/readability state.
- Confirm whether target functions are visible in `/proc/kallsyms`.
- Confirm no tracefs mount, ftrace write, boot_wlan write, HAL/connect, or
  external ping occurred.
- Select the least invasive V755 observability gate.

## Source References

- Linux ftrace documentation:
  <https://docs.kernel.org/next/trace/ftrace.html>
- QCACLD `__hdd_module_init`:
  <https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m4/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_main.c#9341>
- QCACLD driver ops:
  <https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m4/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_driver_ops.c>
