# S22+ FYG8 P2.58A entrypoint-contract incident

Date: 2026-07-25 KST

## Boundary

H0 host-only. No device contact, Odin invocation, manifest binding, approval,
or flash occurred.

## Symptom

Two clean Full-LTO builds, six-artifact reproducibility, linked audit,
two-link userspace build, and two deterministic boot-only packages passed.
The independent candidate checker then stopped with:

```text
E2 candidate executable entrypoint mismatch
```

The exact P2.58A `/init` entrypoint is `0x401580`; its child remains
`0x4000cc`. The P2.58A stock-closure adapter inherited P2.57's
`0x4014f0` `/init` value. File size equality did not imply entrypoint equality.

## Analysis

This was a strict false negative in a source-bound host proof adapter, not a
kernel compile failure or package corruption. A temporary downstream checker
scope made the independent check pass, but Process v2 promotion and the common
evidence verifier call the same stock-closure adapter independently. Keeping
that shim would create multiple verification semantics, so it was discarded.

Because the stock-closure adapter is included in the candidate source
preimage, correcting it changes the derived run ID and final candidate config
patch. The already-built candidate remains useful host evidence but cannot be
promoted under the corrected contract. A fresh intent and two clean Full-LTO
builds are required.

## Correction

P2.58A now owns an isolated legacy stock-closure instance with exact
entrypoints:

```text
init  = 0x401580
child = 0x4000cc
```

All three P2.58A consumers use that scoped instance:

- candidate generic-rootfs audit;
- effective rootfs audit; and
- effective-rootfs validation.

The P2.53/P2.57 isolated checker is restored after success and exception paths,
so historical contracts retain `0x4014f0`.

## Recurrence Controls

1. The P2.58A source contract requires the scoped entrypoint adapter markers.
2. Tests cover all three consumers and exception-path restoration.
3. A prebuild test creates the exact P2.58A intent, links userspace twice,
   inspects both ELF files, and compares their entrypoints with the selected
   closure before Full LTO.
4. The qualification runbook now places this userspace/closure check before
   kernel build A.
5. A downstream-only compatibility shim is explicitly rejected because
   static checking, promotion, and evidence verification must share one
   source of truth.

## Status

The source correction and focused H0 tests pass. The previous P2.58A candidate
is not live-authorized and is not promotable. Next is a fresh intent followed
by the normal clean A/B qualification sequence.
