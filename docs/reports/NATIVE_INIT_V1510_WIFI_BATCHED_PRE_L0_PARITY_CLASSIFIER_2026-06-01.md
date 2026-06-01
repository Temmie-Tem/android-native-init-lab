# Native Init V1510 Wi-Fi Batched Pre-L0 Parity Classifier

## Summary

- Cycle: `V1510`
- Type: host-only classifier over V1509 live handoff evidence
- Decision: `v1510-batched-pre-l0-improves-sampling-but-source-timestamps-needed`
- Result: PASS
- Reason: V1509 batched evidence preserves the RC1 no-L0 failure classification and captures first-sample pre-link-fail state, but per-source timestamps are still missing
- Evidence: `tmp/wifi/v1509-wifi-batched-pre-l0-parity-handoff`

## Handoff Result

- V1509 decision: `v1509-test-boot-downstream-progress-rollback-pass`
- handoff pass: `True`
- rollback ok: `True`
- progress decision: `rc1-ltssm-link-failed-no-l0`
- RC1 progress/link failed/L0: `True/True/False`
- MHI/WLFW/BDF/FW-ready/wlan0: `False/False/False/False/False`

## Batched Focused Reads

- labels present: `9` / `9`
- batched marker present for every label: `True`
- `pcie_1_gdsc` off for every label: `True`
- PCIe1 batched clocks off for every label: `True`
- refgen clocks available for every label: `True`
- GPIO102/103/104/135/142 expected for every label: `True`
- GPIO142 mdm-status IRQ stays zero: `True`
- pinmux lines present for every label: `True`
- pinconf lines present for every label: `True`

## Timing Caveat

- link failed after TEST:11 case: `114.796` ms
- first sample actual micro elapsed: `0` ms
- second sample actual micro elapsed: `148` ms
- max sample actual micro elapsed: `1101` ms
- first sample starts before link fail: `True`
- second sample starts after link fail: `True`
- improved versus V1505 exact scanner: `True`
- still overruns nominal micro window: `True`
- per-source timestamps missing: `True`

V1509 is materially faster than V1505 because each debugfs source is read once per sample. It is still not a source-exact first-150ms proof: the first sample starts at case+0ms, but it reads several sources without per-source begin/end timestamps, while the second sample starts after the RC1 link-fail marker.

## Dmesg Classification

- LTSSM states: `LTSSM_DETECT_QUIET, LTSSM_POLL_ACTIVE, LTSSM_POLL_COMPLIANCE`
- case after esoc0: `36.64` ms
- PHY ready after case: `5.858` ms
- link failed after case: `114.796` ms
- link failed marker: `True`
- L0/MHI/WLFW/BDF/FW-ready/wlan0: `False/False/False/False/False/False`

## Interpretation

V1509 keeps the current blocker fixed at `rc1-ltssm-link-failed-no-l0`. The batched sample shows the same pre-L0 endpoint-response symptoms: `pcie_1_gdsc` and PCIe1 clocks stay off, refgen remains available, GPIO135/GPIO142 stay inactive, and GPIO142 IRQ does not fire. Firmware, MHI, WLFW, BDF, FW-ready, wlan0, scan/connect, and network tests remain downstream and should stay parked until RC1 reaches L0 and PCI enumeration exists.

## Safety Scope

This classifier is host-only. It performs no device command, flash, reboot, partition write, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE` spoof, global PCI rescan, or platform bind/unbind.

## Next

- V1511 should add source begin/end timestamps to the batched sampler or narrow the capture to the minimum critical sources.
- Keep firmware/MHI/WLFW/scan/connect work parked until RC1 L0 and PCI enumeration exist.
