# Native Init V1377 Corrected RC1 Powerup Gate Support

## Summary

- Cycle: `V1377`
- Type: source/build-only helper support
- Decision: `v1377-helper-v283-powerup-gate-ready`
- Result: PASS
- Script: `scripts/revalidation/native_wifi_corrected_rc1_powerup_gate_support_v1377.py`
- Helper: `a90_android_execns_probe v283`
- SHA256: `985eba4834b3b0324d886df39cecff9811ae183ea800119fdaea2d6ef8431a18`
- Reason: helper v283 gates corrected RC1 enumerate on pm-service mdm_subsys_powerup observation instead of requiring an already-open /dev/subsys_esoc0 fd
- Next Step: V1378 deploy helper v283, then V1379 rerun bounded Android participant corrected RC1 gate

## Checks

| field | value |
| --- | --- |
| helper_marker_v283 | true |
| helper_sha_matches | true |
| static_aarch64 | true |
| no_dynamic_section | true |
| powerup_counter_used | true |
| trigger_accepts_powerup_thread | true |
| fd_gate_still_supported | true |
| reports_powerup_gate | true |
| skip_reason_updated | true |
| corrected_rc1_flag_still_present | true |

## Source Locations

| field | value |
| --- | --- |
| marker | 104 |
| powerup_counter | 17868 |
| powerup_gate | 36379 |
| gate_report | 6687 |
| skip_reason | 36404 |

## Hard Exclusions

- source/build-only; no device command
- no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping
- no PMIC/GPIO/GDSC direct write
- no eSoC notify or BOOT_DONE spoof
- no flash, boot image write, or partition write
