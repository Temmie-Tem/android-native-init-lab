# Native Init V1476 Lower-Intervention Design Gate

## Summary

- Cycle: `V1476`
- Type: host-only design review
- Decision: `v1476-select-ap2mdm-bounded-hold-test-boot-design`
- Goal: choose the next rollbackable Wi-Fi test-boot experiment after V1475
- Result: design-only; no device command, build, flash, or live mutation

## Current Proven Boundary

V1475 closes the short-window explanation. The V1472/V1474 Wi-Fi test boot
reaches the modem and esoc0 provider triggers and captures the AP2MDM set-high
tracepoint, but the effective lower response remains absent:

- GPIO135/AP2MDM set-high tracepoint appears.
- GPIO135 still samples low across the extended provider window.
- GPIO142/MDM2AP still samples low.
- mdm3 pinmux ownership for GPIO135/GPIO142 is present.
- pcie1 GDSC remains `0mV` and the pcie1 pipe clock remains zero-enabled.
- RC1/MHI/WLFW/BDF/FW-ready/`wlan0` remain absent.

This is below Wi-Fi HAL, scan/connect, credential handling, DHCP/routes, and
external ping readiness.

## Candidate Review

| Candidate | Verdict | Reason |
| --- | --- | --- |
| Start Wi-Fi HAL or credentials in test boot | reject | `wlan0` is absent; upper Wi-Fi actions cannot succeed and would expand risk before lower readiness. |
| Repeat corrected RC1 `rc_sel=2` + `case=11` only | reject as next step | V1370/V1372/V1391/V1447 already prove RC1 can enter LTSSM but fails before L0 without GPIO142/MDM2AP. |
| Direct PMIC GPIO1270/PON write | reject as next step | Provider already emits PON low/high activity; V1475 gap is AP2MDM effective level plus no MDM2AP response. |
| Direct GDSC/clock write | reject as next step | Prior corrected RC1 path can transiently enable pcie1, but endpoint still fails before L0; unspecific clock/GDSC writes are too broad. |
| Blind eSoC notify/`BOOT_DONE` | reject | Previous controls show downstream spoofing without real MDM2AP/MHI is not useful and can corrupt state. |
| Bounded AP2MDM effective-hold test boot | select | It targets the exact remaining contradiction: provider calls AP2MDM high, but effective readback stays low. |

## Selected V1477+ Path

Build a separate rollbackable Wi-Fi test boot that keeps main v724 unchanged and
adds one opt-in lower intervention after the existing provider trigger is
observed:

1. Boot as a `wifitest` image only.
2. Arm the existing tracefs GPIO/PIL sampler and lightweight GPIO135/GPIO142
   readback.
3. Wait for the exact esoc0 provider trigger and AP2MDM set-high trace.
4. Confirm GPIO135 still reads low before any direct line action.
5. Attempt a bounded AP2MDM hold only through the narrowest available userspace
   GPIO interface, fail-closed if the line is busy/unavailable.
6. Hold only for a short fixed window while sampling GPIO135, GPIO142 IRQ/state,
   pcie1 GDSC/pipe clock, LTSSM, PCI/MHI, WLFW/BDF/FW-ready, and `wlan0`.
7. Release the hold, record cleanup result, persist evidence, then rely on the
   existing rollback handoff to restore `stage3/boot_linux_v724.img`.

The first implementation unit should be source/build-only. The first live unit
must be a rollbackable handoff with explicit timeout and cleanup evidence.

## Success Criteria

The experiment is useful if it proves at least one of these:

- GPIO135 can be made to read high during the bounded hold.
- GPIO142/MDM2AP IRQ or state changes after GPIO135 is effectively high.
- pcie1 reaches LTSSM activity or L0 from the provider/AP2MDM window.
- PCI/MHI, WLFW/BDF/FW-ready, or `wlan0` appears.
- The userspace GPIO path is refused or ineffective cleanly, proving that a
  kernel-side provider/kernel patch would be required instead.

## Failure Criteria

- Device fails to return to v724 with selftest `fail=0`.
- GPIO135 cannot be released or cleanup cannot be proven.
- Transport loss occurs without rollback evidence.
- Unexpected Wi-Fi HAL, scan/connect, credential use, DHCP/routes, external
  ping, global PCI rescan, platform bind/unbind, or blind eSoC notify occurs.
- Any non-target GPIO/PMIC/GDSC write is observed.

## Hard Exclusions

Until a dedicated live handoff is built and verified, keep these prohibited:

- Wi-Fi HAL start, scan/connect, credentials, DHCP/routes, external ping.
- Direct PMIC GPIO1270/PON writes.
- Direct pcie1 GDSC/clock writes.
- Blind eSoC notify/`BOOT_DONE`.
- Global PCI rescan.
- Platform bind/unbind.
- Boot image or partition writes outside the rollbackable test-boot handoff.

## Next

V1477 should be source/build-only: add the AP2MDM bounded-hold test-boot mode
behind an explicit compile-time flag and artifact marker. V1478 should be
local-only artifact sanity. V1479 may be the first rollbackable live handoff if
V1477/V1478 pass.
