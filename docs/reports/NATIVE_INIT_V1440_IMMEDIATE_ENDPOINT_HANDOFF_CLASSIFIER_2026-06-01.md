# Native Init V1440 Immediate Endpoint Handoff Classifier

## Summary

- Cycle: `V1440`
- Type: host-only classifier over V1439 immediate endpoint evidence
- Decision: `v1440-immediate-sampler-too-slow-no-l0`
- Result: PASS
- Reason: V1439 confirmed no L0/MHI/WLFW/wlan0, but debugfs exact immediate samples take seconds and cannot resolve the sub-100ms RC1 active window

## Inputs

- Manifest: `tmp/wifi/v1439-wifi-test-boot-immediate-endpoint-handoff/manifest.json`
- Window: `tmp/wifi/v1439-wifi-test-boot-immediate-endpoint-handoff/test-rc1-window-result.stdout.txt`
- Dmesg: `tmp/wifi/v1439-wifi-test-boot-immediate-endpoint-handoff/test-v1393-dmesg.stdout.txt`
- Watcher: `tmp/wifi/v1439-wifi-test-boot-immediate-endpoint-handoff/test-v1393-rc1-watcher-result.stdout.txt`

## Observations

| Signal | Value |
| --- | --- |
| handoff pass | `True` |
| rollback | `{'attempt': 'from-native', 'ok': True}` |
| corrected RC1 write triggered | `True` |
| immediate labels | `['after_case_0ms', 'after_case_1ms', 'after_case_5ms', 'after_case_20ms']` |
| immediate elapsed ms | `{'after_case_0ms': 0, 'after_case_1ms': 2402, 'after_case_5ms': 5499, 'after_case_20ms': 8634}` |
| samples too slow for RC1 window | `True` |
| after-case-0 `pcie_1_gdsc` enable | `0` |
| all immediate pcie1 GDSC off | `True` |
| all immediate pcie1 clocks off | `True` |
| GPIO103/CLKREQ high | `True` |
| GPIO142/MDM2AP low | `True` |
| link failed | `True` |
| L0 seen | `False` |
| downstream absent | `True` |

## Classification

V1439 still fails before `LTSSM L0`; no MHI, WLFW, BDF, FW-ready, or
`wlan0` appears. The immediate exact sampler does not solve the timing
problem because scanning debugfs regulator/clock summaries is slower
than the RC1 active window. The `after_case_1ms` label appears at
`2402ms` immediate elapsed, and `after_case_20ms` appears at `8634ms`.

The useful next change is not Wi-Fi HAL/scan/connect. It is a source-only
test-boot instrumentation change: use a concurrent writer plus a minimal
fast reader, or remove slow summary scans from the active RC1 window.

## Safety Scope

This cycle was host-only. It did not run device commands, flash, reboot,
write partitions, handle credentials, scan/connect Wi-Fi, run DHCP/routes,
ping externally, write PMIC/GPIO/GDSC controls, spoof eSoC notify/
`BOOT_DONE`, run global PCI rescan, or bind/unbind platform devices.
