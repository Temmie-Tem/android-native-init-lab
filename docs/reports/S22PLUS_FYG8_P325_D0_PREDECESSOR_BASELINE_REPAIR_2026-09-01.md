# S22+ FYG8 P3.25 D0 predecessor-baseline repair

Date: 2026-09-01

Target: `SM-S906N` / `g0q` / `S906NKSS7FYG8`

Status: `PASS_GO_P325_D0_PREDECESSOR_BASELINE_H0`; no P3.25 candidate transfer

## Connected stop

The first fresh P3.25 preparation stopped before a prepared binding because
the bounded ADB capture retained the one-time daemon-start stderr banner. It
created no candidate intent, reboot, Download transition, Odin invocation, or
partition transfer. A second fresh invocation reached D0 and durably stopped
as `STOP_DEVICE_ACTION_D0_V2_BASELINE_REJECTED` at
`baseline-classification`. That invocation was connected read-only: device
writes, reboot, Download transition, Odin, partition transfer, F1 authority,
and live authority were all false.

The second stop preserved a complete 2,097,136-byte `/proc/last_kmsg` capture
with SHA-256
`e64815cf43f0772226518d39e566d6b8670f225a0469bca89022e50a9d918552`.
It is not reusable as a D0 result.

## Root cause and bounded repair

Independent host reanalysis under the consumed P324 adapter finds exactly one
record at offset 1,657,196. It has the P324 run identity, two valid slots, no
integrity issue, no foreign record, no candidate-success claim, and proof
class `NO_PROOF_OBSERVER`. The P325 adapter correctly rejects the predecessor
run ID, but the common classifier had successor exceptions only through P324;
the corresponding P324-to-P325 exact baseline case was missing.

The repair admits only the complete raw identity above, only for the P325
overlay, and only after the P324 adapter rederives the exact single-record
placement and non-positive semantics. A one-byte mutation fails on raw
identity. It does not accept a P325 record, another P324 capture, a different
offset or semantic result, another target, or any candidate replay. The
exception expires on raw drift or P325 candidate intent.

No new baseline reboot, D1 campaign, candidate build, Full-LTO build, AP,
rollback artifact, selector, observer, or transfer behavior was added.

## Fresh host binding

The unchanged P325 candidate AP remains 27,279,401 bytes with SHA-256
`486fd1f2dcb8fbca9f31cb6bce438bb38945cf98e9bb9422f5d5301a7b0abdf4`.
The unchanged exact rollback remains 23,367,721 bytes with SHA-256
`d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`.

Private promotion `process-v2-promotion-20260901-04` contains the unchanged
candidate-static, run-manifest, and static-check payloads as mode `0400`,
single-link files under a mode-`0700` directory. Public manifest
`s22plus_fyg8_p325_process_v2_ready_3.json` is 3,327 bytes with SHA-256
`a197709728fc7efd35ca1de715e7b884b4c912d52a579fd744009b41a5eabb0b`.
The prior `ready_2`/promotion `-03` remain preserved predecessors.

Common evidence/core/live tests pass 131/131, P325 ready tests pass 6/6,
P325 artifact/guard/static tests pass 23/23, and D0 tests pass 23/23.
Compilation, diff checks, noncreating rehearsal, publication, and bundle
reopening pass. Independent hostile review rederived the exact raw identity,
P324 record placement and non-positive semantics, verified mutation and
another P324 capture fail closed, and returned
`PASS_GO_P325_D0_PREDECESSOR_BASELINE_H0`.

These checks and the ready manifest grant no approval, F1, replay, or live
authority. One fresh connected prepare is next.
