# S22+ FYG8 R4W1-E0 Process v2 typed evidence

Date: 2026-07-22 KST
Scope: H0 host-only
Status: exact offline contract and retained classifier integrated

## Verdict

`PASS_R4W1E0_PROCESS_V2_TYPED_EVIDENCE_HOST_CONTRACT`

The common Process v2 verifier and observer now accept one new typed evidence
kind for the exact R4W1-E0 candidate. No candidate-specific runner, transport,
journal state, recovery branch, or approval path was added.

## Exact binding

The draft manifest pins the boot-only candidate AP, known Magisk rollback AP,
fixed probe ID, ENTRY marker, USERSPACE marker, run manifest, and independent
static-check result. Offline verification requires the exact target and E0
profile, canonical run binding, clean baseline, boot-only AP receipt, and a
static checker PASS with every live-action flag false.

Malformed nested artifact receipts fail closed. The shared verifier no longer
assumes that an attacker-controlled nested receipt is a mapping.

## Evidence states

The retained `/proc/last_kmsg` classifier emits exactly one of four states:

- `PID1_USERSPACE_ABSENT`: no marker family is present;
- `PID1_ENTRY_ONLY`: the post-`execve` kernel ENTRY marker is present;
- `PID1_USERSPACE_CALLBACK_REACHED`: the exact first userspace proc checkpoint
  is present and is the only accepted state;
- `PID1_USERSPACE_FAMILY_INTEGRITY_FAILURE`: duplicate, mixed, or partial
  family evidence is present.

The common D0 path performs the clean-baseline check during connected prepare
and repeats it before candidate execution. Any baseline family occurrence is a
stop; a post-run integrity failure cannot pass as userspace proof.

## Review and validation

Independent high-reasoning review first found one P2 fail-closed issue: a
malformed nested AP receipt could escape as `AttributeError`. The verifier now
uses a mapping-aware exact artifact comparison, a regression test covers the
case, and re-review returned no findings.

The shared Process v2, D0, live, R4W1-D, R4W1-E, and R4W1-E0 suite passes 84
tests; the combined related suite including E0 build and candidate coverage
passes 123 tests. Targeted bytecode compilation, exact manifest validation,
and `git diff --check` pass.

## Boundary and next unit

This unit created no ready manifest, device contact, D0 preparation, F1
approval, Odin invocation, transfer, or partition write. It does not prove
that the R4W1-E0 userspace callback ran on the device.

The next bounded unit is data-only ready-manifest promotion followed by one
connected read-only D0 preparation. A candidate transfer remains a separate
F1 action requiring fresh exact approval.
