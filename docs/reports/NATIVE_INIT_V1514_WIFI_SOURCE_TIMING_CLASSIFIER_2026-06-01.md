# Native Init V1514 Wi-Fi Source Timing Classifier

## Summary

- Cycle: `V1514`
- Type: host-only classifier over V1513 live handoff evidence
- Decision: `v1514-source-timing-identifies-clk-summary-overrun`
- Result: PASS
- Reason: V1513 proves the first sample starts at case+0ms, but clk_summary read crosses the RC1 link-fail marker and makes later source reads post-failure
- Evidence: `tmp/wifi/v1513-wifi-source-timestamped-pre-l0-handoff`

## Handoff Result

- V1513 decision: `v1513-test-boot-downstream-progress-rollback-pass`
- handoff pass: `True`
- rollback ok: `True`
- progress decision: `rc1-ltssm-link-failed-no-l0`
- RC1 progress/link failed/L0: `True/True/False`
- MHI/WLFW/BDF/FW-ready/wlan0: `False/False/False/False/False`

## First Sample Source Timing

- link failed after TEST:11 case: `114.859` ms
- first sample micro elapsed: `0` ms
- source timing marker present: `True`
- expected sources present: `True`
- fast sources finish before `clk_summary`: `True`
- `clk_summary` crosses link fail: `True`

| Source | Begin ms | End ms | Duration ms |
|---|---:|---:|---:|
| `micro_interrupts` | `0` | `2` | `2` |
| `micro_debug_gpio` | `3` | `10` | `7` |
| `micro_pcie1_current_link_state` | `10` | `11` | `1` |
| `micro_pcie1_link_state` | `11` | `11` | `0` |
| `micro_batched_regulator` | `11` | `35` | `24` |
| `micro_batched_clk` | `35` | `149` | `114` |
| `micro_batched_debug_gpio` | `149` | `149` | `0` |
| `micro_batched_pinmux` | `149` | `150` | `1` |
| `micro_batched_pinconf` | `150` | `150` | `0` |

## Dmesg Classification

- LTSSM states: `LTSSM_DETECT_QUIET, LTSSM_POLL_ACTIVE, LTSSM_POLL_COMPLIANCE`
- case after esoc0: `31.929` ms
- link failed after case: `114.859` ms
- link failed marker: `True`
- L0/MHI/WLFW/BDF/FW-ready/wlan0: `False/False/False/False/False/False`

## Interpretation

V1513 removes the ambiguity from V1510. The first sample begins at case+0ms and captures fast sources before the link-fail window, but the broad `/sys/kernel/debug/clk/clk_summary` read lasts about 114ms and crosses the RC1 link-fail marker. Reads after that point are not pre-fail evidence. The next useful sampler should split fast critical sources from slow diagnostic sources instead of repeating full `clk_summary` inside the first 115ms window.

## Safety Scope

This classifier is host-only. It performs no device command, flash, reboot, partition write, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE` spoof, global PCI rescan, or platform bind/unbind.

## Next

- V1515 should be source/build-only and add a critical-source pre-L0 sampler that avoids full `clk_summary` during the first link-fail window.
- Keep firmware/MHI/WLFW/scan/connect work parked until RC1 L0 and PCI enumeration exist.
