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

- H3 remains the earlier automatic-handoff benchmark line. Its
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
- H5 run `a90-v3406-debian-display-f1-20260805-12` published its exact fresh
  2 GiB source and re-proved the source SHA, absent work/stage, absent H5
  enable/latch namespace, and exact V2321 starting health. Its candidate was
  never attempted: the A90 ModemManager guard found the transient global rule
  already owned by a concurrent S22+ F1 corridor and failed closed before
  candidate intent. The run is terminal `ABORTED_F1_V2_BEFORE_CANDIDATE` with
  candidate/rollback counts `0/0` and no replay.
- A post-terminal D0 re-proved exact V2321 `0.9.285`, self-test fail zero,
  pstore zero, and the exact A90 bridge. It observed only the expected run-12
  final source present; work and run stage remained absent. The other-target
  guard later released without A90 intervention.
- H5 run `a90-v3406-debian-display-f1-20260805-13` reused that exact published
  source read-only, staged and copied zero rootfs bytes, and installed boot-only
  candidate `0.11.173` exactly once. The durable result is
  `PASS_A90_RESIDENT_INSTALLED` / `RESIDENT_HEALTHY`, with candidate/rollback
  counts `1/0`, candidate replay false, and the global guard released.
- The post-install read-only D0 proved exact H5 build
  `phase3-minimal-h5-fresh-campaign-auto-benchmark`, self-test `11/1/0`, and
  exclusive unarmed state `binding=1 enable=0 latch=0`. SD capacity remained
  61408048 KiB total, 54419496 KiB used, and 3862540 KiB available at 93% use;
  no second 2 GiB staging copy was created.
- D1 run `a90-d1-attended-20260805-09` bound the exact installed H5 resident,
  immutable run-12 source, absent work, rollback, recovery, and one action. It
  armed once and rebooted once. The immediate host observation failed because
  exact bridge continuity did not validate, so the arm or reboot was not
  resent and Debian PID 1, SSH, and display visibility are not mechanically
  claimed for this ordinal.
- Read-only reconciliation found one new complete 15-stage benchmark segment
  followed by a partial returned-native segment. The exact opening 31-marker
  prefix and 19-marker appended suffix are now parsed independently. The
  selected complete segment records `switch_root_exec`, total handoff
  126444 ms, initial source SHA 37459 ms, post-display source SHA 11410 ms,
  and work copy 76068 ms.
- The same durable ordinal cleaned the fixed work copy exactly once and closed
  `NO_PROOF_OBSERVER_RESIDENT_HEALTHY`. Result payload SHA256 is
  `d1971edf46127cdc78d7cd678a42b5b071e1cbe4a6275300b607da1b05837fa3`.
  Exact H5 returned with `binding=1 enable=1 latch=1`, immutable source exact,
  work absent, guard released, and resident health true. No payload, partition
  write, flash, rollback, or replay occurred.
- H0 diagnosis identified the observer failure before NCM rebind: the runner
  performed exact bridge validation immediately during normal post-reboot
  by-id absence. The repaired observer now waits at most 30 seconds only while
  that exact bound path is absent, then requires the unchanged exact bridge;
  a present mismatch still fails immediately. Independent review returned
  `PASS_GO` with HIGH/MEDIUM zero and 230 related tests pass.
- Pre-reclaim read-only capacity was 61408048 KiB total, 54419524 KiB used, and
  3862512 KiB available at 93% use. No D1 transaction is active and no target
  is A90 F1-armed. Runs 11-13 and D1 run09 are terminal and must never be
  resumed or replayed. No A90 command was sent to S22+, and its files and
  device state remained untouched.
- A fresh read-only reclaim inventory re-proved exact H5 `0.11.173`, selftest
  fail zero, pstore zero, `binding=1 enable=1 latch=1`, exact H4 run-11 and H5
  run-12 2 GiB source identities, absent work/stage, and 3862508 KiB available.
  Its device-write and other-target-command counts are zero. The run01 draft
  manifest was superseded by later inventory-validation closure changes and is
  never live-eligible; the inventory itself passes the final loader.
- The exact one-use attended H4-source reclaim capability now has independent
  `PASS_GO` at execution closure
  `2c6f7b431cb82638638b4f891daa9a56deae27d1cb48621b93cadcab97cf8842`
  with HIGH/MEDIUM zero and 143 related tests passing. It selects only the
  host-preserved H4 run-11 source, protects the installed H5 run-12 source,
  requires final exact H5 health and latched state, and permits one unlink with
  no retransmit, payload, partition write, flash, restore, or S22+ authority.
- Live run `a90-h5-h4-source-reclaim-20260806-02` used that closure once and
  closed `PASS_H4_SOURCE_RECLAIMED_FROM_HEALTHY_H5`. One nonrecursive unlink
  removed only the H4 run-11 device source; the H5 run-12 source remained exact
  and work remained absent. Free space increased exactly 2097152 KiB to
  5959660 KiB available, within the bound 2031620..2162692 KiB. Final H5 health
  and `binding=1 enable=1 latch=1` passed. Dispatch count is one, retransmit is
  false, and payload, partition write, flash, rollback, and S22+ command counts
  are zero. Private result SHA256 is
  `127d5c147452561857502f4ad3f1b5e60ad1ac31e4c0cbe37c216cd6bf5e721e`.
- Historical-image GC run `a90-h5-historical-image-gc-20260806-01` bound a
  fixed set of twenty obsolete rootfs, clean-image, and WSTA snapshot files.
  All twenty exact byte identities have private mode-`0600` host recovery
  copies. The initial host aggregate validator rejected expected
  post-staging manifest enrichment before deletion intent or dispatch; the
  narrow validator repair passed independent incident rereview at closure
  `6046591ba7172eaecaf6c664f08520e0c4f271194038d788cc62a41bcd619401`
  with 70 tests and HIGH/MEDIUM zero.
- The same run then dispatched one nonrecursive unlink and closed
  `PASS_HISTORICAL_IMAGES_AND_SNAPSHOTS_RECLAIMED_H5_HEALTHY`. All twenty
  selected paths are absent, protected H5 run-12 is exact, work/stage are
  absent, and available SD space increased by 40370236 KiB from 5959648 to
  46329884 KiB. Final H5 `0.11.173`, self-test `11/1/0`, pstore zero, and
  `binding=1 enable=1 latch=1` passed. Dispatch count is one, retransmit is
  false, and payload, partition write, flash, rollback, and S22+ command
  counts are zero. Private result SHA256 is
  `2c83dfbdfd362082bed2bfec313c7665afd1621e06714a6da0c168fc91d715ff`.
- H6 host preparation now follows the required rootfs-first order. Run
  `a90-v3406-debian-display-f1-20260807-01` has one fresh private observer-keyed
  2 GiB rootfs with SHA256
  `b242fa73ee926d150ef8b8887734210bc4fd41f71597730647932c578fb1fd64`.
  Its absent remote destination is
  `/mnt/sdext/a90/runtime/debian-bookworm-arm64-phase2-display-v3406-keyed-20260807-01.img`.
- The corrected non-LTO H6 A/B build is byte-identical at boot SHA256
  `5e6774018d7e4601bde766521a78d58d90a7ec5851297d8f5c32bf13b7fa07fa`,
  version `0.11.174`, build
  `phase3-minimal-h6-observer-complete-baseline-auto-benchmark`, compiled
  binding `75c0f131e814ab27a123961c17a8082034425e371c9412284a7b78bc17f42231`,
  and fresh H6 enable/latch namespace. The superseded pre-rootfs H0 draft is
  not selected by any public manifest and has no live authority.
- Independent review returned `PASS_GO` for corrected H6 full thirteen-file
  closure `b9f4ddb19d177506bd2d271b50b1e7c305ebe74d1647d0dacbe3dd711a373c70`
  with HIGH/MEDIUM zero and 367 tests passing. No device, USB, private, or
  S22+ reviewer contact occurred.
- Fresh connected D0 for run `a90-v3406-debian-display-f1-20260807-01` passed
  after an H0-only direct-USB observer-route repair. It re-proved exact H5
  `0.11.173`, self-test `11/1/0`, pstore zero, exact H6 candidate and rollback,
  and absent H6 rootfs/work/stage destinations. D0 and path-preflight receipt
  SHA256 values are `50fcd36ecb6dc7fb421eed7b2a821b7bea9680f64b59f603930b56de3a1d8848`
  and `6493244c0ab1dbc0351750ac1e1bc29b913e3a4eaacab4e3425d798feec12ffd`.
  The failed route check issued no device command; the successful D0 issued
  reads only. S22+ was untouched.
- H6 immutable host preparation and resident-install compatibility binding are
  complete. The resident manifest SHA256 is
  `ef65322de1aa5d45b83a71b134b5cd5ea01aefd5cde706a58d1d20f2323b2091`
  and the approval-binding SHA256 is
  `6f5edde21ac92feb6bade8a67173c6a5b251994bec8d30288a16ba21252aa915`.
  This H0 preparation grants no live authority. No H6 staging, candidate
  transfer, flash, reboot, or D1 action has occurred yet; H5 remains exact and
  terminal.

## Qualified Capabilities

- The H3 exact compiled-rootfs binding and resident F1 closure has reusable
  independent `PASS_GO` for its named execution-critical hashes and E2 hazard.
- The current auto-benchmark observer/tail closure
  `60610b2deae343892506c0e13ef88e96c6993b5121fa1c88632410db208afd89`
  has independent `PASS_GO`. It binds exact NCM-before-SSH, all 15 mandatory
  handoff stages, a hash-bound opening-marker prefix plus appended suffix, and
  a bounded absence-only wait for the manifest-bound by-id endpoint before
  exact bridge, NCM, and SSH observation. A present mismatch is never retried.
- Historical closure
  `94be39687a91938d4f82d52242ce0025b3b19e4f8c8bbfd6cf46ff729dd3a5f4`
  remains the exact reviewed closure that finalized run09 from its already
  durable seven-record journal tail with no arm, reboot, handoff, or cleanup
  replay. It is retired from future live use by the post-reboot bridge-absence
  incident. The still earlier
  `e17d9e23e3f473d949cf264b54246ac01ec221fe133e0291a200437a0ed13959`
  receipt is superseded by the accumulated-log observer incident.
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
- The H5/H4 source-reclaim closure
  `2c6f7b431cb82638638b4f891daa9a56deae27d1cb48621b93cadcab97cf8842`
  has independent `PASS_GO` evidence for hazard
  `SD_CAPACITY_EXHAUSTION_BLOCKING_FRESH_SOURCE_AND_WORK_COPY`. The receipt
  qualified reuse only until first PASS, expiry, closure/hazard change, or a
  new incident. The exact run02 first PASS consumed and retired it; it must
  never dispatch again.
- The historical-image GC closure
  `6046591ba7172eaecaf6c664f08520e0c4f271194038d788cc62a41bcd619401`
  has independent incident-rereview `PASS_GO` for the fixed twenty-file set,
  exact host recovery bytes, protected H5, target-bound health, final use
  guards, and one nonrecursive unlink. Run01's durable dispatch consumed and
  retired the capability; it must never unlink or dispatch again. Its private
  recovery bytes remain evidence and grant no automatic restore authority.
- The corrected H6 observer-complete non-LTO baseline closure
  `b9f4ddb19d177506bd2d271b50b1e7c305ebe74d1647d0dacbe3dd711a373c70`
  has independent `PASS_GO`. It binds the fresh run-specific keyed rootfs,
  deterministic boot, compiled H6 markers, resident F1 interpretation, H6 D1
  identity, and the repaired absence-only post-reboot bridge observer. Reuse
  lasts only while those named hashes and hazard assumptions are unchanged and
  no new incident occurs; fresh D0, rollback/recovery, attendance, manifest,
  and inter-effect health remain mandatory live inputs.

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

## Selected Bounded Unit: Install and Close the H6 Observer-Complete Baseline

H5 installation and its first automatic-handoff ordinal are terminal. Preserve
runs 11-13 and D1 run09, their state namespaces, journals, private host bytes,
and no-replay evidence. Protect the installed H5 run-12 device source. The H4
source and the fixed historical-image/snapshot set have been reclaimed from SD;
their exact private host bytes and incident evidence remain preserved. Do not
reset H5 enable/latch, resend run09 arm or reboot, reuse either consumed reclaim
capability, or reinterpret a visible screen as missing mechanical PID1/SSH
evidence.

The run09 15-stage timing series is a usable diagnostic baseline for locating
cost: the two full source hashes and work copy dominate its 126444 ms handoff.
It is not yet a correctness baseline for compiler comparison because the host
observer lost exact bridge continuity before it could bind Debian PID 1, SSH,
service ownership, and display facts to the same ordinal.

The observer diagnosis, corrected rootfs-first H6 build, focused tests, and
independent capability review are complete with no device contact. The next
bounded work is:

1. preserve run09 and its H5 state namespace without replay or reset;
2. retain run02 as the consumed exact PASS that removed only H4, protected H5,
   and proved the bounded 2 GiB free gain; never reuse its capability receipt;
3. retain historical-GC run01 as the consumed exact PASS that removed its
   fixed twenty-file set, reclaimed 40370236 KiB, and preserved exact H5;
   never reuse its capability receipt or infer restore authority from host
   recovery bytes;
4. retain the committed corrected H6 closure and fresh connected D0 proof of
   exact H5 health, exact candidate and rollback, and absent H6
   rootfs/work/stage and enable/latch paths;
5. retain the fresh immutable H6 resident binding, then while the operator is
   attended with Download or TWRP recovery available permit at most one
   boot-only candidate transfer with no replay and exact rollback on failure;
6. from exact unarmed H6 resident health, run one new D1 automatic-handoff
   ordinal through the repaired observer and close Debian PID 1, SSH, service
   ownership, display, native return, cleanup, latch, telemetry, and final
   resident health together; and
7. start Full-LTO comparison only after one observer-complete automatic
   handoff baseline closes Debian PID 1, SSH, display, return, cleanup, and
   resident health together.

An attended visibility confirmation may be appended as evidence for run09,
but it cannot manufacture its missing mechanical PID1/SSH observation.

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
- `docs/reports/A90_PHASE3_MINIMAL_H6_OBSERVER_COMPLETE_BASELINE_INDEPENDENT_REVIEW_2026-08-07.json`
- `docs/reports/A90_H5_H4_SOURCE_RECLAIM_CAPABILITY_INDEPENDENT_REVIEW_2026-08-05.json`
- `docs/reports/A90_H5_HISTORICAL_IMAGE_GC_CAPABILITY_INDEPENDENT_REVIEW_2026-08-06.json`
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
