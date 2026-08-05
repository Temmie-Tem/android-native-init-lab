# Goal: A90 native bridge to Debian runtime

Build the operator-owned Galaxy A90 5G into a Debian-oriented personal server
where native-init performs only the vendor-kernel and hardware bridge-up that
Debian cannot yet perform, then transfers PID 1 and the steady-state runtime to
the immutable SD-backed Debian root with `switch_root`.

`AGENTS.md` and `docs/operations/targets/A90_TARGET_CONTRACT.md` are binding.
This file records current state and the next bounded unit; it grants no device
authority. `GOAL.md` is the separate S22+ objective. Target identities,
artifacts, transports, evidence, recovery, and commands never cross between
the two goals.

The pre-H2 goal history is preserved at
`docs/archive/roadmaps/GOAL_A90_PRE_H2_2026-08-05.md`.

## Current State

- Fresh attended F1 run `a90-v3406-debian-display-f1-20260805-10` installed
  exact resident `0.11.171/phase3-minimal-h3-exact-binding-auto-benchmark` with
  one boot-only candidate transfer, zero rollback, and no replay. Exact H3
  compiled-rootfs binding, first-boot `enable=0/latch=0`, guard release, and
  final `RESIDENT_HEALTHY` all passed.
- Attended D1 run `a90-d1-attended-20260805-08` armed once and rebooted once.
  Its retained log contains one complete ordered benchmark segment from
  `native_runtime_ready` through mandatory `auto_handoff_check` and
  `switch_root_exec`. The operator saw the Debian display.
- The same ordinal returned automatically to exact H3 native-init with
  `enable=1/latch=1`, removed the 2 GiB work copy once, retained the immutable
  source rootfs, released the guard, and closed `RESIDENT_HEALTHY` with no
  action replay.
- The initial SSH observer ran before the re-enumerated exact A90 NCM interface
  was rebound. Debian PID 1, Dropbear, and mechanical display ownership were
  therefore not captured in this ordinal. Its experiment terminal is correctly
  `NO_PROOF_OBSERVER_RESIDENT_HEALTHY`, even though switch-root stage completion,
  operator visibility, automatic native return, cleanup, and final health are
  durable.
- The host observer is repaired for future ordinals: exact A90 NCM rebind now
  precedes SSH, the pre-runtime cache marker is optional capture, and all 15
  handoff-critical stages remain mandatory. Independent review returned
  `PASS_GO` for the current closure.
- H4 host qualification is complete for fresh observer-complete baseline
  candidate `0.11.172/phase3-minimal-h4-observer-complete-auto-benchmark`.
  Its fresh run-11 keyed rootfs, deterministic A/B boot, compiled binding, new
  enable/latch namespace, F1 interpretation, and D1 runner identity have exact
  reusable independent `PASS_GO`; this grants no device authority.
- Fresh run-11 D0 proved exact H3 resident health, exact H4 candidate and V2321
  rollback hashes, and absent H4 final/work/stage paths. SD remains 61408048
  KiB total with 5959744 KiB available at 90% use before H4 staging.
- Final SD inventory is 61408048 KiB total, 52322292 KiB used, and 5959744 KiB
  available at 90% use. The transient work image is absent.
- The exact V2321 boot rollback remains present and hash-verified. Physical
  Download and TWRP recovery remain demonstrated and available.
- No D1 transaction is active and no target is F1-armed. The H3 latch prevents
  replay of the completed automatic handoff. S22+ received no A90 command.

## Qualified Capabilities

- The H3 exact compiled-rootfs binding and resident F1 closure has reusable
  independent `PASS_GO` for its named execution-critical hashes and E2 hazard.
- The current auto-benchmark observer/tail closure
  `e17d9e23e3f473d949cf264b54246ac01ec221fe133e0291a200437a0ed13959`
  has independent `PASS_GO`. It binds exact NCM-before-SSH, all 15 mandatory
  handoff stages, and post-cleanup-only historical journal finalization with no
  arm, reboot, handoff, or cleanup replay.
- The H4 replacement closure has independent `PASS_GO` for boot SHA
  `6bc133937f19482739037b67a44b1f2b5da6da9a178a3edf8a9f2e74bd097935`,
  fresh keyed-rootfs SHA
  `8b4bfd99a9324c0a32e76c837e33282afa79739fa32645e3303861e8928a33fa`,
  compiled binding
  `783a528a541e3a8edf82543d7352ed2e47f5d3393245d413ee8507df6e797e09`,
  and benchmark execution closure
  `d521a3f1c663ff65791ba804ad84469592c3825233d5bcfd227dfdc5984a642d`.
- Earlier minimal-G attended evidence remains the same-ordinal proof of Debian
  PID 1, key-only SSH, Debian service ownership, direct DRM, operator-visible
  output, automatic native return, cleanup, and resident health.
- `PASS_GO` qualifies a capability, not a run. It is reused across manifests,
  campaigns, qualifications, and ordinals only while the named
  execution-critical closure and hazard assumptions remain unchanged and no
  new hazard or incident occurs.
- Fresh exact target, rollback, recovery, presence, D0, immutable manifest,
  runner binding, and inter-effect health remain live requirements. A review
  receipt alone never dispatches a device action.

## Proven Product Path

Earlier minimal-G attended evidence already proves the product mechanism:

```text
native-init strict display and service release
-> immutable SD work-copy verification
-> switch_root
-> Debian sysvinit as PID 1
-> key-only Dropbear SSH and Debian service ownership
-> direct DRM master and visible display output
-> bounded automatic native return
-> exact work cleanup and resident health
```

The H3 line adds two things without changing that product path:

1. a durable two-phase automatic-handoff enable/latch; and
2. bounded boot/handoff telemetry for before-and-after optimization comparison.

H3 now proves first-boot non-dispatch, one armed automatic switch-root stage
sequence, operator-visible Debian output, retained latch, automatic native
return, cleanup, final health, and benchmark telemetry. It does not claim the
missing same-ordinal mechanical Debian PID1/SSH evidence.

## Selected Bounded Unit: Fresh Automatic-Handoff Correctness Baseline

Do not replay or reset the closed H3 ordinal. The next bounded unit is a fresh
candidate/marker namespace using the reviewed observer closure:

H4 host qualification, fresh keyed-rootfs materialization, independent review,
and fresh exact D0 are complete. The next effect boundary is one attended
boot-only H4 F1 install; no candidate intent has started.

1. preserve the closed H3 journal and benchmark as no-replay diagnostic data;
2. build and qualify one fresh exact-bound benchmark candidate without adding
   a general marker-reset or replay primitive;
3. install it through one attended boot-only F1 with exact V2321 rollback;
4. prove its first boot is healthy and unarmed;
5. arm once and reboot once under one durable D1 ordinal;
6. rebind the exact A90 NCM interface before SSH observation;
7. require Debian PID 1, key-only SSH, exact Debian service ownership,
   mechanical display acquisition, operator visibility, and every mandatory
   benchmark stage through `switch_root_exec` in the same ordinal;
8. require automatic native return, retained latch, cleanup, immutable source,
   final resident health, and no replay; and
9. only then designate the result as the pre-optimization correctness baseline.

An uncertain arm or reboot is never resent. Endpoint absence or a late
observation parks the ordinal; it does not authorize replay. No later benchmark
or optimization build starts until exact health is durable.

## Optimization Order

Do not start Full-LTO or other compiler optimization from an unmeasured state.
The order is:

```text
fresh automatic-handoff correctness
-> repeatable baseline benchmark
-> workload and thermal/power interpretation
-> one bounded build optimization such as Full-LTO
-> same benchmark and correctness closure
-> compare without weakening recovery or no-replay behavior
```

Boot timing, phase duration, temperature, CPU/GPU clocks, memory, storage I/O,
and available power signals are diagnostic covariates. They do not replace the
atomic PID1, SSH, display, return, cleanup, and final-health result.

## Final Architecture

```text
vendor boot chain and source-matched kernel
-> minimal native-init hardware bridge-up
-> immutable SD work-root verification
-> strict native display and service release
-> switch_root
-> Debian init as PID 1
-> Debian-owned services, networking, display, storage, and applications
```

Native-init remains the early hardware-enablement, bounded recovery, and
diagnostic bridge. A function moves to Debian only after a Debian-side consumer
proves equivalent ownership and the rollback/recovery contract remains intact.

## Evidence

- `docs/archive/reports/A90_PHASE3_MINIMAL_H2_TWO_PHASE_AUTO_BENCHMARK_INDEPENDENT_REREVIEW_2026-08-05.json`
- `docs/archive/reports/A90_PHASE3_MINIMAL_H2_LIVE_F1_D1_INTEGRATION_FINAL_INDEPENDENT_REVIEW_2026-08-05.json`
- `docs/reports/A90_PHASE3_MINIMAL_H2_POST_INCIDENT_FINAL_INDEPENDENT_REVIEW_2026-08-05.json`
- `docs/reports/A90_PHASE3_MINIMAL_H2_BRIDGE_STOP_FOCUSED_FRESH_INDEPENDENT_REVIEW_2026-08-05.json`
- `docs/reports/A90_PHASE3_MINIMAL_H2_HISTORICAL_ACM_EPOCH_FOCUSED_INDEPENDENT_REVIEW_2026-08-05.json`
- `docs/reports/A90_PHASE3_MINIMAL_H3_EXACT_BINDING_INDEPENDENT_REVIEW_2026-08-05.json`
- `docs/reports/A90_H3_AUTO_BENCHMARK_OBSERVER_TAIL_REPAIR_INDEPENDENT_REVIEW_2026-08-05.json`
- `docs/reports/A90_PHASE3_MINIMAL_H4_OBSERVER_COMPLETE_INDEPENDENT_REVIEW_2026-08-05.json`
- `docs/operations/CAMPAIGN_LEDGER_A90.md`

Private manifests, journals, raw logs, rootfs and boot artifacts, rollback
bytes, target identifiers, and run results remain under `workspace/private/`.
They are never committed.

## Process

For each bounded unit:

`STATE -> SELECT -> DESIGN -> IMPLEMENT -> STATIC VALIDATE -> DEVICE -> REPORT -> COMMIT`

Omit `DEVICE` for H0. Preserve immutable inputs after intent, use one durable
intent per effect, never repeat a proven or uncertain transition because an
observer or report failed, and keep A90 and S22+ completely isolated.

## Success Conditions

The A90 goal is complete only when:

- Debian becomes PID 1 through reproducible automatic `switch_root`;
- Debian owns intended steady-state SSH, networking, display, storage, and
  applications;
- automatic return and recovery remain bounded and reliable;
- native-init retains only named hardware-enablement and recovery functions;
- repeatable benchmark evidence supports later optimization decisions; and
- repeated boots and failure injection support personal-server use without
  broadening boot-only partition authority.

## Stop Conditions

- A permanent boundary in `AGENTS.md` would need to change.
- A90 target, rollback, recovery, resident, rootfs, or health identity is
  ambiguous.
- Work would replay an uncertain arm, reboot, handoff, transfer, or candidate.
- The device is not exact `HEALTHY` before a new effect.
- A non-boot partition write, recovery mutation, or forbidden raw primitive
  would be required.
- S22+ tooling, evidence, identity, approval, or command would be treated as
  A90 proof.
