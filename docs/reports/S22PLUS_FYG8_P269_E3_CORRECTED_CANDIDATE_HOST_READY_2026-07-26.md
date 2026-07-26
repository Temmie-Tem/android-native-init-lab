# S22+ FYG8 P2.69 corrected E3 candidate host-ready

Date: 2026-07-26 KST

Scope: H0 host-only. No device contact, D0, approval, Odin session, transfer,
reboot, or device write occurred.

> **Superseded before D0:** P2.70 exact generic-arm64 QEMU execution found a
> deterministic configfs link creation/readback defect in this frozen
> candidate. Its AP and host-ready bundle remain immutable but are retired
> from D0 and F1 use.

## Result

The corrected P2.60 E3 ACM-banner candidate completed the full host
qualification line:

- fresh source-bound intent and materialized sources;
- exact userspace semantic rehearsal;
- clean Full-LTO Build A in `40:43.23`;
- clean Full-LTO Build B in `40:45.31`;
- no swap and peak RSS near 24.25 GiB in both builds;
- byte equality for `.config`, `Image`, `System.map`, `abi.xml`, `vmlinux`,
  and `vmlinux.symvers`;
- versioned linked audit;
- two byte-identical boot-only package runs;
- independent candidate closure; and
- offline Process v2 promotion plus ready-bundle validation.

This is host readiness only. It does not prove configfs mount, gadget
creation, `ttyGS0`, ACM enumeration, or banner receipt on the S22+.

## Downstream terminal-stage incident

The first generated Process v2 manifest said terminal stage `0x8f`.
That value belongs to the proven legacy E2 sequence. P2.60 adds eight E3-local
stages `0x88..0x8f` and terminates at `0x90`.

The kernel contract and P2.60 decoder already used `0x90`. Two host consumers
instead read the shared legacy model's `PROFILE_TERMINALS["E2"]`:

1. Process v2 run-manifest construction; and
2. typed acceptance validation.

If left in place, a real P2.60 terminal-success record at `0x90` would have
been rejected after the live run. The bug was found before D0 and before any
approval or device action.

The stale host outputs were moved to a rejected private directory. Kernel,
`/init`, boot image, candidate AP, and both immutable Full-LTO bundles were
preserved because none of their input bytes changed.

## Correction and validation

One version-aware terminal selector now serves both consumers:

- a decoder-owned terminal is authoritative for versioned contracts;
- legacy profiles fall back to their existing model terminal; and
- malformed or out-of-byte-range terminals fail closed.

Validation proves:

- legacy E2 remains terminal `0x8f`;
- P2.60 E3 requires terminal `0x90`;
- 28 Process v2 promotion tests pass;
- 17 typed-evidence tests pass;
- Python compilation passes;
- the regenerated ready bundle verifies with terminal `0x90`; and
- mutating its P2.60 acceptance back to `0x8f` is rejected.

This is the build-runbook rule: a downstream host consumer failure does not
invalidate immutable kernel artifacts. Resume from the earliest invalid
boundary.

## Generic ARM64 QEMU assessment

A complete S22+ SoC emulator is not justified. Reproducing Qualcomm SM8450
clock, RPMh, interconnect, PHY, Type-C, and Samsung PMIC behavior would become
a separate platform project and would still not replace F1.

A bounded generic ARM64 QEMU harness is useful as a later H0 regression tool.
It should boot a stock generic ARM64 kernel with configfs, libcomposite,
dummy-hcd, and gadget serial support, then run the exact native `/init` E3
sequence. It can validate:

- real configfs mount and `statfs` semantics;
- gadget directory, descriptor, string, and function construction;
- configfs symlink and UDC binding order;
- `ttyGS0` appearance, termios setup, and exact banner bytes; and
- teardown/error behavior without consuming an F1 cycle.

It cannot validate the remaining target-specific boundary:

- Qualcomm DWC3-MSM bind and peripheral-role behavior;
- SS/HS/eUSB2 PHY and repeater behavior;
- VBUS, Type-C, and Samsung notifier interaction; or
- physical USB host enumeration on this S22+.

Therefore the harness is a reusable semantic pre-LTO test, not a device-proof
substitute. P2.70 implemented it before D0 and it exposed a concrete defect in
this frozen candidate.

## Next attended action

Do not run D0 or F1 with this candidate. Continue from P2.70's corrected source
identity and repeat the required host qualification line first.
