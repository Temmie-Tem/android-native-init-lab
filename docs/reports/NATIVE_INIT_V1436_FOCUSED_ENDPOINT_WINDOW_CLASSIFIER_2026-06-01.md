# Native Init V1436 Focused Endpoint Window Classifier

## Summary

- Cycle: `V1436`
- Type: host-only classifier over V1435 focused endpoint evidence
- Decision: `v1436-focused-window-race-endpoint-no-l0`
- Result: PASS
- Reason: V1435 proves corrected RC1 still fails before L0; focused exact lines confirm endpoint no-response, but pre-RC1 GDSC/clock reads are too timing-sensitive for a stable single-sample conclusion

## Inputs

- Manifest: `tmp/wifi/v1435-wifi-test-boot-focused-endpoint-handoff/manifest.json`
- Window: `tmp/wifi/v1435-wifi-test-boot-focused-endpoint-handoff/test-rc1-window-result.stdout.txt`
- Dmesg: `tmp/wifi/v1435-wifi-test-boot-focused-endpoint-handoff/test-v1393-dmesg.stdout.txt`

## Observations

| Signal | Value |
| --- | --- |
| focused sampler seen | `True` |
| pre-delay sample lines | `108` |
| pre-RC1 sample lines | `108` |
| post-50ms sample lines | `108` |
| post-150ms sample lines | `108` |
| post-500ms sample lines | `108` |
| broad pre-RC1 `pcie_1_gdsc` enable | `1` |
| focused pre-RC1 `pcie_1_gdsc` enable | `0` |
| focused post-50ms `pcie_1_gdsc` enable | `0` |
| focused post-500ms `pcie_1_gdsc` enable | `0` |
| broad pre-RC1 pcie1 clocks enabled | `True` |
| focused pre-RC1 pcie1 clocks enabled | `False` |
| focused post-50ms pcie1 clocks enabled | `False` |
| focused post-500ms pcie1 clocks enabled | `False` |
| same-window timing race | `True` |
| GPIO103/CLKREQ high in all samples | `True` |
| GPIO142/MDM2AP low in all samples | `True` |
| GPIO102/PERST owned by RC1 | `True` |
| GPIO103 pci_e1 function seen | `True` |
| link failed | `True` |
| L0 seen | `False` |
| downstream absent | `True` |
| post-failure pcie1 off | `True` |

## Classification

V1435 confirms the current native path reaches the corrected RC1/LTSSM
window but still fails before `LTSSM L0`. No MHI, WLFW, BDF, FW-ready,
or `wlan0` evidence appears, so Wi-Fi scan/connect remains out of
scope.

The focused sampler improves the signal quality by emitting exact pcie1
regulator, clock, GPIO, pinmux, and pinconf lines. It also shows that
the `pre_rc1` window is still too wide for a stable one-read conclusion:
the broad pass saw pcie1 GDSC/clocks enabled, while later focused exact
reads in the same logical sample saw them already disabled. The next
instrumentation should sample the exact fields immediately around the
`case=11` write inside the PID1 test-boot process, or compare against an
Android positive reference, before changing lower hardware controls.

## Next

- Preferred V1437: source/build-only tighter in-PID1 around-write sampler
  for pcie1 GDSC/clocks, PERST/CLKREQ/WAKE/MDM2AP, and LTSSM.
- Alternative: Android-side positive reference capture for the same exact
  fields around the known-good L0 path.
- Do not proceed to Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or
  external ping until at least L0/MHI/WLFW/`wlan0` progress exists.

## Safety Scope

This cycle was host-only. It did not run device commands, flash, reboot,
write partitions, handle credentials, scan/connect Wi-Fi, run DHCP/routes,
ping externally, write PMIC/GPIO/GDSC controls, spoof eSoC notify/
`BOOT_DONE`, run global PCI rescan, or bind/unbind platform devices.
