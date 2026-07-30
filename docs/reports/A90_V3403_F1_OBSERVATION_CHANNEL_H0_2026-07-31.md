# A90 V3403 F1 Observation Channel H0

Date: 2026-07-31 KST

Status: `H0_STATIC_GO`

## Scope

This unit diagnoses the V3403 F1 no-proof observation failure and hardens the
host-side command channel before any later A90 experiment. It changes no boot
payload or device runtime source and performs no device action.

The closed run and its consumed approval remain non-reusable. This report does
not authorize a new D0, D1, or F1 action.

## Corrected failure boundary

The closed observation result has only proof, error, and candidate-return
records. It has no accepted source-preflight, handoff, or SSH record. The
failed echo is a truncated and invalid command frame with menu output
interleaved into it.

The first candidate-side remote source-preflight request was therefore
corrupted before the handoff phase. The switch-root handoff itself was never
sent. The earlier report was corrected to state this narrower boundary.

## Remediation

All F1 command-channel operations now bind an explicit slow serial input mode
and per-character delay instead of depending on ambient environment state.
The observation corridor is exact and single-shot:

1. send a framed menu-hide command;
2. wait three seconds, longer than the V3403 automatic-menu refresh interval;
3. require a harmless framed command canary;
4. perform the read-only source preflight;
5. repeat hide, settle, and canary; and
6. send the handoff through one direct bridge exchange with no retry.

Failure of either settle sequence prevents the handoff. Observation failure
still proceeds to bounded candidate-return classification and the already
authorized mandatory rollback path.

The bridge deadline now covers lock acquisition, connection, paced
transmission, and a reserved read window. A slow exchange refuses to send its
first byte unless the complete paced payload and minimum read budget remain.
It also checks the remaining budget before every byte. This prevents a
deadline exhausted while waiting for the bridge lock from partially or fully
sending a handoff that the host can no longer observe.

## Complete handoff timeout

The prior 45-second manifest value was too short. A historical failure had
already spent about 38 seconds before reaching the work-copy phase, while the
V3403 success path still had a bounded 2 GiB copy and later verification and
mount work remaining.

The new minimum handoff read budget is 900 seconds:

- bounded work-image copy: 300 seconds;
- four source/work SHA passes: 4 times 90 seconds;
- bounded loop-attach and mount helpers: 2 times 30 seconds; and
- display cleanup, metadata operations, and safety margin: 180 seconds.

Five additional seconds are reserved for lock, connection, and paced command
transmission. A new manifest must therefore specify at least 905 seconds.
Both manifest loading and the runtime handoff boundary reject a shorter value
before transport.

The static source contract independently binds the exact budget expression,
the manifest-loader gate, and the runtime pre-transport gate. Mutation tests
prove that removing any one of those three protections is rejected.

## Validation

The focused host-only suite passes `124/124`, covering:

- explicit input-mode and pacing propagation;
- deadline exhaustion before the first byte;
- deadline erosion during paced transmission;
- two ordered hide/settle/canary sequences;
- handoff suppression after either settle failure;
- direct single-shot handoff with no retry;
- 45-second manifest and runtime rejection;
- exact 900/905-second budget binding; and
- source-contract rejection of the three timeout regressions.

The four touched Python sources pass `py_compile`. The complete tracked diff
passes `git diff --check`.

Independent review first rejected insufficient deadline accounting, then the
45-second full-path timeout, and finally incomplete source-contract binding.
Each finding was fault-tested and closed. The final independent result is
`GO` for this H0 closure, with no device contact or live authority.

## Disposition

The host-side observation machinery is now a normal, bounded basis for
preparing another A90 experiment. It is not itself a prepared live run.

Before a new F1 attempt:

1. resolve the current staged source and work-path state with fresh bounded
   checks;
2. create a new run and immutable manifest using the current source hashes and
   the new timeout contract;
3. perform fresh connected D0 preflight; and
4. obtain one fresh exact approval binding that new target, candidate,
   rollback, manifest, and runner.

The prior run, manifest, approval, candidate attempt, and rollback must not be
replayed.
