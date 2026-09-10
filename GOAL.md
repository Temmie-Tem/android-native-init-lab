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

**v0.1.2-rc.4 / P381** is consumed and CLOSED/19 with exact rollback and final
rooted FYG8/original health complete. All six functional qualifications and three
planned commands passed with zero dropped output; the operator photograph shows
SOC/voltage/current. Two complete memory observations confirm369 files retained
on RAM with55.988MiB allocation metadata, not reclaimability.
The host's full OBSERVED journal record exceeded32KiB after observation. One
unchanged recovery resumed from durable evidence without candidate/CONTROL
replay, but timely software-return observation was missed. Formal NO_PROOF is
preserved and v0.1.1 retained. Next H0 unit: repair journal serialization and
qualify the actual full close/recovery path before a new candidate. No file
deletion, RBIN/CMA change or standing native lease follows.
See the [rc.4 report](docs/reports/S22PLUS_FYG8_OUTPUT_MEMORY_RC4_H0_2026-09-10.md).

Previous candidate **v0.1.2-rc.3** (P380) is consumed and CLOSED/19 with one
exact rollback and final rooted FYG8/original health complete. The gauge HUD
subproof passed with three fresh SOC/voltage/current samples; overall console
qualification failed on 1536 dropped output bytes (queue pressure), so all
three planned commands stayed unexecuted. Formal NO_PROOF is preserved.
Two native meminfo observations identify an 800 MiB RBIN reservation component
in the ~1054 MiB HUD accounting difference; separating it leaves ~254 MiB,
not reclaimed RAM. The command output loss leaves the full process census unproved
and does not establish absence of a leak. No replay/native lease remains; v0.1.1 is retained and
image publication deferred. Follow-up Android D0 observed RBIN800MiB with7MiB
allocated/793MiB free/zero cached, and CmaTotal444MiB. Source verification found
the camera-named RBIN/gen_pool/cleancache implementation; reusable alone is not
proof of automatic reuse or safe release. Further H0 verified the historical
A90 281MiB arithmetic, but not its historical kernel/RBIN accounting. Reducing
the real S22+ reservation is a worthwhile design candidate, distinct from
changing the HUD calculation; no release or new device run is qualified.
The [H0 memory source review](docs/reports/S22PLUS_FYG8_MEMORY_SOURCE_REVIEW_H0_2026-09-10.md)
prioritizes RBIN ownership and Shmem/slab attribution. The adjusted254MiB
includes about32MiB of net availability-estimator gap; enabled diagnostic
options alone do not prove their runtime memory cost. No settings were changed.
Further H0 includes the vendor ramdisk: combined file data rounds to77.672MiB,
with55.988MiB in369 module files outside the current explicit load plans.
This is a RAM-file retention design candidate, not measured reclaimability.
Both applicable merged DTs explain CMA444MiB across13 areas and carry kasan=off;
final native filesystem/slab attribution and effective boot arguments remain open.
See the [rc.3 close and memory report](docs/reports/S22PLUS_FYG8_GAUGE_MODEL_MEMORY_RC3_H0_2026-09-10.md).

Previous candidate: **v0.1.2-rc.2 gauge diagnostics** (P379), consumed and CLOSED/19.
Formal result is NO_PROOF with one exact rollback and final rooted FYG8/original
health complete; no replay or native lease remains. Authenticated diagnostics
localize root-model allowlist rejection (stage7/ENODEV), before binding or any
I2C read. Units were not reached. Later probe checks remain untested.
Diagnostic localization succeeded; v0.1.2 remains unconfirmed and v0.1.1 retained.
Post-close bounded Android D0 observed root model `Samsung G0Q PROJECT (board-id,12)`
and retained meminfo; Android values do not decompose the prior native 1053 MiB.
This is the concrete rc.3 identity-check input. HUD image publication remains
deferred until rc.3 shows actual gauge data. See the [close report](docs/reports/S22PLUS_FYG8_GAUGE_DIAGNOSTICS_RC2_H0_2026-09-10.md).

Previous candidate: **v0.1.2-rc.1 — restricted gauge telemetry HUD**, consumed.
The attended `p378-ready1-prepared-20260909-1` run closed
`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`: the gauge HUD qualification failed,
all three planned console commands remained unexecuted, and one exact rollback
plus final rooted FYG8/original-hash health completed. CLOSED/19,
`recovery_required=false`; no replay or standing native lease remains.
The photograph and retained HUD records show memory/CPU but gauge SOC, voltage,
current and gauge age N/A. Module insertion return does not prove child binding
or reads; the retained evidence cannot localize that failure. **v0.1.2 is not
confirmed.** See the [run report](docs/reports/S22PLUS_FYG8_GAUGE_HUD_V012_RC1_H0_2026-09-09.md).

Functional version: **v0.1.1 — system-status HUD**, mapped to successful
v0.1.1-rc.1 / run-001 (internal P377) without rebuilding or renaming artifacts.
The attended run passed all six fixed qualifications and three planned commands,
then one exact rollback and final rooted FYG8/original-hash health. CLOSED/19,
`recovery_required=false`; no replay or standing native console/HUD lease remains.

The operator photograph shows the grid-aligned text, memory/CPU and version/
purpose footer without visible clipping. Physical output is OBSERVED. Memory
and CPU are machine-qualified; battery capacity/charge/temperature show N/A and
remain unmeasured in native boot. Supplemental stock proof stays NO_PROOF_OBSERVER.
See the [status HUD report](docs/reports/S22PLUS_FYG8_STATUS_HUD_V011_RC1_H0_2026-09-09.md)
for the exact artifacts, photograph metadata, canonical timeline and limits.
This bounded unit is complete; any next candidate needs its own current authority.

Previous functional version: **v0.1.0 — root console and minimal HUD**, mapped to the
unchanged P376 artifacts and completed run. New experiments use the
[version/candidate/run naming convention](docs/operations/S22PLUS_FYG8_VERSIONING.md).
This mapping changes no internal identifier, consumed evidence or device authority.

P376 minimal HUD plus root console is complete. The attended run
`p376-ready1-prepared-20260909-1` closed with
`PASS_F1_V2_P376_ROOT_CONSOLE_AND_ROLLED_BACK`: all six fixed qualifications and
three planned commands passed. Matched HUD updates continued during console
work, and the operator reported seeing the text and increasing UPTIME.
Physical output is OBSERVED; machine pixel proof is not claimed.

One candidate and one exact rollback completed. Final rooted FYG8 Android,
original partition hashes and Download absence passed; CLOSED/19 with
`recovery_required=false`. No recover invocation, replay or standing console/HUD
lease remains. Supplemental stock evidence is still NO_PROOF_OBSERVER.
See the [P376 report](docs/reports/S22PLUS_FYG8_P376_BOOT_HUD_H0_2026-09-09.md)
for the canonical timeline, evidence hashes and limits. Any next candidate
requires its own current binding and authority.

P375 root console implementation, independent review and one attended live run
are complete. Run `p375-ready1-prepared-20260909-1` closed with
`PASS_F1_V2_P375_ROOT_CONSOLE_AND_ROLLED_BACK`: five fixed qualification commands
and three sealed plan commands passed; one candidate and one exact rollback
completed, followed by verified rooted FYG8 Android and original partition
hashes. The journal has 19 records, CLOSED, `recovery_required=false`.

The proved capability is repeated root BusyBox `sh -c` execution supervised by
native PID1 over one authenticated transport, real proc/sys/dev, same-boot RAM
state, bounded stdout/stderr, STATUS and cancellation. CONTROL acceptance and
observed exact Download rollback remain separate evidence. The supplemental
stock projection remains `NO_PROOF_OBSERVER`; it provides no causal stock proof.
No standing shell or replay authority remains. Any next run needs its own
current binding and authority. See the [P375 report](docs/reports/S22PLUS_FYG8_P375_ROOT_CONSOLE_H0_2026-09-09.md)
for the canonical timeline, evidence hashes and limits.

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
