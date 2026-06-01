# Native Init V1432 Endpoint Window Classifier

## Summary

- Cycle: `V1432`
- Type: host-only classifier over V1431 endpoint-sampler evidence
- Decision: `v1432-ap-rc1-prereqs-toggle-but-endpoint-no-l0`
- Result: PASS
- Reason: V1431 shows AP-side pcie1 GDSC/clocks toggle in the corrected-RC1 window, but the endpoint still never reaches L0

## Inputs

- Manifest: `tmp/wifi/v1431-wifi-test-boot-endpoint-prereq-handoff/manifest.json`
- Window: `tmp/wifi/v1431-wifi-test-boot-endpoint-prereq-handoff/test-rc1-window-result.stdout.txt`
- Dmesg: `tmp/wifi/v1431-wifi-test-boot-endpoint-prereq-handoff/test-v1393-dmesg.stdout.txt`

## Observations

| Signal | Value |
| --- | --- |
| endpoint sampler seen | `True` |
| sample count | `5` |
| pre-delay `pcie_1_gdsc` enable | `0` |
| pre-RC1 `pcie_1_gdsc` enable | `1` |
| post-50ms `pcie_1_gdsc` enable | `0` |
| post-500ms `pcie_1_gdsc` enable | `0` |
| pre-RC1 pcie1 clocks enabled | `True` |
| post-50ms pcie1 clocks enabled | `False` |
| post-500ms pcie1 clocks enabled | `False` |
| GPIO103/CLKREQ high | `True` |
| link failed | `True` |
| L0 seen | `False` |
| downstream absent | `True` |

## Classification

V1431 no longer supports the broad claim that pcie1 never powers in the
test window. The corrected-RC1 path briefly enables the AP-side pcie1
GDSC/clock set, then disables it again after the endpoint fails before
L0. GPIO103/CLKREQ is high/pull-up in the same window. The remaining
gap is therefore narrower: endpoint response/parity at PERST release,
not another blind RC1 retry or direct GDSC/PMIC/GPIO write.

## Next

V1433 should stay host/source-only first. Two useful options are:

1. refine the native endpoint sampler to avoid clock-summary truncation
   and emit exact pcie1 clock/GDSC/PERST/CLKREQ fields; or
2. capture an Android-side pcie1 clock/GDSC/CLKREQ reference for the
   known-good L0 path, then compare against V1431.

Do not proceed to scan/connect, credentials, DHCP/routes, or external
ping until at least L0/MHI/WLFW/`wlan0` progress exists.

## Safety Scope

This cycle was host-only. It did not run device commands, flash, reboot,
write partitions, handle credentials, scan/connect Wi-Fi, run DHCP/routes,
ping externally, write PMIC/GPIO/GDSC controls, spoof eSoC notify/
`BOOT_DONE`, run global PCI rescan, or bind/unbind platform devices.
