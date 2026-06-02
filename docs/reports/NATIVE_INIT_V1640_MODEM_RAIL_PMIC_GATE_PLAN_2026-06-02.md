# Native Init V1640 Modem-rail / PMIC Gate Plan

## Summary

- Cycle: `V1640`
- Type: host-only next-gate plan
- Decision: `v1640-modem-rail-pmic-gate-plan-ready`
- Result: PASS
- Reason: V1638/V1639 leave the Wi-Fi blocker below the natural eSoC provider path; next progress requires identifying a bounded modem-rail or power prerequisite before any write gate.

## Current Evidence Boundary

- V1638 returned to the v724 baseline and selftest `fail=0`.
- V1638 captured natural esoc0 provider entry, GPIO1270/PON low, GPIO135/AP2MDM high, GPIO142/MDM2AP IRQ delta `0`, mdm errfatal IRQ delta `0`, sample count `120`, and safety markers all zero.
- V1638 strict label remains `natural-path-observation-incomplete` because explicit GPIO1270/PON high was not traced.
- V1639 host-only reconciliation shows AP2MDM high is source-order downstream of the PON de-assert path, but intentionally does not promote the live label to `mdm2ap-silent-natural-path`.

## Closed / Rejected Paths

- Do not retry timing/window variants only to chase the missing PON-high trace marker.
- Do not use forced RC1 enumerate, pci-msm case writes, PCI rescan, or platform bind/unbind as the next trigger.
- Do not spoof ONLINE/system-info or issue eSoC notify/`BOOT_DONE`.
- Do not directly request/hold PMIC GPIO9 from userspace; V1262/V1263/V1276/V1355 already classify it as kernel-owned and parity-correct.
- Do not treat `pcie_1_gdsc 0mV` text alone as physical rail proof; prior classifiers showed debugfs regulator visibility is useful but not sufficient as a write target.
- Do not start Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping until lower readiness reaches at least MDM2AP/RC1/MHI/WLFW progress.

## Next Gate: V1641 Host-only Rail / Control Inventory

V1641 should produce a write-target candidate table, not perform a live mutation.

Inputs:

- V1638/V1639 natural-path evidence and strict-label caveat.
- `ESOC_PON_SOURCE_ANALYSIS_2026-06-02.md` and `ESOC_DTB_PARITY_2026-06-02.md`.
- Existing PMIC/GPIO/PCIe reports: V1244, V1252, V1263, V1276, V1306, V1355, V1554, V1559, V1560.
- OSRC source for `drivers/esoc`, `msm_pcie`, regulator/clock users, and A90 DTS/DTBO-derived modem/PCIe nodes.

Required output columns:

| candidate | class | current evidence | write surface | rollback risk | allowed next action |
|---|---|---|---|---|---|
| PM8150L GPIO9/PON | eSoC provider GPIO | parity-correct, kernel-owned | reject direct userspace line request | high if misused | read-only only |
| GPIO135/AP2MDM | eSoC provider GPIO | natural path reaches AP2MDM | reject direct write | high | read-only only |
| GPIO142/MDM2AP | modem response input | IRQ delta remains 0 | no write | n/a | observe only |
| GPIO141/errfatal | modem response input | IRQ delta remains 0 | no write | n/a | observe only |
| pcie1 GDSC / clocks / refclk | AP-side PCIe prerequisite | diagnostic only; downstream of endpoint response in current contract | reject blind enable | medium/high | source/static ownership analysis |
| unknown SDX50M main rail | suspected missing prerequisite | not identified on disk | unknown | high | identify owner before write |

V1641 success criteria:

- Names every plausible SDX50M power prerequisite with evidence class: closed, observe-only, candidate, or rejected.
- Identifies whether any candidate has a kernel-owned, rollbackable, narrow control surface.
- Separates source/static analysis from live write approval.
- Produces a fail-closed recommendation for V1642: either more host-only source analysis or a read-only live preflight. No write gate yet.

## If V1641 Finds a Candidate

Only then define a separate bounded write gate with these minimum requirements:

1. source/build-only helper or test boot first;
2. artifact sanity and forbidden-marker scan;
3. rollback image fixed to `stage3/boot_linux_v724.img`;
4. bounded timeout and cleanup path;
5. discriminator limited to MDM2AP/GPIO142 IRQ delta, errfatal IRQ delta, RC1/MHI/WLFW appearance, and rollback selftest;
6. no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping in the same write gate.

## Safety Scope

V1640 is host-only. It performs no device command, flash, reboot, partition write, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE` spoof, pci-msm debugfs write, global PCI rescan, or platform bind/unbind.
