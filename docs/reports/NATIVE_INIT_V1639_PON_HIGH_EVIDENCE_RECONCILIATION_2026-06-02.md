# Native Init V1639 PON-high Evidence Reconciliation

## Summary

- Cycle: `V1639`
- Type: host-only evidence reconciliation
- Decision: `v1639-pon-high-inferred-not-promoted`
- Result: PASS
- V1638 strict label: `natural-path-observation-incomplete`
- Evidence: `tmp/wifi/v1638-natural-path-mdm2ap-irq-summary-handoff`

## Finding

- V1638 captured esoc0 provider entry, GPIO1270/PON low/assert, GPIO135/AP2MDM assert, and complete zero IRQ deltas for GPIO142/MDM2AP plus mdm errfatal.
- V1638 did not capture an explicit GPIO1270/PON high/de-assert trace marker, so the strict contract label remains incomplete.
- Source order still matters: `mdm4x_do_first_power_on()` calls soft-reset/PON first, then waits, then drives AP2MDM high. Therefore the observed AP2MDM high is downstream of the PON de-assert path, but this is an inference rather than the explicit trace marker required by the live contract.

## Evidence Timing

- esoc0 PIL time: `9.142394`
- GPIO1270/PON low time: `9.14251`
- GPIO1270/PON high trace time: `None`
- GPIO135/AP2MDM high time: `9.480079`
- PON-low to AP2MDM delta ms: `337.569`

## IRQ Discriminator

- GPIO142/MDM2AP IRQ delta: `0`
- mdm errfatal IRQ delta: `0`
- sample count: `120`
- parsed flags ok: `True`
- safety markers zero: `True`

## Source Contract

- source present: `True`
- PON assert sleep 120-180 ms present: `True`
- post-PON sleep 150 ms present: `True`
- AP2MDM after sleep present: `True`
- ESOC_REQ_IMG queue present: `True`
- provider regulator code absent: `True`

## Classification

- PON high inferred from source order: `True`
- promote to `mdm2ap-silent-natural-path`: `False`
- reason: PON de-assert is source-order inferred before AP2MDM, but the live contract required an explicit GPIO1270 high/de-assert trace marker.

## Next Gate

No live mutation was performed. Do not spin another timing/window variant from this result. The next Wi-Fi-relevant blocker is below the natural eSoC path: a separately decided bounded modem-rail/PMIC investigation plan, with source/build-only and read-only preflight first, then explicit write-gate separation if selected.
