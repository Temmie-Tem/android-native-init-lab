# Native Init V1638 Natural-path MDM2AP IRQ Summary Handoff

## Summary

- Cycle: `V1638`
- Type: one-run rollbackable natural-path live observation
- Decision: `v1638-natural-path-observation-incomplete`
- Result: BLOCKED
- Contract label: `natural-path-observation-incomplete`
- Reason: rollback verified but required provider/PON/AP2MDM/timing evidence was incomplete
- Evidence: `tmp/wifi/v1638-natural-path-mdm2ap-irq-summary-handoff`
- Test boot image: `tmp/wifi/v1636-natural-path-mdm2ap-irq-summary-test-boot/boot_linux_v1636_natural_mdm2ap_irq_summary.img`
- Rollback image: `stage3/boot_linux_v724.img`
- Rollback ok: `True`

## Contract Checks

- `provider_trigger_seen`: `True`
- `pil_esoc_seen`: `True`
- `pon_low_seen`: `True`
- `pon_high_seen`: `False`
- `ap2mdm_seen`: `True`
- `gpio142_trace_seen`: `False`
- `gpio142_irq_delta`: `0`
- `errfatal_irq_delta`: `0`
- `gpio142_irq_initial_parsed`: `True`
- `errfatal_irq_initial_parsed`: `True`
- `mdm_status_zero_sample_count`: `14`
- `errfatal_zero_sample_count`: `1`
- `gpio142_low_sample_count`: `14`
- `limited_silent_window_evidence`: `True`
- `timing_powerup_seen`: `True`
- `timing_complete`: `True`
- `sample_count`: `120`
- `safety_zero`: `True`
- `forbidden_markers_seen`: `[]`

## Downstream Context

- `pcie_rc1_transition_seen`: `0`
- `mhi_bus_max`: `0`
- `wlfw_kmsg_max`: `0`
- `wlan0_seen`: `0`

## Interpretation

- Rollback is verified and the device returned to the v724 baseline with selftest `fail=0`.
- The natural provider path did trigger: esoc0 PIL was observed, GPIO1270/PON was driven low, and GPIO135/AP2MDM was asserted.
- The required IRQ discriminator was collected: GPIO142/MDM2AP IRQ delta `0`, mdm errfatal IRQ delta `0`, parsed flags `True`, and sample count `120`.
- The strict contract label is still `natural-path-observation-incomplete` because this run did not capture an explicit GPIO1270/PON high/de-assert trace marker in the window result.
- Evidence strongly suggests the modem stayed silent after the natural path, but the report intentionally does not promote this to `mdm2ap-silent-natural-path` without the full PON low->high trace required by the contract.

## Safety Scope

This run observes the natural `__subsystem_get(esoc0)` provider path only.
It does not force RC1 enumerate, write pci-msm debugfs case values, spoof
ONLINE/system-info, write PMIC/GPIO/GDSC/regulator state, issue eSoC
notify/`BOOT_DONE`, rescan PCI, bind/unbind platforms, start Wi-Fi HAL,
scan/connect, use credentials, run DHCP/routes, or external ping.

## Next

Stop here for handoff. Do not run timing/window variants or enter modem-rail/PMIC write gates from this result without a separate decision.
