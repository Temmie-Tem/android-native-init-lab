# S22+ FYG8 P2.80 diagnostic precedence amendment

Date: 2026-07-27 KST

Scope: H0, host-only, design and focused control-test amendment

Device contact: none

## Verdict

The adversarial priority objection is substantially correct:

> failure of optional control-flow instrumentation must not destroy an
> otherwise valid E3 functional result.

The proposed blanket conversion of `0xb01..0xb03` to fail-soft is not safe,
however. P2.80 has two different synchronization boundaries:

- Phase B ends in a synchronous configfs UDC-bind return. Trace loss after that
  return cannot leave the bind call or its nested pull-up call in flight.
- Phase R queues asynchronous parent work. After the role action starts, a
  malformed or missed trace can hide an active parent worker and an active
  kretprobe instance. Continuing from that state would turn diagnostic loss
  into an unbounded cleanup or ordering hazard.

The selected amendment therefore makes setup-time instrumentation loss
fail-soft in both phases and post-bind trace loss fail-soft in Phase B only.
Phase R post-action ambiguity remains fail-closed.

## Contract Evidence

The current retained checkpoint format has two alternating slots. The decoder
requires adjacent generations and selects the newest slot as active.

The current contract also requires:

- progress records to have `detail == 0`;
- terminal success to have `detail == 0`; and
- any failure record to terminate the checkpoint client.

Consequently, publishing `0xb01` as a failure and then continuing is
impossible, while publishing a one-off warning before later progress would be
overwritten. Allowing nonzero terminal-success detail would weaken the
long-standing terminal invariant and alter generic Process v2 success
semantics.

P2.80 instead uses a versioned progress-warning semantic without changing the
45-byte record shape, stage sequence, generation ordinals, or terminal rule.
A warning is copied into every later nonterminal progress slot through stage
`0x8f`. At a final result:

- terminal success leaves warning-bearing `0x8f` as the previous A/B slot;
- a failure at `0x8f` leaves warning-bearing `0x8e` as the previous slot; and
- an earlier primary operation failure remains authoritative even if no
  same-stage warning can also be retained.

The P2.80 decoder must expose the warning from either valid slot separately
from the active functional outcome. It must never reinterpret a warning as
proof that a target function did not execute.

## Exact Priority

### Fail-soft after verified clean ownership

`0xb01` and `0xb02` become progress warnings when they occur before the phase's
device action:

- tracefs or the required control ABI is unavailable; or
- exact event registration/readback fails.

Continuation is allowed only after the candidate proves that it owns no live
event, instance, or mount. Any cleanup uncertainty becomes terminal `0xb04`.

Phase R then falls back to the already exercised P2.60 final role/UDC
predicate, but only after a P2.80 exact-`none` precondition; it never accepts or
writes from initial `host`. Phase B performs the unchanged synchronous UDC bind
without trace classification.

This fallback does not claim parent-worker quiescence. Its safety argument is
narrower:

- setup failed before the role action;
- verified cleanup proves that no P2.80 probe remains active; and
- the resulting uninstrumented role-to-bind ordering is the P2.76 ordering
  already observed through exact `0x8e` without a boot loop.

The degraded path can still establish the primary E3 result through exact
configured/high-speed plus the host banner. It cannot establish a Phase R
control-flow conclusion.

### Phase-B fail-soft after its synchronous fence

Malformed, missed, or source-contradictory Phase-B trace becomes progress
warning `0xb03` only after all of these hold:

1. the synchronous configfs bind returned;
2. tracing was disabled;
3. no owned probe can still be active; and
4. full cleanup was verified.

The candidate continues to the primary configured/high-speed check. If that
check times out while the final state is `not attached`, it emits a dedicated
"Phase-B diagnostic incomplete" result rather than one of the trace-derived
`0xb20..0xb22` conclusions. A Phase R-only warning does not invalidate
independently clean Phase-B pull-up/run-stop evidence.

### Phase-R fail-closed after action begins

The following remain terminal:

- an entered parent worker without its return by the absolute deadline;
- a malformed helper record or impossible helper/source ordering;
- a missed, malformed, or contradictory Phase-R trace after role action; and
- any cleanup failure.

These cases do not merely lose diagnostics. They also lose the proof that the
asynchronous parent worker and its return-probe instances are quiescent.

## Detail Semantics

The versioned P2.80 descriptor must bind allowed outcome as well as allowed
stage:

- `0xb01`: progress warning, tracefs/control ABI unavailable before action;
- `0xb02`: progress warning, arming/readback failed before action;
- `0xb03`: progress warning, Phase-B trace quality lost after synchronous bind;
- `0xb04`: terminal failure, cleanup could not be verified;
- `0xb18`: terminal failure, Phase-R post-action trace quality cannot prove a
  quiescent worker; and
- `0xb27`: terminal `0x8f` failure, final state is `not attached` and the clean
  Phase-B trace evidence needed for `0xb20..0xb22` is unavailable.

The first warning class wins and is propagated. This preserves diagnostic
quality without adding a warning stack or a new retained field, but it does not
preserve the origin phase: `0xb01` and `0xb02` are shared by both phases. The
decoder must report that origin as `unknown`.

No `0xb01..0xb03` value is valid as terminal success or as a failure detail.
No `0xb18` or `0xb27` value is valid as progress. Terminal success remains
zero-detail.

## Existing Buffer Bound

The main P2.80 design already fixes the isolated instance buffer at 64 KiB per
CPU. No buffer-size change is required.

## Focused Host-Test Closure

The generic-arm64 control runner now exposes its exact QEMU-version decision as
a pure function. Focused tests directly cover:

- a host subprocess timeout;
- a cpio subprocess timeout;
- a QEMU-version-query timeout;
- an incorrect QEMU version; and
- the exact pinned QEMU version.

These tests close the two previously reported LOW mocked-branch gaps. They do
not replace the already passing exact QEMU guest execution.

## Validation

Host validation after the amendment:

- 81 focused and historical checkpoint/source/QEMU unit tests: pass;
- touched Python `py_compile`: pass;
- exact pinned generic-arm64 QEMU control: pass;
- QEMU control result: entry 1, return 1, signed return `-9`,
  `nmissed=0`, cleanup `ok`;
- guest init SHA256 remains
  `2d0253e89185d0db7b09dd4421e20a447d7553e25b32913657974c6de4dcd8d7`;
- initramfs SHA256 remains
  `3b3d9bcaebe7ad199fac70938223a283b5fb6fb15ca887b71bca1cafa1235e96`;
- `git diff --check`: pass; and
- `ruff`: not run because the command is not installed on this host.

The repeat QEMU output was written only under `/tmp`; no generated guest
artifact or raw execution log is added to the repository.

## Implementation Gate

Before Full LTO, focused fixtures must prove:

1. warning details are accepted only as progress at allowed P2.80 stages;
2. terminal success still requires zero detail;
3. warning propagation leaves the warning in the previous A/B slot at both
   terminal success and `0x8f` failure;
4. a Phase-R post-action trace loss parks as `0xb18`;
5. Phase-B trace loss continues only after synchronous return and verified
   cleanup;
6. cleanup failure always overrides warning state as `0xb04`;
7. trace-derived `0xb20..0xb22` is impossible when Phase-B diagnostic quality
   is not clean, while a Phase R-only warning preserves clean Phase-B
   classification; and
8. historical P2.60 records and decoders remain byte-identical.

## Independent Review Resolution

The first amendment review returned `NO-GO` on two points:

1. it read the Phase R setup fallback as claiming worker quiescence without
   `start_out`; and
2. propagated `0xb01`/`0xb02` cannot preserve their original phase.

The first finding is resolved by narrowing the fallback proof: only P2.80 probe
ownership is quiescent, while parent-worker quiescence is explicitly unproved.
The fallback reuses the already live-observed P2.76 ordering and remains
eligible only for primary configured/banner proof. The second finding is
accepted; origin is explicitly `unknown`.

The same reviewer re-read the amended contract and returned `GO`: both findings
are closed for versioned H0 implementation. The review grants no D0 or F1
authority.

## Decision

P2.80 remains `GO` for H0 implementation with this amended priority. The
amendment preserves the primary E3 mission, keeps unsafe Phase-R ambiguity
fail-closed, and adds no device action, checkpoint field, stage, module, or
live authority.
