# Goal: A90 native bridge to Debian runtime

Build the Galaxy A90 5G into a Debian-oriented system in which native-init
performs only the vendor-kernel and hardware bridge-up that Debian cannot yet
perform, then hands PID 1 and the runtime to the SD-backed Debian root with
`switch_root`.

`AGENTS.md` is the binding operating contract. This file is the active A90
objective. `GOAL.md` is the separate S22+ objective. Target evidence,
artifacts, approvals, transports, rollback identities, and health checks never
transfer between the two files.

## Current Authority

- This is an H0 planning and implementation line.
- No A90 F1 or other live-device action is currently authorized.
- All V3402 through V3406 live approvals and attended continuations are
  consumed and non-reusable.
- Exact V2321 health was restored after the V3406 display run.
- Do not add a device step while host-only work can answer the selected
  question.

## Final Architecture

The intended steady-state boot is:

```text
vendor boot chain and source-matched kernel
-> minimal native-init hardware bridge-up
-> immutable SD work-root verification
-> strict native display and service release
-> switch_root
-> Debian init as PID 1
-> Debian-owned services, networking, display, storage, and applications
```

Native-init is not the intended long-running product environment. It is the
early hardware-enablement and recovery bridge. Code may move out of native-init
only after a Debian-side consumer proves that it can own the same function and
the rollback/recovery contract remains intact.

## Proven Frontier

V3405 run `a90-v3405-debian-f1-20260731-01` is closed healthy/no-proof with:

- one checked boot-only candidate transfer;
- one exact V2321 rollback transfer;
- no candidate replay;
- one handoff;
- final exact V2321 health;
- no non-boot partition or internal-userdata action; and
- no command sent to the separately connected S22+.

The run directly proves this mechanism-level path:

```text
native-init strict display release
-> immutable work-copy handoff
-> switch_root
-> Debian sysvinit PID 1
-> USB-local Dropbear observation
-> no-sync supervisor return to healthy native-init
```

The live SSH evidence includes `pid1_comm=init`, a Debian init executable,
`dropbear_started=1`, and the Debian marker. This is a `switch_root` proof, not
a chroot inference.

Display release is also affirmative: both modeled presenter services stopped,
two remaining owners were killed, and the authoritative scan found zero
non-preserved owners before `switch_root`. The V3405 diagnostic Debian image
did not start a DRM/KMS presenter. Its black screen is therefore expected;
Debian display acquisition remains unimplemented and untested.

The no-sync supervisor bypassed V3404's global-`sync` return failure and
returned to the healthy native candidate. The original global-sync stall
remains supported but not proven as a kernel writeback diagnosis.

## Formal Result Boundary

V3405 remains formally:

`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`

The first candidate-return channel check lost the `A90P1 END` frame. The
observer collected retained pmsg only after that check, so retained-pmsg
closure was not reached. The Debian PID1, Dropbear, display-release, and
healthy-return subproofs remain valid, but they do not promote the atomic F1
result to PASS.

Return-channel framing and retained-pmsg collection ordering are a separate H0
observer unit. They are not part of the selected build-determinism unit below.

## Latest Live Result: V3406 Phase 2 Display

Run `a90-v3406-debian-display-f1-20260731-02` is closed as
`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`. It completed one candidate transfer,
one handoff, one exact V2321 rollback, no candidate replay, and final V2321
health restoration. No command was sent to the separately connected S22+.

The one handoff and USB-local SSH observation prove the following subpath:

```text
native KMS release with zero remaining DRM fds
-> switch_root
-> Debian /usr/sbin/init as PID 1
-> Dropbear
-> terminal display attempt 3 rc=1
```

The operator observed a black screen. Debian display acquisition was not
proved. The candidate also missed the bounded return contract and reappeared
only after the observer had closed, so late recovery availability does not
promote the result.

The Phase 2D observer has a confirmed host parser defect: its native-release
regular expression accepts LF but rejects the CRLF-terminated live ACM line.
Normalizing the preserved transcript makes the exact native-release validator
pass. This lost a valid subproof in the structured result but does not explain
the real presenter failure or bounded-return miss and cannot retroactively
promote the F1 result.

`docs/reports/A90_V3406_PHASE2_DISPLAY_NO_PROOF_F1_CLOSED_2026-07-31.md`

## Completed Bounded Unit: Phase 0 Build Determinism

Phase 0 closed `A90_V3404_BUILD_DETERMINISM_PHASE0_HOST_PASS`. Two clean,
isolated builds matched for boot, ramdisk, init, helper, and engine while the
accepted V3404 boot remained unchanged. The effective inherited builder chain
contains 171 modules. Golden hashes and tool versions are recorded in:

`docs/reports/A90_V3404_BUILD_DETERMINISM_PHASE0_H0_2026-07-31.md`

### Question

Can the latest effective A90 native-init boot builder produce byte-identical
artifacts twice from the same pinned inputs, without changing native-init C
source or overwriting the accepted V3404 artifact?

### Scope

The selected entrypoint is:

`workspace/public/src/scripts/revalidation/build_native_init_boot_v3404_d3_resolved_owner_timeout.py`

The accepted V3404 boot SHA256 remains the immutable reference recorded in:

`docs/reports/NATIVE_INIT_V3404_D3_RESOLVED_OWNER_TIMEOUT_SOURCE_BUILD_2026-07-31.md`

This unit may change only host-side build orchestration, a versioned
determinism helper, focused tests, and its H0 report. Native-init C, helper C,
the accepted private boot image, live manifests, runners, rollback artifacts,
and device state are out of scope.

### Design

1. Resolve and record the complete effective builder/import chain and every
   byte-affecting input before editing.
2. Hash the selected native-init and helper source closure and require those
   hashes to remain unchanged throughout the unit.
3. Audit archive order, cpio metadata, compiler timestamps/build IDs/random
   seeds, `mkbootimg` arguments, padding, inherited absolute paths, locale, and
   environment inputs.
4. Add the smallest versioned host helper and focused test needed to normalize
   only evidenced nondeterministic inputs.
5. Build in two fresh isolated private output roots. Never reuse or overwrite
   the canonical V3404 output path.
6. Compare the boot image, ramdisk cpio, init ELF, helper ELF, engine ELF, and
   normalized manifest byte-for-byte and by SHA256.
7. Preserve two identities when normalization changes bytes:
   - the accepted V3404 reference identity, which remains historical and
     untouched; and
   - the first reproducible profile identity, accepted only after two clean
     builds match.
8. Record toolchain versions, complete fixed arguments, input hashes, both
   build receipts, and the resulting golden hashes in one H0 report.

### Static Validation

- focused determinism tests pass;
- touched Python passes `py_compile`;
- both isolated builds complete from the same pinned inputs;
- all declared output pairs are byte-identical;
- native-init and helper source hashes are unchanged;
- the accepted V3404 private artifact is unchanged;
- tracked diffs contain no private identifiers or compiled payloads; and
- `git diff --check` passes.

### Phase 0 Success

Phase 0 closes only when an independent rerun on a qualified host can use the
same pinned inputs and versioned procedure to obtain the documented
reproducible profile hashes. A single successful build, equal ELF semantics,
or a report that omits one byte-affecting input is not enough.

### Phase 0 Stops

Stop and report without repairing when:

- a selected native-init or helper source byte changes;
- the accepted V3404 artifact would be overwritten or rebound;
- an input is missing, mutable, unpinned, or silently taken from a legacy
  fallback;
- either clean build differs and the difference cannot be fully attributed
  within this bounded unit;
- a fix would alter candidate runtime behavior rather than build metadata;
- private material would enter a tracked diff; or
- any device, network-to-device, reboot, staging, flash, or live approval step
  becomes necessary.

## Selected Bounded Unit: Phase 1 Flat Builder

Flatten the measured 171-module effective builder into one versioned,
reviewable snapshot without editing native-init or helper C. The flat builder
must reproduce all five Phase 0 golden hashes in two fresh isolated builds.
Until that equality passes, the inherited chain remains authoritative and the
flat builder creates no candidate or live authority.

The first Phase 1 audit stopped
`STOP_HOST_ACCEPTED_PATH_REWRITE_HASH_UNCHANGED`: duplicate module identities
defeated a `main()` interception and the host builder rewrote the canonical
accepted path. Its bytes and all tracked sources remain unchanged, but its
timestamp changed, so the no-overwrite contract failed. Do not retry that
method. A successor must use a disposable module tree or pre-import entrypoint
replacement and first fault-test that the canonical output cannot be opened.

`docs/reports/A90_V3404_FLAT_BUILDER_PHASE1_STOP_H0_2026-07-31.md`

A successor then repeated the same material host failure twice. Direct
write-open fault injection passed, but upper legacy post-processing continued
after the intercepted common `main()` and replaced the canonical path through
an unguarded operation. Content SHA stayed unchanged and no device action
occurred, but mtime changed again. Phase 1 is stopped under the two-failure
rule. Do not retry in-process monkey-patching or Python audit-hook containment.
A future restart requires a new H0 design with a fully disposable repository
clone that has no path to the canonical private tree.

`docs/reports/A90_V3404_FLAT_BUILDER_PHASE1_SUCCESSOR_REPEATED_STOP_H0_2026-07-31.md`

Phase 1A is the selected new H0 design. It uses a minimal disposable tracked
export plus exact copied inputs inside a bubblewrap namespace where the
canonical repository path is absent. The schema is `flat-builder-v1`, not a
new candidate version. Its binding plan is:

`docs/plans/A90_V3404_FLAT_BUILDER_PHASE1A_DISPOSABLE_CLONE_PLAN_2026-07-31.md`

Phase 1A closed
`A90_V3404_PHASE1A_ISOLATED_PATH_ATTRIBUTION_PASS`. Unmapped clone A/B matched
init/helper but changed engine/ramdisk/boot. Two Doom `__FILE__` strings carried
the build root. A clone-private prefix-map restored all five Phase 0 hashes
exactly, proving complete path attribution. The original golden remains a
bridge control but is not portable.

`docs/reports/A90_V3404_FLAT_BUILDER_PHASE1A_ISOLATED_PATH_ATTRIBUTION_H0_2026-07-31.md`

Phase 1B closed
`A90_V3404_FLAT_BUILDER_PHASE1B_PORTABLE_AB_PASS`. The effective state is now
one flat manifest with 84 native-init flags, 25 inherited helper feature flags,
60 native-init and 80 Doom translation units, three materialized generated
sources, a read-only buildlib, and one writer. A disposable sandbox A/B
produced the following portable golden hashes:

```text
init     beb44eea342e5a151f66b0379c3fb3872b7c29d61afaa27d3946072975606628
helper   fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef
engine   5b262978867bf98239e5d7e1b112f29b0217b59f057fc48c5b6e91d90eb5eaad
ramdisk  38e1edc8d9e8b0f396acaf366ef7d48311595a51df4ddf7849e183c8c505cbf2
boot     5839b260ef30d7ece9566a296155f571ad62b7f90ba3499b687f3db53eb956c2
```

Init and helper retain exact Phase 0 identity. Offline ramdisk comparison
attributes the new ramdisk and boot identities only to the engine's stable
`/usr/src/a90/doomgeneric` source prefix. No final artifact contains the
canonical repository or sandbox source path. The accepted V3404 artifact is
unchanged.

`docs/reports/A90_V3404_FLAT_BUILDER_PHASE1B_PORTABLE_AB_H0_2026-07-31.md`

Phase 1C closed
`A90_V3404_FLAT_BUILDER_PHASE1C_COMMITTED_EXPORT_PASS`. A wholly fresh
disposable export of committed `HEAD`
`79e5424da8be26b0bde77fb081f2725446d741f5` reproduced the same five portable
hashes in byte-identical A/B builds without copying any working-tree file into
the clone. The clone fault test passed with the canonical repository absent,
the committed builder and manifest hashes matched, both sides were free of
canonical and sandbox source paths, and the accepted V3404 artifact remained
unchanged.

`docs/reports/A90_V3404_FLAT_BUILDER_PHASE1C_COMMITTED_EXPORT_H0_2026-07-31.md`

Phase 1D closed
`A90_V3404_FLAT_BUILDER_PHASE1D_SHALLOW_MANIFEST_PASS`. A two-line
`flat-builder-v1-noop` child resolves to the exact V3404 effective data and
effective hash. The resolver permits one child over one flat sibling baseline,
tracks leaf-source provenance, and rejects cycles, deeper chains, path-like
parents, unknown keys, type changes, execution manifests outside the versions
tree, manifest/profile symlinks, and any candidate-authority escalation.
Receipts bind the effective hash plus ordered raw child/parent hashes, and the
raw lineage is revalidated after each build before receipt acceptance. Focused
tests passed `14/14`.
Final-code A/B reproduced all five Phase 1C portable hashes, left the accepted
V3404 artifact unchanged, and retained static AArch64 closure with no source
path leak. Independent H0 review returned `GO` with no Critical, High, or
Medium finding against the latest source hashes and fresh `ab-03` receipt.

`docs/reports/A90_V3404_FLAT_BUILDER_PHASE1D_SHALLOW_MANIFEST_H0_2026-07-31.md`

Phase 1 is closed. The flat V3404 effective snapshot and shallow resolver are
the qualified host baseline for future versions. The 171-module Python
mutation chain remains historical evidence and is not deleted. No V3406
identity was created.

Phase 2A closed `A90_PHASE2A_DRM_VTLESS_HANDOFF_CONTRACT_PASS`. The carried
kernel has direct MSM DRM/KMS but no Linux VT, DRM fbdev emulation, DRM lease,
or devtmpfs. The supported steady-state model is therefore one VT-less Debian
direct-DRM session, not a VT/logind/fbcon handoff.

The inventory also found a concrete native release gap. PID 1 opens KMS for
the boot splash before it forks autohud; the ordinary DRM descriptor is not
close-on-exec, no primary-KMS teardown API exists, and the D3 final scan
excludes PID 1. A zero child-owner count does not prove that PID 1 released its
DRM descriptor. The V3405 diagnostic Debian image contains no presenter or
display service, which explains its expected black screen. Older D-public
evidence proves Debian can acquire and present on this panel, but that helper
ignores `SET_MASTER` failure and is not bound into the current rootfs.

The exact native-release, all-process fd audit, VT-less Debian service,
acquisition marker, and failure contracts are recorded in:

`docs/reports/A90_PHASE2A_DRM_VTLESS_HANDOFF_CONTRACT_H0_2026-07-31.md`

Phase 2B closed `A90_PHASE2B_DISPLAY_HANDOFF_SOURCE_H0_PASS`. D3 strict cleanup
now disables and destroys native PID 1 KMS state, drops master, closes the
close-on-exec DRM descriptor, scans PID 1 plus every other process for zero DRM
fds, and writes a fail-closed release marker into the verified work root before
mount movement. D4 preserve semantics remain separate.

The current-source Debian profile requires that release proof, acquires exact
DRM master, proves sole fd ownership and Debian PID 1, then drops to numeric
UID/GID 3904 with zero effective capabilities and no-new-privileges before
`SETCRTC`. Its marker binds the sysfs-matched device number and complete
ownership/mode state. A sysvinit `once` launcher allows three attempts without
VT, network, reboot, sync, or sysrq dependence.

Native boot, ramdisk, init, helper, and engine were byte-identical across A/B.
The static presenter and normalized 2 GiB Debian ext4 image were also
byte-identical across A/B and both filesystems passed read-only `e2fsck`.
Historical V3404 closure drift remains fail-closed, the accepted V3404 boot and
V3405 base remained unchanged, and both host manifests grant no candidate
authority. Independent review found and closed pre-SETCRTC capability proof
and DRM major/minor marker gaps, then returned `GO` with no remaining Critical,
High, or Medium finding.

`docs/reports/A90_PHASE2B_DISPLAY_HANDOFF_SOURCE_H0_2026-07-31.md`

Phase 2C closed `A90_PHASE2C_HOST_PROFILES_BOUND_NOT_LIVE_READY`. One
machine-readable H0 packet now reopens and binds both A/B sides of all five
native artifacts, both clean 2 GiB ext4 images, and both static presenters. It
also re-audits the exact coupled A90 checked boot-only route and the absent-only
hard-link staging lifecycle.

The clean Phase 2B ext4 image has no observer authorized key, generated
Dropbear host key, native release marker, display-ready marker, or
display-failure marker. It is therefore a deterministic base, not the final
keyed rootfs. The current staging adapter accepts only V3403-V3405 identities,
and the current orchestrator observes Debian PID 1/Dropbear/return but not the
new native release, DRM acquisition, bounded failure, or physical visibility
contracts. No candidate identity, staging, device action, or live authority
was created.

The observation packet now requires exact native KMS teardown, Debian sole DRM
master under UID/GID 3904 with zero effective capabilities, four fixed visible
screen strings through a bound attended receipt, terminal attempt-3 failure
without replay, healthy no-sync return, retained armed pmsg, one rollback, and
final baseline health.

`docs/reports/A90_PHASE2C_DISPLAY_QUALIFICATION_OBSERVATION_PACKET_H0_2026-07-31.md`

Phase 2D host implementation closed
`A90_PHASE2D_V3406_EXECUTION_CLOSURE_H0_PASS`. A new-inode per-run key
materializer, split display observer, bounded A90 D0 helper, V3406
absent-only staging contract, attended visible-confirmation flow, recovery
evidence revalidation, and host-only finalizer are now integrated. The
finalizer hard-pins the canonical V2321 rollback, while staging and finalizer
both revalidate the connected-preflight helper's path, size, and SHA256.

Malformed display evidence, including the observer module's distinct
exception type, is fail-closed `NO_PROOF` and cannot preempt the
already-authorized rollback. Integrated tests passed `185/185`; the Phase 2C
machine closure passed `6/6`; Python and diff checks passed. Independent
review returned `GO` with zero unresolved High or Medium findings and no
device action.

`docs/reports/A90_PHASE2D_V3406_EXECUTION_CLOSURE_H0_2026-07-31.md`

The next bounded unit is H0 incident closure, not another F1. Fix and
independently review the CRLF observation parser, preserve and diagnose the
presenter attempt-3 `rc=1`, and classify the bounded-return framing/deadline
miss. Retained-work cleanup remains separate and must not precede evidence
preservation.

## Later Phases

Phase 1 flattens the measured inherited builder/import chain into one
versioned, reviewable snapshot. The flat builder must reproduce the Phase 0
golden identity before the inherited chain can be retired.

Phase 2 gives Debian explicit DRM/KMS ownership after `switch_root`: inventory
the carried kernel interfaces, define the Debian presenter and VT/session
contract, and prove acquisition without reintroducing a native display owner.

Phase 3 moves networking, Dropbear/SSH policy, logging, health reporting,
storage lifecycle, and application supervision to Debian one function at a
time. Native-init retains only functions Debian has not yet proven.

Phase 4 minimizes native-init to hardware bridge-up, immutable handoff,
bounded recovery, and diagnostics. Production stability work follows the
proved dependency order rather than deleting code by size alone.

No later phase creates live authority. Each device rung still requires its own
fresh tier classification, preflight, immutable identity, recovery path, and
approval under `AGENTS.md`.

## Evidence to Preserve

- `docs/reports/A90_DEBIAN_REACTIVATION_F1_CLOSED_2026-07-30.md`
- `docs/reports/NATIVE_INIT_V3403_D3_IMMUTABLE_HANDOFF_H0_CLOSURE_2026-07-30.md`
- `docs/reports/NATIVE_INIT_V3404_D3_RESOLVED_OWNER_TIMEOUT_SOURCE_BUILD_2026-07-31.md`
- `docs/reports/A90_V3404_D3_SWITCHROOT_NO_PROOF_F1_CLOSED_2026-07-31.md`
- `docs/reports/A90_V3404_D3_WORK_COPY_POSTMORTEM_DEBIAN_PID1_PROVEN_2026-07-31.md`
- `docs/reports/A90_V3405_D3_SYNC_DECISION_SUPERVISOR_H0_2026-07-31.md`
- `docs/reports/A90_V3405_F1_RETAINED_PMSG_NCM_REBIND_H0_2026-07-31.md`
- `docs/reports/A90_V3405_DEBIAN_PID1_F1_CLOSED_2026-07-31.md`
- `docs/reports/A90_V3406_PHASE2_DISPLAY_NO_PROOF_F1_CLOSED_2026-07-31.md`
- `docs/reports/A90_V3404_BUILD_DETERMINISM_PHASE0_H0_2026-07-31.md`
- `docs/reports/A90_V3404_FLAT_BUILDER_PHASE1_STOP_H0_2026-07-31.md`
- `docs/reports/A90_V3404_FLAT_BUILDER_PHASE1_SUCCESSOR_REPEATED_STOP_H0_2026-07-31.md`
- `docs/reports/A90_V3404_FLAT_BUILDER_PHASE1A_ISOLATED_PATH_ATTRIBUTION_H0_2026-07-31.md`

Private journals, structured results, raw logs, work-image evidence, approval
receipts, and exact rollback identity remain under `workspace/private/`.
Tracked goal text must not copy their target identifiers, addresses,
credentials, or device-specific private paths.

## Process

For each A90 bounded unit:

`STATE -> SELECT -> DESIGN -> IMPLEMENT -> STATIC VALIDATE -> DEVICE -> REPORT -> COMMIT`

Omit `DEVICE` for H0. Use scoped staging, preserve immutable inputs after
intent, and never repeat a proven device transition because reporting failed.

## Goal Success Conditions

The A90 goal is complete only when:

- Debian becomes PID 1 by `switch_root` on a reproducible immutable image;
- Debian owns the intended steady-state services and display;
- native-init has a small, documented hardware-bridge and recovery surface;
- every retained native function has a named unproved Debian dependency;
- bounded observation and exact rollback remain available; and
- repeated boot/return and failure-injection evidence supports personal
  production use without broadening partition authority.

## Goal Stop Conditions

- A permanent boundary in `AGENTS.md` would need to change.
- A90 target, rollback, recovery, or health identity is ambiguous.
- Work would reuse a consumed run, approval, or attended continuation.
- A failure would require candidate replay or a non-boot write.
- The S22+ evidence line or tooling would be treated as A90 proof.
- Three consecutive units add only policy or review with no tested behavior.
