# Native Init V1374 Android Participant RC1 Support

## Summary

- Cycle: `V1374`
- Type: source/build-only helper support
- Decision: `v1374-helper-v282-support-ready`
- Result: PASS
- Script: `scripts/revalidation/native_wifi_android_participant_rc1_support_v1374.py`
- Helper: `a90_android_execns_probe v282`
- SHA256: `c1f4670536c37b068dd2f8ac807c0eb5416eb3f248857791002156c1f0195418`
- Reason: helper v282 now supports a helper-side corrected RC1 enumerate action gated on the late per_proxy window after pm-service is observed holding /dev/subsys_esoc0
- Next Step: V1375 deploy-only helper v282 preflight, then V1376 bounded live Android participant parity + corrected RC1 enumerate gate

## Source Checks

| check | pass |
| --- | --- |
| gated_on_pm_service_esoc0 | true |
| helper_marker_v282 | true |
| new_flag_in_usage | true |
| new_flag_parsed | true |
| reports_debugfs_write | true |
| reports_skip_without_esoc0 | true |
| requires_mdm2ap_timing_sampler | true |
| requires_response_sampler | true |
| uses_corrected_rc1_case_path | true |
| uses_corrected_rc1_rc_sel_path | true |
| writes_case_11_enumerate | true |
| writes_rc_sel_bitmask_2 | true |

## Build Checks

| check | pass |
| --- | --- |
| helper_and_versioned_sha_match | true |
| helper_exists | true |
| helper_marker_embedded | true |
| no_dynamic_section | true |
| static_aarch64 | true |
| versioned_helper_exists | true |

## Prior Evidence Checks

| check | pass |
| --- | --- |
| v1373_passed | true |

## Source Locations

| field | line |
| --- | --- |
| path | stage3/linux_init/helpers/a90_android_execns_probe.c |
| marker_line | 104 |
| flag_line | 480 |
| rc_sel_path_line | 6669 |
| case_path_line | 6670 |
| gate_line | 36373 |

## V1376 Live Design

- Intent: start the lower Android participant parity path, wait until pm-service reaches /dev/subsys_esoc0, then trigger corrected RC1 enumerate from inside the same helper process
- Required flags:
  - `--allow-post-pm-mdm-helper-esoc-observer`
  - `--allow-post-pm-mdm-helper-lower-trace`
  - `--pm-observer-start-mdm-helper-after-cnss`
  - `--pm-observer-start-cnss-after-provider`
  - `--pm-observer-start-cnss-before-per-proxy`
  - `--pm-observer-start-per-proxy-after-mdm-helper-esoc-fd`
  - `--pm-observer-late-per-proxy-response-sampler`
  - `--pm-observer-late-per-proxy-mdm2ap-errfatal-pcie-timing-sampler`
  - `--pm-observer-late-per-proxy-corrected-rc1-enumerate`
- Success signals:
  - corrected_rc1_enumerate.triggered=1
  - rc_sel_rc=0 and case_rc=0
  - RC1 LTSSM reaches L0, or GPIO142/PCI/MHI/WLFW/wlan0 appears
  - postflight selftest fail=0 after cleanup or reboot recovery
- Failure signals:
  - per_mgr_subsys_esoc0_count never becomes positive
  - rc_sel or case write fails
  - transport loss without recovery evidence
  - postflight selftest fail>0
  - unexpected Wi-Fi HAL, scan/connect, DHCP/routes, credential, or external ping activity

## Hard Exclusions

- V1374 is source/build-only; no device command is run by this script
- no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping
- no PMIC/GPIO/GDSC direct writes
- no eSoC notify or BOOT_DONE spoof
- no flash, boot image write, or partition write

## Evidence

- `tmp/wifi/v1374-android-participant-rc1-support/manifest.json`
- `tmp/wifi/v1374-android-participant-rc1-support/summary.md`
