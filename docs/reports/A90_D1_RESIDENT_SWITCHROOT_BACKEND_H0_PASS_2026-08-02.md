# A90 resident D1 switch-root backend H0 pass — 2026-08-02

## Result

The host-only implementation unit closed
`A90_D1_RESIDENT_SWITCHROOT_BACKEND_H0_PASS`. The healthy V3406 resident boot
can now be bound to one attended, no-payload D1 session without another boot
transfer. No device command was sent during this unit; A90 and the separately
connected S22+ were untouched.

## Execution model

One exact session approval binds the resident terminal evidence, candidate and
rollback boot identities, immutable Debian rootfs, exact A90 target profile,
action budget, expiry, observer, and fourteen reachable execution-source
files. The only allowlisted action is `SWITCHROOT_EXPERIMENT`.

Each action uses this fixed sequence:

```text
resident/source preflight
-> durable action intent
-> one switch_root dispatch
-> Debian/display observation
-> bounded native return
-> exact transient work cleanup
-> final resident/source health
```

The runner has no candidate or rollback transfer call. Its manifest and action
records state `payload_transfer=false`, `partition_write=false`, and
`flash=false`.

## Durable ownership and recovery

- The manifest fixes one private `d1-live` directory and one session lock.
- A whole-session `flock` and ordinal-derived expected sequence prevent two
  concurrent resume processes from dispatching the same action.
- The approval can open only that one manifest-bound session directory.
- Every journal record binds the run and manifest hashes.
- Every completed action first writes a private, fsynced engine-outcome file.
  The journal binds its path, size, and SHA256; restore replays the engine and
  rejects snapshot/outcome changes that do not match that evidence.
- A dangling intent is never replayed.

Observer, experiment, and safety results remain separate. Host/NCM/work or
retained-pmsg cleanup failure with exact final resident health closes
`SESSION_CLOSED_EXPERIMENT_BLOCKED` while retaining `RESIDENT_HEALTHY`.
Unknown native health or ambiguous control still requires recovery.

## Return proof

A candidate return is accepted only with the exact bridge identity, an exact
changed USB serial epoch, native version/selftest proof, one integer command
sequence, the transient ModemManager guard proof and release, and a captured
then cleared retained-pmsg record. Empty, malformed, boolean-count, mixed
success/error, and cleanup-incomplete shapes cannot become `PROVED`.

A malformed observer result is normalized as observer evidence and does not
skip returned-NCM checking, work cleanup, final native health, or final source
verification.

## Validation

- D1 focused regression: `21/21` pass.
- Existing transition engine and adapter regression: `49/49` pass.
- Python compilation and `git diff --check`: pass.
- The real V3406 resident manifest and its eleven-record terminal journal were
  used in a temporary host-only build/load check. Resident evidence
  cross-check, fourteen source roles, canonical transaction path, and lock
  binding all passed.
- Independent review replayed approval reuse, concurrent resume, journal
  tampering, source-closure mutation, arbitrary paths, malformed return,
  retained-pmsg failure, non-dict observer, and bool/int confusion probes. The
  final disposition was `PASS / GO` with no unresolved finding.

## Boundary

This unit grants no live authority and proves no new device behavior. A fresh
exact `A90_D1_ATTENDED_SESSION_V1` approval is still required before the first
live action. Once that approval is consumed, later actions may resume the same
bounded session without another boot image transfer or approval replay.
