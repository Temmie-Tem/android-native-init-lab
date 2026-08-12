# A90 Goal

## Objective

Build the operator-owned Samsung Galaxy A90 5G into a Debian-oriented personal
server. Native init performs only the vendor-kernel and hardware bridge-up that
Debian cannot yet perform, mounts the existing UFS appliance root read-only,
and transfers PID 1 with `switch_root`. The production steady state is Debian
PID 1, authenticated SSH, final Wi-Fi, and a minimal Debian `/dev`.

`AGENTS.md` and `docs/operations/targets/A90_TARGET_CONTRACT.md` are binding.
This file records current state and the next bounded unit; it grants no device
authority. Historical detail lives in the A90 campaign ledger, incident and
review reports, and Git history. The pre-H2 snapshot remains archived at
`docs/archive/roadmaps/GOAL_A90_PRE_H2_2026-08-05.md`.

Target identities, artifacts, transports, evidence, recovery, and commands
never cross between the two goals. The same non-transfer rule also applies to
the separately registered S20+ goal and every future target row.

## Exact Current State

- H24 `0.11.192`, build
  `phase3-minimal-h24-ufs-auth-native-hud-private-card-root-minimal-debian-dev`,
  is the exact installed resident. Its attended F1 wrote and read back one
  deterministic boot-only candidate and closed
  `PASS_A90_H24_UFS_RESIDENT_INSTALLED` / `RESIDENT_HEALTHY`. Candidate replay
  is false, rollback transfer count is zero, and the host guard was released.
- The separately approved H24 D1 run consumed exactly one arm, reboot, and
  handoff. It verified and mounted the read-only UFS root and four writable
  tmpfs paths, then stopped at `persistent-hud rc=-22 errno=22` before evidence
  bind, Wi-Fi handoff bind, `switch_root`, or Debian PID 1.
- Same-intent cleanup proved the UFS root unmounted, userdata unchanged, zero
  userdata writes, and no recovery requirement. The device returned to exact
  native `RESIDENT_HEALTHY` with `binding=1 enable=1 latch=1`. The terminal is
  `REFUTED_H24_POST_ROOT_FAILURE_ATTRIBUTED_NATIVE_FALLBACK_HEALTHY`.
- The H24 D1 effect is consumed and is never replayed. Its live evidence proves
  only the outer HUD-stage `EINVAL`; the inner syscall remains unproved.
- V2321 remains the exact bound rollback for a future, freshly qualified
  successor. No successor candidate, approval, transfer, reboot, or D1 effect
  is authorized by this goal.
- S22+ and S20+ command counts for the H24 transaction are zero. Their profiles,
  approvals, evidence, and authority do not transfer to A90.

## Proven Product Mechanics

The following are established capabilities, not standing live authority:

- A boot-only native resident can be installed with exact rollback, durable
  intent, post-transfer source revalidation, candidate no-replay, and terminal
  resident health.
- Reviewed native source can resolve the UFS appliance partition at runtime,
  verify its identity and clean ext4 state, mount it
  `ro,noload,nosuid,nodev`, verify its content, prepare bounded writable tmpfs,
  and construct a minimal Debian `/dev` with mandatory devpts. Earlier live
  lanes reached `switch_root`; the exact current minimal-`/dev` combination has
  not yet been live-proved.
- H10 proved the minimal automatic loop can reach `switch_root` in about one
  second after dispatch. H16 proved the direct UFS path avoids the former
  multi-gigabyte SD work-copy and reached the UFS `switch_root` boundary in
  about 11.8 seconds on its successful mechanical run.
- H24's reviewed design proves that native devtmpfs need not be moved into
  Debian: Debian is intended to receive a bounded tmpfs `/dev`, while a native
  HUD card capability is isolated in a separate private root. The H24 D1 run
  stopped before those post-HUD steps, so their live execution remains unproved.
- Debian display, SSH, and Wi-Fi have each been observed in earlier bounded
  experiments, but H24 did not prove them in one terminal persistent-server
  run. Do not combine evidence from different ordinals into a new PASS.

## Retired Successor Experiments

- H19-H23 were host-only successors retired before live use as their display
  ownership or device-isolation assumptions failed review.
- H25 `0.11.193` was also host-only and is `NO_GO_RETIRED`. Its `chroot` design
  left the old mount graph reachable as a namespace capability; its boot
  self-test could leave parent mounts, touch an unowned fixed path, be rerun or
  overwrite boot evidence, and did not close every reap/parser/receipt failure
  path. No H25 runner, approval, connected D0, flash, reboot, or handoff ever
  existed. Its draft source and manifest were removed and its untracked build
  output was moved to trash.
- Retired identities, paths, artifacts, reviews, and evidence are never
  reinterpreted as a fresh successor.

## Selected Bounded Unit: Handoff Reduction and Headless Successor Design

The current unit remains H0 architecture only. A fresh static audit found that
the existing persistent native Wi-Fi companion cannot simply be carried into a
headless successor: it retains the old Android root in a private mount
namespace while Debian receives the shared PID namespace and `/proc`. A private
mount namespace alone does not prevent Debian root from reaching a surviving
process through `/proc/<pid>/root`, `fd`, or `ns/mnt`.

The binding plan is
`docs/plans/A90_UFS_HANDOFF_ARCHITECTURE_AND_PRODUCTION_REDUCTION_PLAN_2026-08-12.md`.
Its ownership decision is refined by
`docs/plans/A90_HEADLESS_HANDOFF_MINIMUM_AND_WIFI_OWNERSHIP_DECISION_2026-08-13.md`
and the host incident report
`docs/reports/A90_NATIVE_WIFI_SIDECAR_PROC_ROOT_EXPOSURE_HOST_INCIDENT_2026-08-13.md`.
This unit does not build a successor and does not touch the device, UFS root,
boot partition, private evidence, or another target. No H26 identity or path is
allocated.

Before the next candidate, one separately qualified no-payload Wi-Fi ownership
test must decide whether all native Wi-Fi/Android companions can be stopped and
reaped while `wlan0` remains suitable for Debian takeover. Its terminal is only
`TRANSFER_FEASIBLE`, `TRANSFER_REFUTED`, or `NO_PROOF`; it never proves Debian
or resident health.

If transfer is feasible, the next implementation candidate uses a fresh
identity after H25 and is headless:

- persistent native HUD disabled;
- firstboot overlay disabled;
- boot chime disabled;
- every native Wi-Fi sidecar gone before `switch_root`;
- Debian owns Wi-Fi from a boot-private, non-SD input;
- read-only UFS root, bounded writable tmpfs set, minimal Debian `/dev`,
  authenticated SSH, final Wi-Fi, exact cleanup/recovery, and no-replay kept;
- a distinct persistent-result model that proves headless Debian service
  health, explicitly makes no display-success claim, and remains
  `HEALTH_PENDING_PERSISTENT_DEBIAN` until an exact attended return.

If transfer is refuted, work returns to H0 for a separately reviewed nested
PID-namespace supervisor. It is not an automatic fallback. The exact successor
ordinal, version, build, enable/latch paths, artifact pins, qualification, D0,
F1 approval, and D1 approval remain future work. Nothing in this document
reserves or authorizes them.

## What Stays in the Critical Path

- exact A90 target/profile and compiled binding;
- fresh dynamic UFS identity, size, unmounted, clean-ext4, marker, and content
  verification;
- versioned enable and latch with one-shot/no-replay journal semantics;
- exact boot-only candidate and rollback recovery;
- read-only `ro,noload,nosuid,nodev` root mount;
- bounded tmpfs writable paths and boot-private SSH authorization;
- fresh minimal Debian `/dev`, mandatory devpts, and no native-devtmpfs move;
- final Wi-Fi with an explicit owner and no Debian-visible old-root sidecar;
- a compact durable cache receipt plus authenticated same-run observation,
  replacing the SD evidence sidecar before the next candidate;
- strict pre-exec failure attribution, mount restoration, and final native
  health;
- final Debian PID 1, authenticated SSH, final Wi-Fi, minimal-device-tree, and
  same-run evidence.

## What Leaves or Moves Out

Remove from the next headless critical path now:

- persistent native HUD bootstrap and display-health predicates;
- H25 HUD self-test and all H25 design artifacts;
- firstboot overlay injection;
- boot chime autoplay;
- the hard SD evidence bind and compiled SD Wi-Fi property-root dependency.

Move out of the eventual production init after the headless lane is stable:

- legacy SD image/work-copy and hashing machinery;
- UFS formatter/populator commands;
- manual HUD and experimental display commands;
- benchmark and verbose qualification telemetry not needed for field recovery;
- smoke HTTP, optional tunnel, and HUD-intent logic in the installed Debian
  firstboot script;
- obsolete candidate-specific adapters and reports from the shipped image.

Keep host-side approval, durable journal, exact rollback, and recovery tooling.
Those are safety machinery, not target runtime bloat.

## Product Sequence

1. Freeze and independently review this reduction boundary.
2. Qualify and perform one attended no-payload Wi-Fi ownership test; do not arm
   handoff, mount UFS, reboot, or flash as part of that test.
3. Select Debian-owned Wi-Fi only on exact `TRANSFER_FEASIBLE`; otherwise stop
   for a separately reviewed PID-namespace design.
4. Design one fresh headless candidate; do not patch or reuse H25.
5. Build and host-validate it, including a before/after size and handoff-time
   baseline. Qualification remains host-only.
6. Require fresh connected D0 and exact attended F1 approval before one
   boot-only resident install.
7. Require exact resident health, then a separate attended D1 approval before
   one arm/reboot/handoff.
8. While Debian remains the persistent live runtime, publish only its exact
   service evidence and `HEALTH_PENDING_PERSISTENT_DEBIAN`; do not call the
   native resident healthy. After an attended return or recovery, require exact
   native `RESIDENT_HEALTHY`. Missing display is expected in the headless lane,
   not a failure.
9. Replace the hard SD evidence bind and compiled Wi-Fi property-root path
   before the next headless candidate. After its resident install, prove an
   attended no-SD D0 before approving handoff; absence of SD is not yet a
   proved resident invariant.
10. After repeatable headless success, split experimental source modules and
   rebuild the Debian firstboot content as a separate rootfs/config change.
11. Add display later as a separate optional capability, preferably owned by
   Debian. Any persistent native HUD needs a fresh hazard design and review.
12. Consider section garbage collection and then Full-LTO only after functional
   boundaries and comparable benchmarks are stable.

## Evidence

Canonical public records include:

- `docs/operations/CAMPAIGN_LEDGER_A90.md`
- `docs/reports/A90_H24_MINIMAL_DEBIAN_DEV_INDEPENDENT_REVIEW_2026-08-12.json`
- `docs/reports/A90_H24_UFS_F1_D1_EXECUTION_INDEPENDENT_REVIEW_2026-08-12.json`
- `docs/reports/A90_H24_PERSISTENT_HUD_BOOTSTRAP_EINVAL_INCIDENT_2026-08-12.md`
- `docs/reports/A90_H25_HUD_CHROOT_AND_SELFTEST_REPLAY_HOST_INCIDENT_2026-08-12.md`
- `docs/reports/A90_NATIVE_WIFI_SIDECAR_PROC_ROOT_EXPOSURE_HOST_INCIDENT_2026-08-13.md`
- `docs/plans/A90_UFS_HANDOFF_ARCHITECTURE_AND_PRODUCTION_REDUCTION_PLAN_2026-08-12.md`
- `docs/plans/A90_HEADLESS_HANDOFF_MINIMUM_AND_WIFI_OWNERSHIP_DECISION_2026-08-13.md`

Private manifests, journals, raw logs, artifacts, device identifiers, network
identifiers, and credentials remain under `workspace/private/` and are never
committed.

## Success Conditions

- Current documentation names H24, its consumed D1 refutation, and the exact
  no-replay/native-health boundary without overclaiming the failing syscall.
- H25 is unambiguously retired before qualification or live use.
- The Wi-Fi owner is decided before a successor identity is allocated, and a
  private mount namespace alone never proves old-root isolation.
- The critical-path inventory distinguishes device safety from experiment
  convenience and from later product cleanup.
- Any future headless successor keeps the permanent boot-only, rollback,
  recovery, isolation, evidence, and target-selection boundaries.
- GOAL remains a current-state document rather than another historical ledger.

## Stop Conditions

Stop and remain H0 if exact target, resident, UFS identity, rollback, recovery,
source/artifact binding, or terminal health is ambiguous; if any previous effect
is not durably terminal; if a candidate would reuse a retired identity; if a
forbidden partition or native devtmpfs exposure appears; if evidence would need
to combine different runs; or if another target's profile, command, approval,
or evidence enters the A90 scope.
