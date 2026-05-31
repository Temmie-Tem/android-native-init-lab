# Native Init V1380 RC1 LTSSM/Participant Gap Classifier

## Summary

- Cycle: `V1380`
- Type: host-only RC1 LTSSM/participant gap classifier
- Decision: `v1380-v1379-rc1-action-too-late-for-android-window`
- Result: PASS
- Script: `scripts/revalidation/native_wifi_rc1_ltssm_participant_gap_classifier_v1380.py`
- Evidence:
  - `tmp/wifi/v1380-rc1-ltssm-participant-gap-classifier/manifest.json`
  - `tmp/wifi/v1380-rc1-ltssm-participant-gap-classifier/summary.md`

## Decision

V1379 fixed the v283 powerup-thread gate and executed rc_sel/case successfully, but RC1 enumerate occurred 4.123s after esoc0 versus Android's 0.255s reference; the resulting LTSSM path still failed before L0 with no GPIO142/PCI/MHI/WLFW/wlan0 progress.

## Checks

| check | pass |
| --- | --- |
| v1379_passed | true |
| v1379_corrected_triggered | true |
| v1379_powerup_gate_positive | true |
| v1379_rc_write_ok | true |
| v1379_rc1_transition_seen | true |
| v1379_no_downstream | true |
| v1379_reached_phy_ready | true |
| v1379_failed_before_l0 | true |
| android_reference_reaches_l0 | true |
| v1373_selected_android_participant_combo | true |
| v1379_timing_is_late_vs_android | true |
| host_only | true |

## Timing Comparison

| field | seconds |
| --- | --- |
| v1379_esoc0_time | 1311.506981 |
| v1379_test11_time | 1315.629697 |
| v1379_assert_time | 1315.629716 |
| v1379_phy_ready_time | 1315.635136 |
| v1379_release_time | 1315.635141 |
| v1379_detect_quiet_time | 1315.641281 |
| v1379_poll_active_time | 1315.651512 |
| v1379_poll_compliance_time | 1315.677090 |
| v1379_l0_time |  |
| v1379_link_failed_time | 1315.744019 |
| v1379_esoc0_to_assert_sec | 4.122735 |
| v1379_release_to_poll_compliance_sec | 0.041949 |
| v1379_release_to_link_failed_sec | 0.108878 |
| android_esoc0_to_assert_sec | 0.254929 |
| android_release_to_l0_sec | 0.016666 |
| v1379_vs_android_esoc0_to_assert_ratio | 16.172091 |

## Evidence Lines

| field | value |
| --- | --- |
| v1379_esoc0 | [ 1311.506981] [2:  Binder:9283_3: 9902] subsys-restart: __subsystem_get(): __subsystem_get: esoc0 count:0 |
| v1379_test11 | [ 1315.629697] [6:a90_android_exe: 1167] PCIe: TEST: 11 |
| v1379_assert | [ 1315.629716] [6:a90_android_exe: 1167] msm_pcie_enable: PCIe: Assert the reset of endpoint of RC1. |
| v1379_phy_ready | [ 1315.635136] [6:a90_android_exe: 1167] msm_pcie_enable: PCIe RC1 PHY is ready! |
| v1379_release | [ 1315.635141] [6:a90_android_exe: 1167] msm_pcie_enable: PCIe: Release the reset of endpoint of RC1. |
| v1379_poll_compliance | [ 1315.677090] [6:a90_android_exe: 1167] msm_pcie_enable: PCIe RC1: LTSSM_STATE: LTSSM_POLL_COMPLIANCE |
| v1379_link_failed | [ 1315.744019] [2:a90_android_exe: 1167] msm_pcie_enable: PCIe RC1 link initialization failed (LTSSM_STATE:0x3) |

## Counts

| field | value |
| --- | --- |
| v1379_l0_lines | 0 |
| v1379_current_gen_lines | 0 |
| v1379_link_initialized_lines | 0 |
| v1379_link_failed_lines | 1 |

## Interpretation

V1379 did not prove the final Android timing parity path. It proved the corrected RC1 action can be gated by the `pm-service` powerup thread and can transition RC1, but the action happened far later than the Android esoc0-to-RC1 interval captured in V1371. The next implementation should move the corrected RC1 write before expensive surface snapshots/samplers, then observe the post-write window.

## Hard Exclusions

- host-only; no device command
- no debugfs/sysfs write, rc_sel/case write, or PCI rescan
- no PMIC/GPIO/GDSC direct write
- no eSoC notify or BOOT_DONE spoof
- no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping
- no flash, boot image write, or partition write

## Next

V1381 source/build-only helper v284: trigger corrected RC1 immediately when the powerup-thread gate becomes positive, then sample the post-enumerate window
