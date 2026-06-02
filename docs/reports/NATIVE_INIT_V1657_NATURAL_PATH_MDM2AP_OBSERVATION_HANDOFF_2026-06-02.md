# Native Init V1657 Natural-path MDM2AP Observation Handoff

## Summary

- Cycle: `V1657`
- Type: one-run rollbackable natural-path live observation
- Decision: `v1657-mdm2ap-silent-natural-path`
- Result: PASS
- Contract label: `mdm2ap-silent-natural-path`
- Reason: rollback verified, provider/PON/AP2MDM natural path was observed, and GPIO142/errfatal stayed silent
- Evidence: `tmp/wifi/v1657-natural-path-mdm2ap-observation-handoff`
- Test boot image: `tmp/wifi/v1636-natural-path-mdm2ap-irq-summary-test-boot/boot_linux_v1636_natural_mdm2ap_irq_summary.img`
- Rollback image: `stage3/boot_linux_v724.img`
- Rollback ok: `True`

## Contract Checks

- `provider_trigger_seen`: `True`
- `pil_esoc_seen`: `True`
- `pon_low_seen`: `True`
- `pon_high_seen`: `True`
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

## Safety Scope

This run observes the natural `__subsystem_get(esoc0)` provider path only.
It does not force RC1 enumerate, write pci-msm debugfs case values, spoof
ONLINE/system-info, write PMIC/GPIO/GDSC/regulator state, issue eSoC
notify/`BOOT_DONE`, rescan PCI, bind/unbind platforms, start Wi-Fi HAL,
scan/connect, use credentials, run DHCP/routes, or external ping.

## Next

STOP before modem-rail/PMIC writes.  The natural provider/PON/AP2MDM path ran and MDM2AP stayed silent with complete IRQ-delta evidence.
