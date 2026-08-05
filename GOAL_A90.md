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

- Fresh attended F1 run `a90-v3406-debian-display-f1-20260805-09` installed
  exact resident `0.11.170/phase3-minimal-h2-two-phase-auto-benchmark` with one
  boot-only candidate transfer, zero rollback, and no replay. Exact candidate
  health, rootfs publication, V2321 rollback readiness, guard release, and
  `RESIDENT_HEALTHY` passed before the transaction closed and disarmed.
- The H2 first boot remained deliberately native. Its exact state was
  `binding=1 enable=0 latch=0`, and the unique unarmed log marker proved that
  no automatic D1 handoff occurred during F1 installation.
- Runs `-06` and `-07` stopped before candidate intent on host observer
  timeouts during rootfs staging. Their uncertain staging actions were not
  replayed; run-bound residue was reconciled and removed before a new campaign.
- Run `-08` staged successfully but stopped before candidate intent because
  the selected timeout pair exceeded the reviewed ModemManager guard lifetime.
  Its run-bound staged final was removed before `-09`. Candidate and rollback
  transfer counts for `-06`, `-07`, and `-08` were all zero.
- The operator then requested one attended D1 recovery entry. Run
  `a90-d1-recovery-entry-20260805-01` sent `recovery` exactly once and observed
  the exact A90 in TWRP `3.7.0_12-0`. It performed no payload transfer,
  partition write, flash, rollback, or replay.
- The live device is therefore `RECOVERY_PENDING_PARKED`, not resident
  `HEALTHY`. No new D1 or F1 effect may start until an exact native return and
  fresh bounded D0 re-establish the installed H2 identity and health.
- The exact V2321 boot rollback remains present and hash-verified. Physical
  Download and TWRP recovery remain demonstrated and available.
- No D1 auto-handoff benchmark transaction is active, and no target is
  F1-armed. S22+ received no A90 command.

## Qualified Capabilities

- `A90_PHASE3_MINIMAL_H2_TWO_PHASE_AUTO_HANDOFF_BENCHMARK_V1` has reusable
  independent `PASS_GO` for its exact named native H2 and benchmark-parser
  closure. The first boot is unarmed; one exact later arm may create the enable
  state, and a subsequent ordinary boot may create the no-replay latch before
  one automatic `switch_root` dispatch.
- The exact H2 live resident-install and attended D1 integration closure has
  reusable independent `PASS_GO`. Its current focused bridge-stop and
  historical-ACM-epoch repairs also have `PASS_GO` over their changed hashes.
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

The H2 line adds two things without changing that product path:

1. a durable two-phase automatic-handoff enable/latch; and
2. bounded boot/handoff telemetry for before-and-after optimization comparison.

H2 installation proves resident health and first-boot non-dispatch. It does
not yet prove the complete armed automatic boot, Debian phase, native return,
retained latch, final health, or benchmark result.

## Selected Bounded Unit: H2 Automatic Handoff Benchmark

After an exact operator-controlled return from TWRP:

1. re-inventory and pin the exact A90 USB endpoint;
2. prove installed H2 `0.11.170` health and exact unarmed `enable=0/latch=0`;
3. reopen the exact V2321 rollback and demonstrated recovery binding;
4. build a fresh installed-resident D1 manifest from the closed `-09` F1
   result and current reviewed execution closure;
5. durably record one arm intent, send one exact arm, and prove
   `enable=1/latch=0`;
6. durably record one reboot intent and send one reboot without replay;
7. observe one automatic `switch_root`, Debian PID 1, SSH, display, and the
   complete benchmark boot segment;
8. observe automatic native return with `enable=1/latch=1`, exact cleanup, and
   final installed-resident health; and
9. preserve the result as the pre-optimization benchmark baseline.

An uncertain arm or reboot is never resent. Endpoint absence or a late
observation parks the ordinal; it does not authorize replay. No later benchmark
or optimization build starts until exact health is durable.

## Optimization Order

Do not start Full-LTO or other compiler optimization from an unmeasured state.
The order is:

```text
H2 automatic-handoff correctness
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
