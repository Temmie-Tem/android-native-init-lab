# Goal: repeatable multi-device native PID 1

Build a repeatable path from an Android vendor boot chain and source-matched
vendor kernel to a custom static `/init` running as PID 1, then grow that entry
point into a minimal observable and recoverable Linux-style runtime.

Current targets are Galaxy A90 5G and Galaxy S22+. Target evidence, artifacts,
and authorization are isolated. `AGENTS.md` is the binding operating contract.

## Current Frontier - Process v2 Migration

**State: HOST-ONLY. The first Process v2 device-session canary completed the
exact candidate transfer and exact Magisk rollback, but retained only an
unterminated R4W1-B marker prefix. The durable verdict is
`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`. Final health passed. The exact USBFS
departure fix is tested and independently reviewed. No active S22+ F1
authorization. R4W1-D contiguous-proof implementation has passed one
complete-overlay clean Full-LTO build and output gate. That first
build exposed a vendor-build rewrite of three archive-owned source symlinks;
the adapter now pins and restores all five absolute archive symlinks, and a
second independent clean build proved that restoration plus byte-identical GKI
outputs. The final descriptor-bound restoration hardening passed local and
build-host focused tests plus independent review; it postdates both full
builds. Adapted full static audits of both builds and the durable A/B
reproducibility gate now pass with blocker count zero. Three separate
invocations inserted the exact R4W1-D Image into the exact R4W1-C watchdog
carrier in distinct directories. Raw boot, LZ4, single-member AP, and manifest
outputs are byte-identical;
the independent candidate checker and Process v2 offline D0 gate pass. The
manifest remains `draft-host-only`: no connected D0, preparation binding, or
live authority exists.**

The R4W1-C2 run did not start an Odin device session: its candidate and rollback
invocations were rejected while parsing `/proc/self/fd/7`. The R4W1-C3
regular-path adapter then proved host-only that the same boot-only artifacts can
be validated and supplied to Odin through real absolute `.tar.md5` paths.
R4W1-C3 remains `DRAFT_INACTIVE`; it will not be promoted as another bespoke
candidate policy.

The current task is to replace per-candidate helpers and policy activation with
the reusable process defined in
`docs/operations/DEVICE_ACTION_PROCESS_V2.md`.

## Established S22+ Evidence

- FYG8 stock and Magisk boot-only recovery artifacts are available and pinned
  in private evidence.
- A source-matched unmodified rebuilt kernel reached normal FYG8 Android and
  rolled back cleanly (`R3C1`).
- A retained `/proc/last_kmsg` marker proved execution of the custom Android
  `/init` path and clean rollback (`R4W1-A`).
- R4W1-C2 proved the sealed-FD Odin path is invalid before device-session start;
  it produced no native-PID1 result and no partition transfer.
- R4W1-C3 proved the ordinary regular-file transport contract host-only.
- Process v2 D0 proved the reusable target/profile preflight on one connected
  FYG8 device with bounded read-only collection and no F1 authority.
- The first Process v2 canary invocation reached Download but stopped before
  candidate attempt or transfer; its USBFS arrival-race fix is host-qualified.
- The next Process v2 canary completed candidate transfer and verified Magisk
  rollback. Two stable retained-log reads contained one candidate-specific but
  unterminated R4W1-B prefix, so the result remains no-proof. Exact measured
  Odin-node departure is now host-qualified without relaxing unrelated USB or
  replacement failures.
- The retained bytes match the R4W1-B record being split after 73 of 99 bytes;
  the wrapped suffix was replaced by following boot-log content. R4W1-D now
  backfills one 45-byte proof into a contiguous pre-cursor region without
  changing the ring index. Its host contract directly reopens the carrier
  boot/init inputs and requires current-overlay DT/vendor validation. A full
  build and output audit passed once. The first build left three audio-header
  symlinks pointing at the work tree; they were restored to archive values and
  a new manifest-derived automatic restoration gate passes focused tests. A
  second clean build observed those exact three mutations, restored all five
  archive-owned absolute symlinks, and reproduced every core GKI artifact. A
  later failure-path review hardened restoration around pinned root/parent
  descriptors, no-follow traversal, complete cleanup attempts, exact metadata
  restoration, and combined error reporting. The final revision passed 52
  local combined tests, 23 build-host focused tests, and independent re-review.
  The adapted full static auditor then reopened both builds, proved the exact
  final ELF control-flow and 45-byte no-index-publication backfill, regenerated
  matching FIPS integrity state, and retained 1,536 bytes of fixed-layout
  slack. Its A/B reproducibility checker passed every core artifact identity
  gate and exactly rebound the one recorded runtime symlink restoration to the
  current five-link manifest identity. Both static results and the durable
  reproducibility result have blocker count zero.
- R4W1-D candidate construction reuses the existing fixed-interval builder and
  independent checker through contract-bound adapters. Three distinct output
  directories produced exact raw boot SHA256 `18db8c8d...0b0e6fa0` and exact
  boot-only AP SHA256 `e35cee4c...a915d649`. The checker independently proved
  the watchdog carrier `/init`, D marker cardinality, fixed kernel replacement,
  stale AVB preservation, AP shape, and three-way byte identity. Process v2
  offline D0 returned `PASS_DEVICE_ACTION_D0_V2_OFFLINE_READY` for bundle
  `3a068ce7...01aa498`; the data manifest is intentionally not live-ready.

Historical details and retired clauses are preserved in:

- `docs/archive/policy/AGENTS_PRE_PROCESS_V2_2026-07-21.md`
- `docs/archive/roadmaps/GOAL_PRE_PROCESS_V2_2026-07-21.md`
- `docs/reports/`

Archived text is evidence only and grants no device authority.

## Immediate Roadmap

1. **P2.1 - Active-contract cleanup (complete):** current rules and frontier are
   separated from retired policy/history, with focused regression coverage.
2. **P2.2 - Reusable host implementation (complete):** target profile and
   candidate manifest schemas, approval-bound append-only journal with durable
   head, failure taxonomy, and one generic H0 core using regular paths.
3. **P2.3 - Host validation (complete):** test archive rejection, wrong target, changed
   hash, missing rollback, Odin local-parse failure, timeout, interruption,
   resume, simulated transfer outcomes, tail loss, and path containment with
   device access hidden. Independent review and remediation re-review returned
   `GO_HOST_CORE_TO_D0_IMPLEMENTATION`.
4. **P2.4 - D0 qualification (complete):** the reusable D0 adapter passed
   focused tests, independent review, strict result reopening, and one bounded
   connected read-only preflight. It created no F1 authority.
5. **P2.5 - F1 canary (current):** the reusable runner completed one exact
   candidate and rollback cycle and closed its journal, but the 99-byte witness
   crossed a retained-ring boundary and only its 73-byte first segment
   survived. USB arrival and exact-departure races are now narrowly closed.
   R4W1-D uses one contiguous 45-byte proof backfilled behind a saturated-ring
   cursor, with no diagnostic record and no index mutation. Focused host tests
   pass. One complete-overlay clean Full-LTO build passed: exact stock Image
   geometry, one-proof cardinality, banner, provider closure, 2,397 generated
   modules, and separate ELF `sec_log_buf.ko` all verified. The build exposed
   and the adapter now closes a vendor symlink-restoration gap. A second clean
   build proved the runtime restoration and reproduced `.config`, `Image`,
   `Image.lz4`, `vmlinux`, `System.map`, `vmlinux.symvers`, `abi.xml`, and both
   `modules.builtin` files byte-for-byte. Descriptor-bound failure-path
   hardening was added afterward and is focused-tested rather than claimed as
   part of those full-build results. The adapted full static audits pass for A
   and B, and the durable verdict is `PASS_R4W1D_CLEAN_REPRODUCIBILITY` with
   blocker count zero. Three deterministic R4W1-D boot-only candidate
   reproductions and their independent static audit now pass; a Process v2
   `draft-host-only` manifest also passes offline D0 validation. The next unit
   is one separately approved connected read-only D0 against this exact bundle,
   followed by data-only readiness promotion and F1 preparation. No live
   manifest or candidate transfer is currently authorized.

Do not activate C3, fork a C4 helper, or add another policy block. The source
review does not promote the manifest or authorize device contact. P2.5 remains
host-only until a separately approved connected D0 is completed, the manifest
is explicitly promoted, and the operator gives one fresh approval for that
exact prepared binding.

## Process

For each bounded unit:

1. **STATE:** inspect the current frontier, repository state, and last evidence.
2. **SELECT:** choose the smallest action tier that answers the question.
3. **DESIGN:** state expected evidence, stop conditions, and recovery.
4. **IMPLEMENT:** reuse the common path; do not fork for changed hashes or
   markers.
5. **STATIC VALIDATE:** run focused tests and artifact checks.
6. **DEVICE:** only when required by the selected tier and authorized under
   `AGENTS.md`.
7. **REPORT:** structured evidence by default; prose only for meaningful change
   or incident.
8. **COMMIT:** one scoped, validated unit.

## Success Conditions

The S22+ direct-PID1 rung closes when one Process v2 F1 run proves all of:

- exact boot-only candidate transferred to the attended FYG8 target;
- bounded evidence establishes execution of the intended native PID 1 path;
- the exact Magisk boot-only rollback succeeds;
- normal Android, Magisk root, expected boot identity, stock supporting
  partitions, orange verified-boot state, and no Odin endpoint return; and
- the structured journal can reconstruct the run without a bespoke report or
  helper-specific policy clause.

The long-term project succeeds when the same method supports repeatable native
PID 1 bring-up across target profiles without weakening target isolation or the
boot-only recovery boundary.

## Stop Conditions

- Any permanent safety boundary in `AGENTS.md` would need to change.
- Physical recovery is unavailable or rollback cannot be verified.
- Device identity or Odin endpoint is ambiguous.
- An unexplained device-session failure occurs.
- The same material host-side failure occurs twice.
- Three consecutive units add only policy, metadata, or review machinery with
  no new tested behavior. In that case, stop and select a substantive rung.
