# Native Init V1518 Wi-Fi Critical Source Timing Classifier

## Summary

- Cycle: `V1518`
- Type: host-only classifier over V1517 live handoff evidence
- Decision: `v1518-critical-source-first-window-pre-fail-confirmed`
- Result: PASS
- Reason: V1517 proves all selected critical first-window sources finish before the RC1 link-fail marker while L0/MHI/WLFW/wlan0 remain absent
- Evidence: `tmp/wifi/v1517-wifi-critical-source-pre-l0-handoff`

## Handoff Result

- V1517 decision: `v1517-test-boot-downstream-progress-rollback-pass`
- handoff pass: `True`
- rollback ok: `True`
- progress decision: `rc1-ltssm-link-failed-no-l0`
- RC1 progress/link failed/L0: `True/True/False`
- MHI/WLFW/BDF/FW-ready/wlan0: `False/False/False/False/False`

## Critical First-Window Timing

- link failed after TEST:11 case: `114.851` ms
- first sample micro elapsed: `0` ms
- max selected source end: `30` ms
- all selected sources finish before link fail: `True`
- full `clk_summary` skipped: `True`
- no full clock summary source emitted: `True`

| Source | Begin ms | End ms | Duration ms |
|---|---:|---:|---:|
| `micro_interrupts` | `0` | `3` | `3` |
| `micro_debug_gpio` | `3` | `4` | `1` |
| `micro_pcie1_current_link_state` | `4` | `5` | `1` |
| `micro_pcie1_link_state` | `5` | `5` | `0` |
| `micro_critical_regulator` | `5` | `29` | `24` |
| `micro_critical_pinmux` | `29` | `30` | `1` |

## Dmesg Classification

- LTSSM states: `LTSSM_DETECT_QUIET, LTSSM_POLL_ACTIVE, LTSSM_POLL_COMPLIANCE`
- case after esoc0: `35.983` ms
- link failed after case: `114.851` ms
- link failed marker: `True`
- L0/MHI/WLFW/BDF/FW-ready/wlan0: `False/False/False/False/False/False`

## Interpretation

V1517 closes the V1514 sampler-overrun gap. The selected fast sources complete by about 30ms after `case=11`, before the ~115ms RC1 link-fail marker. In that pre-fail window GPIO135 remains low, GPIO142 remains low, `pcie_1_gdsc` remains 0mV, and the pcie1 pinmux ownership is as expected. RC1 still fails before L0, so firmware/MHI/WLFW/scan/connect remain downstream.

## Safety Scope

This classifier is host-only. It performs no device command, flash, reboot, partition write, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE` spoof, global PCI rescan, or platform bind/unbind.

## Next

- V1519 should compare Android-good and native-fail critical source timing/order before any new live mutation.
- Keep firmware/MHI/WLFW/scan/connect work parked until RC1 L0 and PCI enumeration exist.
