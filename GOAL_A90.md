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

- H3 remains the last successful resident and automatic-handoff line. Its
  attended D1 ordinal armed once, rebooted once, displayed Debian, retained all
  15 mandatory benchmark stages, returned automatically, cleaned its work
  copy, and closed exact H3 health without replay. The missed same-ordinal SSH
  observation remains correctly `NO_PROOF_OBSERVER_RESIDENT_HEALTHY`.
- H4 run `a90-v3406-debian-display-f1-20260805-11` staged its exact fresh 2 GiB
  keyed rootfs and transferred boot-only candidate `0.11.172` exactly once.
  The F1 observer then rejected the cumulative native log before it could write
  `candidate-boot-ready`; the candidate was not replayed.
- The same durable run performed one exact V2321 rollback and closed terminal
  `ABORTED_F1_V2_CANDIDATE_UNCERTAIN_ROLLED_BACK`. Exact V2321
  `0.9.285/v2321-usb-clean-identity-rodata`, self-test fail zero, pstore zero,
  the bounded control channel, guard release, and final health all passed.
- The incident is classified `HOST_OBSERVER_CUMULATIVE_UNARMED_LOG_REJECTION`.
  The exact thrown branch and source semantics identify the global
  exactly-one log count as the likely cause, but no candidate log receipt was
  durably recorded, so H4 candidate health is not retroactively claimed.
- The H0 repair accepts one or more cumulative state lines only when every
  `A90AUTO state=` line is exactly `unarmed-stay-native`; missing, malformed,
  armed, dispatch, and mixed states still fail closed. F1 and resident-install
  journal consumers now share that rule. All 240 focused tests pass and
  independent review returned `PASS_GO_NEW_CAMPAIGN_ONLY` with no unresolved
  HIGH or MEDIUM finding and no device authority.
- The exact H4 source remains on SD, while its work and staging paths are
  absent. Post-rollback SD inventory is 61408048 KiB total, 54419468 KiB used,
  and 3862568 KiB available at 93% use. This is below the margin required for
  another fresh 2 GiB source plus 2 GiB work copy.
- The exact V2321 boot rollback remains present and hash-verified. Physical
  Download and TWRP recovery remain demonstrated and available.
- No D1 transaction is active and no target is F1-armed. Run-11 and its H4
  candidate are terminal and must never be resumed or replayed. S22+ received
  no A90 command.

## Qualified Capabilities

- The H3 exact compiled-rootfs binding and resident F1 closure has reusable
  independent `PASS_GO` for its named execution-critical hashes and E2 hazard.
- The current auto-benchmark observer/tail closure
  `e17d9e23e3f473d949cf264b54246ac01ec221fe133e0291a200437a0ed13959`
  has independent `PASS_GO`. It binds exact NCM-before-SSH, all 15 mandatory
  handoff stages, and post-cleanup-only historical journal finalization with no
  arm, reboot, handoff, or cleanup replay.
- The pre-incident H4 replacement closure had independent `PASS_GO` for boot SHA
  `6bc133937f19482739037b67a44b1f2b5da6da9a178a3edf8a9f2e74bd097935`,
  fresh keyed-rootfs SHA
  `8b4bfd99a9324c0a32e76c837e33282afa79739fa32645e3303861e8928a33fa`,
  compiled binding
  `783a528a541e3a8edf82543d7352ed2e47f5d3393245d413ee8507df6e797e09`,
  and benchmark execution closure
  `d521a3f1c663ff65791ba804ad84469592c3825233d5bcfd227dfdc5984a642d`.
  The new incident and changed F1 observer retire that receipt for live reuse;
  the repaired production observer closure
  `5120fea1eb29975cb92216d07627f68ced883c1560a4e6dce807f8839c5e8634`
  is qualified `PASS_GO_NEW_CAMPAIGN_ONLY`. A fresh candidate, qualification,
  exact binding and D0, attendance, recovery, and live campaign remain required.
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

## Selected Bounded Unit: Prepare Fresh H5 From Recovered Capacity

Run-11 is terminal. Do not resume or replay its candidate, reset its state
namespace, or reinterpret the missing candidate log receipt. Incident closure
and bounded capacity recovery are complete; execution continues at item 4:

The exact V2321 H3 run-10 source reclaim capability was independently
`PASS_GO` over its named 19-test closure and used once under a fresh D0 and
immutable manifest. It returned `PASS_H3_SOURCE_RECLAIMED`: run-10 is absent,
H4 run-11 remains exact, work is absent, final V2321 health is exact, and SD
available space increased by exactly 2,097,152 KiB to 5,959,716 KiB. Its
capability-wide receipt is consumed and the capability is retired; never reuse
it under another run ID. Host-preserved bytes remain evidence and grant no
restore authority. The next live unit is a fresh H5, not H4 replay.

H5 host preparation now has one fresh run-12 keyed rootfs, deterministic
byte-identical A/B boot candidate `0.11.173`, fresh h5 enable/latch namespace,
and independent `PASS_GO` over the exact 13-file F1/D1 closure. No H5 rootfs
has been staged and no candidate, reboot, arm, or flash authority has been
consumed. The next gate is a committed closure followed by fresh exact D0,
immutable H5 manifests, and attended boot-only F1; H4 remains terminal.

1. preserve the closed H4 journal, exact source, and rollback result as
   no-replay incident evidence;
2. independently review the cumulative-log observer repair and bind its exact
   execution-critical closure;
3. inventory obsolete A90 SD sources at H0 and design one bounded reclaim path
   that is valid from exact V2321 health; existing V3406-only GC authority must
   not be reused;
4. only after adequate free-space margin exists, build and qualify a fresh H5
   candidate with a new build identity, absent rootfs destination, and absent
   enable/latch namespace;
5. perform fresh exact D0 and one new attended boot-only F1 campaign with exact
   V2321 rollback;
6. prove first-boot health and exclusive unarmed state before any D1 action;
7. arm once and reboot once under one durable D1 ordinal, rebind exact A90 NCM
   before SSH, and require Debian PID 1, key-only SSH, exact service ownership,
   mechanical display acquisition, operator visibility, and all mandatory
   benchmark stages; and
8. require automatic native return, retained latch, cleanup, immutable source,
   final resident health, and no replay before designating a baseline.

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
- `docs/reports/A90_H4_CUMULATIVE_UNARMED_LOG_OBSERVER_INCIDENT_REVIEW_2026-08-05.json`
- `docs/reports/A90_V2321_H3_SOURCE_RECLAIM_CAPABILITY_INDEPENDENT_REVIEW_2026-08-05.json`
- `docs/reports/A90_PHASE3_MINIMAL_H5_FRESH_CAMPAIGN_INDEPENDENT_REVIEW_2026-08-05.json`
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
