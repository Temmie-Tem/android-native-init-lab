# Native Init V1545 Low-Overhead Endpoint Observer Design

## Summary

- Cycle: `V1545`
- Type: host-only source/design classifier
- Decision: `v1545-low-overhead-observer-design-ready`
- Result: PASS
- Reason: existing PID1 critical-fast sampler can build the next observer without full clk_summary in the RC1 micro window

## Inputs

| input | path |
| --- | --- |
| v1544_manifest | tmp/wifi/v1544-endpoint-electrical-result-classifier/manifest.json |
| v1541_build | scripts/revalidation/build_native_init_wifi_test_boot_v1541.py |
| v1515_build | scripts/revalidation/build_native_init_wifi_test_boot_v1515.py |
| v1536_build | scripts/revalidation/build_native_init_wifi_test_boot_v1536.py |
| base_build | scripts/revalidation/build_native_init_wifi_test_boot_v1393.py |
| pid1_source | stage3/linux_init/v724/90_main.inc.c |

## Checks

| check | value |
| --- | --- |
| v1544-fixed-no-l0-classifier-pass | True |
| v1541-explains-slow-clock-source | True |
| critical-fast-contract-exists | True |
| critical-fast-avoids-full-clk-summary | True |
| critical-fast-covers-endpoint-sources | True |
| existing-build-proves-critical-without-micro-focused | True |
| sysfs-client-enumerate-flag-available | True |

## Source Contract

| field | value |
| --- | --- |
| V1541 has micro-focused sampler | True |
| V1515 has critical-fast without micro-focused | True |
| V1536/V1541 have sysfs-client enumerate | True |
| critical block skips clk_summary | True |
| critical block reads full clk_summary | False |
| focused block reads full clk_summary | True |
| critical skip line | 1742 |
| focused clk line | 1756 |

## Interpretation

V1544 proves that `clk_summary` is too slow to serve as a precise sub-120ms pre-fail clock trace in the current endpoint-electrical handoff. The PID1 source already has a narrower critical-fast micro sampler that records interrupts, debug GPIO, link-state files, focused regulator lines, and focused pinmux lines while explicitly writing `micro_critical_clk_summary_skipped=1` instead of reading full `/sys/kernel/debug/clk/clk_summary` in the micro loop.

Therefore the next useful live attempt should not repeat V1543 unchanged. It should build a V1541-derived test image that keeps sysfs/client enumerate and case-aligned micro sampling, keeps `micro_critical_fast_endpoint_sampler`, and removes `micro_focused_endpoint_sampler` from the critical micro path.

## V1546 Recommended Contract

| include flag |
| --- |
| --wifi-test-mount-debugfs |
| --wifi-test-auto-readiness-supervisor |
| --wifi-test-pid1-rc1-watcher |
| --wifi-test-rc1-window-sampler |
| --wifi-test-rc1-endpoint-sampler |
| --wifi-test-rc1-micro-endpoint-sampler |
| --wifi-test-rc1-micro-source-timestamped-sampler |
| --wifi-test-rc1-micro-critical-fast-endpoint-sampler |
| --wifi-test-rc1-case-aligned-micro-endpoint-sampler |
| --wifi-test-rc1-sysfs-client-enumerate |

| exclude flag |
| --- |
| --wifi-test-rc1-micro-focused-endpoint-sampler |
| --wifi-test-rc1-micro-batched-focused-endpoint-sampler |
| --wifi-test-rc1-immediate-endpoint-sampler |

## Expected Markers

| present |
| --- |
| micro_critical_fast_endpoint_sampler=1 |
| micro_critical_clk_summary_skipped=1 |
| micro_interrupts |
| micro_debug_gpio |
| micro_pcie1_current_link_state |
| micro_pcie1_link_state |
| micro_critical_regulator |
| micro_critical_pinmux |

| absent |
| --- |
| micro_focused_clk |
| micro_batched_clk |
| immediate_clk |

## Next Gate

- Cycle: `V1546`
- Summary: source/build-only V1541-derived test boot that removes micro-focused clk_summary from the case-aligned micro loop
- Guardrail: no live flash until V1546 artifact sanity passes
- Guardrail: no full clk_summary read in the sub-120ms micro loop
- Guardrail: no PMIC/GPIO/GDSC direct write
- Guardrail: no global PCI rescan or platform bind/unbind
- Guardrail: no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping
- Guardrail: no firmware/MHI/WLFW branch until native L0 and PCI enumeration exist

## Safety Scope

This classifier is host-only. It performs no device command, flash, reboot, partition write, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, global PCI rescan, or platform bind/unbind.
