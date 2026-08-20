# A90 H28 physical-return selftest transport NO_PROOF — 2026-08-21

## Disposition

`NO_PROOF_OBSERVER / RECOVERY_PARKED`.

The separately reviewed H28 physical System-return continuation was authorized
once. Its durable physical intent was published, the operator selected
`TWRP -> Reboot -> System` once on the attended A90, and Native became visible.
The fixed finalizer then durably consumed its sole Native observation. It did
not publish `41-recovery-closed.json` and did not remove either retained guard.
The physical action, candidate, rollback, original TWRP requests, and this
observation are all consumed and are not replayed.

## What was proved

- USB inventory contained exactly one A90 Native `04e8:6861`; the other Samsung
  endpoint remained present but received no command.
- The managed fixed A90 bridge was exact, running, non-ambiguous, and selected
  the fixed A90 by-id endpoint.
- The first Native command returned a complete structural receipt for exact
  V2321 `0.9.285 / v2321-usb-clean-identity-rodata`, kernel
  `4.14.190-25818860-abA908NKSU5EWA3`, and the expected display tuple.
- The physical intent SHA-256 is
  `19377bc18714c7b2b698665a8c9ff96573d3c1fdfb028efba5b86f6b2def9f66`.
- The consumed observation-intent SHA-256 is
  `8f401590bca71575258a2e3d45e1bee6c55fd4e8eeff4c22012fc25f559d05be`.

These facts prove the physical return reached the exact V2321 resident. They
do not satisfy the complete health terminal because selftest was not observed.

## Observer failure

The fixed adapter's `version` producer completed. The immediately following
`selftest` producer emitted zero stdout and zero stderr and failed its bounded
producer contract. The managed bridge capture settles attribution: it records
the host transmission `cmdv1 selftest`, but the device echo reaches only
`cmdv1 selft` before returning to `a90:/#`; no `A90P1 BEGIN`, selftest body, or
`A90P1 END` exists for that command.

The adapter invokes `a90ctl.py` without `--input-mode` and with a minimal
environment that contains no `A90CTL_INPUT_MODE`, so `a90ctl` selected its
default `normal` one-write input. The failure is therefore a truncated serial
command/observer failure, not a selftest contradiction and not evidence of a
V2321 boot or kernel failure. Earlier A90 reports independently document this
same normal-input truncation shape and successful bounded slow-input recovery,
but those historical results are not reused as current health proof.

## Current boundary and next unit

The exact H28 run still has its original nine records only. The sidecar has
both exact intents. The capability-wide active guard and consumed H28 candidate
guard remain. The current finalizer must not be invoked again.

The next unit is host-only observer repair: a new, separately reviewed,
terminal-only reconciler may bind this fixed failed observation and permit one
fresh read-only Native health observation using the already reviewed
`a90ctl --input-mode slow` framing for safe retryable commands. It may send no
ADB, TWRP, reboot, flash, candidate, rollback, partition, or physical-action
command. Only exact V2321 version, selftest `fail=0`, status, target identity,
and other-target preservation may publish recovery closure and remove only the
active guard. Until that capability is reviewed and separately authorized,
the run remains parked.
