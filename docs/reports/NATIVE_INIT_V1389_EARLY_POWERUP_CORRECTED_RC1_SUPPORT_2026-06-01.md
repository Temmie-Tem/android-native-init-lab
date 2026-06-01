# Native Init V1389 Early-Observer Corrected RC1 Support

## Summary

- Cycle: `V1389`
- Type: source/build-only helper support
- Decision: `v1389-helper-v286-early-powerup-corrected-rc1-ready`
- Result: PASS
- Script: `scripts/revalidation/native_wifi_early_powerup_corrected_rc1_support_v1389.py`
- Helper: `a90_android_execns_probe v286`
- SHA256: `e5fc81a5becb2c6e6efd2ca026800560ed9e0e72a692f0fbb07861cf26d5380f`
- Reason: helper v286 adds an opt-in early-observer corrected RC1 trigger that fires from the first visible pm-service mdm_subsys_powerup gate before late_per_proxy response sampling
- Next Step: V1390 deploy helper v286, then V1391 bounded early-observer corrected RC1 live gate

## Context

- V1388 showed v285's pre-poll writer works but enters too late: about `3.556s` after `__subsystem_get(esoc0)`.
- V1388 also showed an earlier `pm-service` `mdm_subsys_powerup` thread was already observable before the late response sampler.
- V1389 keeps this source/build-only and moves only the opt-in corrected RC1 trigger point.

## Checks

| field | value |
| --- | --- |
| v1388_prerequisite_passed | true |
| helper_marker_v286 | true |
| helper_sha_matches | true |
| static_aarch64 | true |
| no_dynamic_section | true |
| new_flag_in_source | true |
| new_flag_in_binary | true |
| validation_requires_response_sampler | true |
| validation_requires_timing_sampler | true |
| validation_rejects_ambiguous_combo | true |
| mode_reported | true |
| response_sampler_reports_mode | true |
| early_markers_in_binary | true |
| early_block_before_late_per_proxy | true |
| early_block_before_response_sampler | true |
| early_block_reuses_powerup_gate | true |
| early_block_fail_closed_no_late_fallback | true |
| response_sampler_preserves_early_write_state | true |
| legacy_prepoll_path_preserved | true |
| host_only | true |

## Source Locations

| field | value |
| --- | --- |
| marker | 104 |
| new_flag_parse | 1354 |
| validation_response_sampler | 2049 |
| validation_timing_sampler | 2069 |
| validation_ambiguous_combo | 2076 |
| mode_const | 34838 |
| mode_report | 35009 |
| early_block | 36174 |
| early_begin_marker | 36186 |
| response_sampler_mode | 36288 |
| late_per_proxy_begin | 36236 |
| response_sampler_begin | 36276 |

## Hard Exclusions

- source/build-only; no device command
- no helper deploy
- no debugfs/sysfs write, rc_sel/case live write, or PCI rescan
- no PMIC/GPIO/GDSC direct write
- no eSoC notify or BOOT_DONE spoof
- no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping
- no flash, boot image write, or partition write
