# A90 Phase 2D V3406 Display F1 Preparation Plan

Date: 2026-07-31
Target: Galaxy A90 5G native-init profile only
Risk posture: H0 implementation, then one bounded D0; F1 remains separately gated

## Objective

Prepare one fresh V3406 transaction that can prove Debian direct-DRM
acquisition after `switch_root`, pause for an attended visible confirmation,
and always return through the exact V2321 boot-only rollback path. Native-init
releases KMS and supplies the immutable handoff; Debian owns the steady-state
display.

## Selected sequence

1. Freeze and independently review the execution-critical host closure.
2. Commit the reviewed machinery before generating run-bound private evidence.
3. Materialize one new-inode keyed copy from the exact clean Phase 2B 2 GiB
   ext4 image. Keep the clean source byte-identical.
4. Perform one exact A90 D0 read-only preflight:
   baseline version/build and self-test, zero retained pstore entries, and
   absence of the run-derived final/work/stage paths.
5. Finalize one immutable V3406 manifest from the keyed receipt, D0 evidence,
   canonical Phase 2 candidate, canonical V2321 rollback, current source
   closure, and independent review report.
6. Prepare the host-only approval receipt and stop at the exact
   `A90-F1-V2-APPROVE:<sha256>` gate.
7. Only a fresh exact operator token may start F1. Candidate start activates
   the already-bound mandatory rollback; candidate replay is forbidden.

## Display proof

Mechanical proof requires the native release marker, Debian PID 1, exact DRM
device and sole-owner state, UID/GID 3904, zero effective capabilities,
no-new-privileges, and the ready marker from the bound presenter. The attended
receipt additionally binds these exact visible strings:

- `A90 DEBIAN`
- `DIRECT DRM SESSION`
- `PID 1: SYSVINIT / VT: NONE`
- `DISPLAY OWNER: DEBIAN`

Ready pauses before rollback for the bounded visible-confirmation window.
Attempt-3 terminal failure, malformed evidence, timeout, or missing proof is
`NO_PROOF` and proceeds to rollback without candidate replay.

## Fail-closed conditions

- Any mismatch in current keyer, connected-preflight helper, staging adapter,
  orchestrator, flash runner, candidate, rollback, keyed image, or evidence
  hash.
- Any reused run directory, pre-existing private output, non-regular input,
  direct symbolic link, or non-new-inode boot/rootfs copy.
- Any ambiguity in A90 target selection, baseline health, recovery identity,
  or final/work/stage path absence.
- Any request for live execution without the exact final approval token.

S22+ evidence, identity, authority, and tooling state are not inputs to this
transaction.
