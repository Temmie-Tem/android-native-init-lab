# Native Init V1388 V1387 Timing/Participant Classifier

## Summary

- Cycle: `V1388`
- Type: host-only V1387 timing/participant classifier
- Decision: `v1388-prepoll-gate-works-but-helper-enters-it-too-late`
- Result: PASS
- Script: `scripts/revalidation/native_wifi_v1387_timing_participant_classifier_v1388.py`
- Reason: V1387 proves the v285 pre-poll writer works, but it starts about 3.556s after esoc0 and only 0.106s earlier than V1383. The observer already saw a pm-service mdm_subsys_powerup thread before the late_per_proxy response-sampler block, so the next fix must move corrected RC1 into that earlier observer phase.
- Next Step: V1389 source/build-only: add helper v286 early-observer corrected RC1 trigger that fires on the first pm_service_powerup_thread observation before response-sampler/proc-map snapshots

## Checks

| check | pass |
| --- | --- |
| v1385_helper_support_passed | true |
| v1386_deploy_passed | true |
| v1387_live_passed | true |
| v1387_precondition_flags_present | true |
| v1387_prepoll_triggered | true |
| v1387_prepoll_poll0 | true |
| v1387_corrected_from_prepoll_phase | true |
| v1387_powerup_gate_positive | true |
| v1387_write_ok | true |
| v1387_rc1_transition_seen | true |
| v1387_failed_before_l0 | true |
| v1387_no_downstream | true |
| v1387_still_late_vs_android | true |
| v1387_prepoll_improvement_small | true |
| v1387_prepoll_started_after_esoc0_gap | true |
| v1387_prepoll_loop_not_primary_delay | true |
| observer_saw_powerup_before_response_sampler | true |
| v1384_prior_classifier_passed | true |
| host_only | true |

## Timing

| field | value |
| --- | --- |
| android_esoc0_to_assert_sec | 0.254929 |
| android_release_to_l0_sec | 0.016666 |
| v1379_esoc0_to_assert_sec | 4.122735 |
| v1383_esoc0_to_assert_sec | 3.666356 |
| v1387_esoc0_to_assert_sec | 3.560847 |
| v1387_vs_android_ratio | 13.967995 |
| v1387_improvement_vs_v1383_sec | 0.105509 |
| v1387_improvement_vs_v1379_sec | 0.561888 |
| v1387_prepoll_start_after_esoc0_sec | 3.555739 |
| v1387_corrected_write_after_prepoll_start_sec | 0.119000 |
| v1387_release_to_link_failed_sec | 0.108849 |

## Observer Ordering

| field | value |
| --- | --- |
| first_powerup_thread_line | 1036 |
| first_late_per_proxy_begin_line | 7999 |
| first_response_sampler_begin_line | 8006 |
| first_prepoll_begin_line | 8032 |
| first_corrected_begin_line | 8036 |
| first_corrected_end_line | 8050 |
| powerup_seen_before_late_per_proxy_begin | True |
| powerup_seen_before_prepoll_begin | True |

## Interpretation

| field | value |
| --- | --- |
| prepoll_code_path_works | true |
| prepoll_loop_is_not_primary_delay | true |
| late_per_proxy_response_sampler_entry_is_too_late | true |
| earlier_powerup_thread_signal_exists | true |
| another_same_shape_live_retry_is_low_value | true |
| next_change_should_be_source_build_only | true |

## Key Observer Lines

- `first_powerup_thread_sample`: thread_sample index=1 tid=9280 comm=Binder:9245_1 state=D wchan=mdm_subsys_powerup syscall=56 0xffffff9c 0xb400007f80006108 0x0 0x0 0x72006500670061 0x6100670065007200 0x7efbdfb720 0x7f8078965c
- `late_per_proxy_begin_line_text`: pm_service_trigger_observer.late_per_proxy.begin=1
- `prepoll_begin_line_text`: pm_service_trigger_observer.prepoll_corrected_rc1.begin=1
- `corrected_begin_line_text`: pm_service_trigger_observer.corrected_rc1_enumerate.begin=1

## Hard Exclusions

- host-only; no device command
- no debugfs/sysfs write, rc_sel/case write, or PCI rescan
- no PMIC/GPIO/GDSC direct write
- no eSoC notify or BOOT_DONE spoof
- no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping
- no flash, boot image write, or partition write
