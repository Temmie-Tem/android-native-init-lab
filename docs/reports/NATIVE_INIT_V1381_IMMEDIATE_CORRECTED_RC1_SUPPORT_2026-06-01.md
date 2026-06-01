# Native Init V1381 Immediate Corrected RC1 Support

## Summary

- Cycle: `V1381`
- Type: source/build-only helper support
- Decision: `v1381-helper-v284-immediate-corrected-rc1-ready`
- Result: PASS
- Script: `scripts/revalidation/native_wifi_immediate_corrected_rc1_support_v1381.py`
- Helper: `a90_android_execns_probe v284`
- SHA256: `da1f8b65cbc3872f7ec31a368bd382720a399d3a785e50ae383c800632047b9f`
- Reason: helper v284 adds an immediate corrected RC1 enumerate path that fires as soon as the pm-service powerup-thread gate becomes positive, before the response sampler consumes the poll iteration
- Next Step: V1382 deploy helper v284, then V1383 bounded immediate corrected RC1 live gate

## Context

- V1380 showed V1379 wrote corrected RC1 too late: about 4.12 seconds after `__subsystem_get(esoc0)`, versus Android's about 0.255 second reference window.
- V1381 changes only source/build support. It adds an immediate path for the existing corrected RC1 debugfs enumerate write, guarded by the same powerup-thread/fd gate.
- The legacy delayed path remains guarded for non-immediate runs.

## Checks

| field | value |
| --- | --- |
| v1380_prerequisite_passed | true |
| helper_marker_v284 | true |
| helper_sha_matches | true |
| static_aarch64 | true |
| no_dynamic_section | true |
| new_flag_in_source | true |
| new_flag_in_binary | true |
| validation_requires_response_sampler | true |
| validation_requires_timing_sampler | true |
| immediate_enabled_reported | true |
| mode_reported | true |
| monotonic_timestamp_reported | true |
| powerup_gate_still_used | true |
| immediate_before_sampler | true |
| delayed_path_guarded_for_legacy_flag | true |
| host_only | true |

## Source Locations

| field | value |
| --- | --- |
| marker | 104 |
| new_flag_parse | 482 |
| validation_response_sampler | 2027 |
| validation_timing_sampler | 2037 |
| immediate_mode_const | 34787 |
| mode_report | 34955 |
| sampler_enable_report | 36172 |
| immediate_trigger | 36289 |
| legacy_delayed_guard | 36415 |
| monotonic_report | 6702 |

## Hard Exclusions

- source/build-only; no device command
- no debugfs/sysfs write, rc_sel/case write, or PCI rescan
- no PMIC/GPIO/GDSC direct write
- no eSoC notify or BOOT_DONE spoof
- no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping
- no flash, boot image write, or partition write
