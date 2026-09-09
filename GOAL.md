# Goal: S22+ repeatable native PID 1

Build a repeatable path from the FYG8 Android vendor boot chain and
source-matched kernel to a custom static `/init` running as PID 1, then grow
that entry point into a minimal observable and recoverable runtime.

This goal reports state, never device authority. The binding layers are
`AGENTS.md`, `docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md`, and
`docs/operations/DEVICE_ACTION_PROCESS_V2.md`. Select only
`SM-S906N/g0q/S906NKSS7FYG8`; A90 and S20+ remain isolated.

## Current bounded unit

Changed-path regression reference: [past failure checklist](docs/operations/S22PLUS_FYG8_PAST_FAILURE_CHECKLIST.md).

Implement and qualify a new attended root command console (P375). Its changed
closure is independently reviewed and the H0 READY declaration is published;
no connected preparation or live grant exists yet.
PID1 owns one persistent authenticated transport and supervises repeated root
BusyBox `sh -c` children, separate bounded stdout/stderr, command status and
process-group cancellation. Real proc/sys/dev and a same-boot RAM workspace
are intended; filesystem containment and hostile-root isolation are not claims.
STATUS and return CONTROL must remain responsive during command work and cleanup.
Host completion required actual producer/consumer and ARM64 syscall checks, a
reviewed candidate/host closure, and concrete preparation for the next attended
run. Those checks passed. See the [P375 H0 report](docs/reports/S22PLUS_FYG8_P375_ROOT_CONSOLE_H0_2026-09-09.md).

P375 A/B builds are byte-identical and contain only `boot.img.lz4`; candidate
static and the published common bundle both pass. The exact closure received
`PASS_GO` after 63 independent tests, plus the root's 33-test final rerun. The
next step is a fresh exact-target connected D0 preparation with a pre-effect
sealed command plan. Any candidate effect still requires current physical
attendance and a fresh finite live grant. The P372-P374 grant is closed and
cannot be reused.

The preceding reviewed attended batch used three fixed display-step candidates:
P372 queues one fixed pattern; P373 queues two fixed patterns in order; P374
exits its display child after a fixed request starts, before completion. Shared
PID1 supervision must retain CONTROL independently of child work. Queued,
started, completed, child-failed, Download arrival, rollback and final health
remain separate evidence. Pixel output remains operator observation unless
independently proved.

Implementation, strict ARM64 A/B builds, candidate-static/common checks and one
shared independent review are complete. All three READY manifests and the
source-bound attended-session capability review are published; 142 changed-path
tests plus two activation-gate tests passed. See the [shared H0 report](docs/reports/S22PLUS_FYG8_DISPLAY_STEP_SESSION_H0_2026-09-09.md).

The attended P372/P373/P374 session is complete. Each candidate ran once,
rolled back once and closed PASS/CLOSED19 with recovery_required=false and
validated rooted FYG8/original hashes/Android/Download absence. P372 completed
one fixed request; P373 completed two in order. P374 started one request but
completed none, exited its display child with code7, and retained STATUS/CONTROL
with the signed pending/failed state. The declared child failure is the intended
negative display outcome. Original execute completed each run without a recover
invocation. P372's temporary final-health ADB offline resolved within the existing
wait; the operator separately observed Android.

All three reservations are consumed and the grant is closed. No active native
session or replay authority remains. P375 does not reuse that grant.
Visible pixels, continuous liveness, child/kernel/PID1 stall recovery and
unattended operation remain unproved. The shared report preserves exact results,
source qualification, evidence limits and canonical timelines.

P371's separately approved third preparation is consumed and CLOSED/19 with
`PASS_F1_V2_P371_NATIVE_RETURN_CONTROL_AND_ROLLED_BACK`, recovery_required=false.
Two fixed STATUS replies after planned handoff passed, with signed native
spacing 2121 ms and the expected unreaped-child/wait facts. CONTROL, exact
Download, one candidate/rollback and final rooted FYG8/original hashes/Android
health passed. No native session or replay authority remains. Earlier ABORTED/4
and cold-ADB preparation records are preserved; no continuous-liveness/pixel/
kernel-stall or unattended claim follows. See the [P371 report](docs/reports/S22PLUS_FYG8_P371_FIXED_STATUS_PREPARATION_2026-09-09.md).


## Archive and continuing boundaries

The previous 799-line goal, including P371 closure and earlier archive links,
is preserved byte-for-byte in [the completed-history archive](docs/archive/roadmaps/GOAL_THROUGH_P371_2026-09-09.md).
That history is evidence only. Private append-only campaign records and run
journals remain authoritative for effects. Consumed candidates are never replayed.

Never prepare a new experiment over unhealthy or uncertain state. Preserve exact
target, current boot, candidate/rollback, topology, source and journal bindings.
An unexplained device-session failure stops the experiment; retain raw evidence
and continue only allowed observation and preauthorized recovery. A reporting
failure never repeats a device effect. A90 and S20+ are outside this unit.
