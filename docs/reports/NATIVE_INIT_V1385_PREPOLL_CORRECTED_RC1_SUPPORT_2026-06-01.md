# Native Init V1385 Pre-Poll Corrected RC1 Support

## Summary

- Cycle: `V1385`
- Type: source/build-only helper support
- Decision: `v1385-helper-v285-prepoll-corrected-rc1-ready`
- Result: PASS
- Script: `scripts/revalidation/native_wifi_prepoll_corrected_rc1_support_v1385.py`
- Helper: `a90_android_execns_probe v285`
- SHA256: `09827b6f0301f077cd0beb4ed2ae9d48a63662d0ca34eff38245704f2f724cf4`
- Reason: helper v285 adds a pre-poll corrected RC1 path that checks the fd/powerup-thread gate every 1ms immediately after late per_proxy spawn, before the main 50ms sampler loop
- Next Step: V1386 deploy helper v285, then V1387 bounded pre-poll corrected RC1 live gate

## Context

- V1384 showed V1383 was still too late before the debugfs write; the write itself reached RC1 immediately.
- V1385 keeps this source/build-only and adds a pre-poll path before the main late-per-proxy sampler loop.
- The pre-poll path still requires the same fd or `pm_service_powerup_thread_count` gate before writing corrected RC1.

## Checks

| field | value |
| --- | --- |
| v1384_prerequisite_passed | true |
| helper_marker_v285 | true |
| helper_sha_matches | true |
| static_aarch64 | true |
| no_dynamic_section | true |
| new_flag_in_source | true |
| new_flag_in_binary | true |
| validation_requires_response_sampler | true |
| validation_requires_timing_sampler | true |
| prepoll_mode_reported | true |
| response_sampler_reports_prepoll | true |
| prepoll_markers_in_binary | true |
| prepoll_before_main_poll | true |
| prepoll_reuses_powerup_or_fd_gate | true |
| prepoll_tight_window | true |
| legacy_immediate_path_preserved | true |
| host_only | true |

## Source Locations

| field | value |
| --- | --- |
| marker | 104 |
| new_flag_parse | 484 |
| validation_response_sampler | 2038 |
| validation_timing_sampler | 2053 |
| mode_const | 34806 |
| mode_report | 34975 |
| sampler_report | 36194 |
| prepoll_block | 36284 |
| prepoll_interval | 36289 |
| main_poll_loop | 36355 |

## Hard Exclusions

- source/build-only; no device command
- no debugfs/sysfs write, rc_sel/case live write, or PCI rescan
- no PMIC/GPIO/GDSC direct write
- no eSoC notify or BOOT_DONE spoof
- no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping
- no flash, boot image write, or partition write
