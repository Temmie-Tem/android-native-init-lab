# A90 boot-only F1 owner v1 — structural design

Date: 2026-08-17
Target: operator-owned Samsung Galaxy A90 5G only
Tier of this document: H0 structural design
Device or live effect of this document: none
Status: **H0 IMPLEMENTATION CORE PRESENT — live execution is hard-disabled.
Runtime qualification, device preflight/final observer, crash-prefix resume,
and the required independent full review remain absent. This qualifies nothing
and grants no authority.**

This design exists to stop a loop, not to add a feature. Six independent
reviews of the per-candidate H27 runner each found real defects, and the
pattern was structural rather than accidental: every candidate got its own
~3,900-line runner, so every candidate required a fresh full review of safety
machinery that had nothing to do with the candidate.

The correction is one sentence: **review the code once, and make each candidate
data.**

## The loop being removed

Two mechanisms produced it.

**Self-reference.** The per-candidate runner stores review findings — reviewer,
date, incident class, validated invariants — as code constants. Filling them
after a review changes the source, which changes the execution closure, which
requires another review. The fifth review said so directly: filling the
bindings changes the closure, so re-freeze and re-review. There is no fixed
point.

**Lineage drag.** H27's runner inherited H24's, which inherited H18's. Booting
one kernel therefore re-validated rootfs staging, UFS inventory, Debian
handoff, display, SSH, and a seven-record H24 D1 journal. Reviews spent their
attention on machinery this experiment never executes, and the defects they
found were mostly in that inherited surface: an H18 predecessor left bound in
32 places, colliding journal namespaces, a `d1_runner_qualified` expectation
for a D1 runner that does not exist.

Both are removed by separating the reviewed artifact from the reviewed-about
artifact.

## The rule that breaks the cycle

**Review artifacts sign the owner closure. The owner closure never contains
review artifacts.**

A capability review signs a digest of the owner's source. That signature lives
outside the source, so producing it cannot change what it signed. The owner
carries no reviewer name, no review date, no incident class, and no invariant
list.

## Two review layers

| layer | when reviewed | changes with |
|---|---|---|
| owner capability | only when owner code changes | code |
| candidate manifest + hazard qualification | every candidate | data |

H28 (`CONFIG_ANDROID_BINDERFS=y`) and later candidates add a manifest and a
hazard qualification. They do not touch owner code, so they do not re-open the
owner capability review.

## Current implementation checkpoint

The current tree now contains the reusable stdlib-only owner, its strict
contract/journal module, and focused hostile tests:

- `workspace/public/src/scripts/server-distro/a90_boot_only_f1_owner_v1.py`;
- `workspace/public/src/scripts/server-distro/a90_boot_only_f1_contract_v1.py`;
- `tests/test_a90_boot_only_f1_owner_v1.py`.

The implemented H0 core rejects noncanonical or authority-bearing manifests,
binds direct regular artifact FDs, derives approval from the exact target,
boot, run, manifest, artifact, executable, observation, recovery, and hazard
inputs, journals candidate and rollback as separate one-shot attempts, and
validates the candidate-neutral success terminal. The CLI `execute` action
unconditionally returns `NO_GO` even with `--operator-attended`.

This is deliberately not a half-enabled F1 runner. No live path exists until
the external Python/ADB runtime qualification is generated and bound to a
`PASS_GO` capability review, the exact A90 preflight/final-health producer and
crash-prefix reconciler are implemented, and the resulting execution-critical
closure receives a fresh independent full review.

## The owner

`workspace/public/src/scripts/server-distro/a90_boot_only_f1_owner_v1.py`,
capability `A90_BOOT_ONLY_F1_OWNER_V1`.

It does exactly this and nothing else:

1. resolve exactly one A90 target, inventory attached devices, and report S22+
   and S20+ untouched;
2. fresh preflight: the actual resident version, build, and boot identity must
   equal the manifest's `expected_start`;
3. re-hash the candidate and rollback files **at execution time**, immediately
   before use;
4. require an empty durable journal, construct the exact live
   `approval-binding-v1`, and consume one fresh token for that binding;
5. `fsync` a `CANDIDATE_INTENT` record before any transfer;
6. transfer the candidate exactly once;
7. verify exact candidate version, build, self-test, and a bounded control
   response;
8. on failure, timeout, or ambiguity: prove the candidate helper process group
   and every descendant quiescent, then publish `ROLLBACK_INTENT`, launch the
   exact rollback helper behind a release gate, publish `ROLLBACK_LAUNCHED`,
   and release that helper exactly once;
9. publish the exact helper receipt as `ROLLBACK_RESULT`, or park an uncertain
   released rollback without reconstructing or replaying it; and
10. record the final health of whichever image is resident.

Removed relative to the per-candidate runners: rootfs staging, UFS inventory
and mount, Debian handoff, display, SSH, benchmark, observer, and every D1
path.

### Runtime rehash replaces delegated verification

The owner opens the private candidate and rollback files and hashes them itself,
immediately before use. That is the authoritative check.

This dissolves a problem that consumed two review rounds. Asking an independent
reviewer to verify private bytes contradicts the review contact contract, which
requires `workspace_private: 0`; delegating the check to tests then requires
binding a durable zero-skip receipt and the test source into the closure. Both
disappear when the executing owner does the hashing. No reviewer reads private
bytes, and no receipt needs binding, because the check happens where and when
it matters.

### File lifetime and post-helper revalidation

An immediate pre-use hash is not a lease. For the candidate, rollback, flash
helper, and every generated non-stdlib helper-closure member, the owner opens
the ordinary absolute path with `O_RDONLY|O_CLOEXEC|O_NOFOLLOW` before approval.
It rejects a missing, symlinked, non-regular, group/world-writable, or hardlinked
object, or an object not owned by the invoking host identity, and records one
`artifact-identity-v1` tuple:

`role, absolute path, st_dev, st_ino, st_mode, st_uid, st_gid, st_nlink=1,
exact size, SHA256`.

Every path ancestor below the configured artifact root and the containing
directory must be a real, non-symlink directory with a fixed `st_dev:st_ino`, be
owned by the invoking host identity, and not be group/world writable. Any
concurrent writer with that identity is outside this lane and is an immediate
stop. This explicit precondition closes the interval in which Python must open
the helper and its imports by ordinary path; the owner never turns an FD or
temporary alias into a transfer-tool pathname.

The owner keeps each opened FD until the corresponding helper has exited and
been reaped. A signal, timeout, or lost return first requires the exact helper
process group and every descendant quiescent; it does not skip the artifact
check. At approval, immediately before a candidate or rollback helper release,
and after every normal or abnormal helper exit, it:

1. `fstat`s the held FD and requires the exact recorded tuple;
2. hashes the complete held regular file from offset zero and requires the
   recorded size and SHA256; and
3. `lstat`s the ordinary pathname and requires the same regular-file
   `st_dev:st_ino`, mode, owner, link count, and size as the held FD.

The helper receives only that ordinary absolute candidate or rollback path plus
the exact expected size and SHA256. The reviewed `native_init_flash.py` then
independently opens it with `O_NOFOLLOW`, copies only those exact bytes to its
private mode-`0600` sealed image, verifies the sealed size and SHA256, and uses
only that sealed image for transfer. A pathname swap, truncation, content
change, inode replacement, symlink, hardlink, or helper/import drift therefore
cannot become an accepted transfer input.

The post-return checks happen before the owner interprets helper success,
publishes a transfer result, observes candidate health, or publishes a
terminal. Their exact tuples and pass/fail result are bound into the helper
result record. A mismatch before a device session is a host rejection. A
mismatch after `CANDIDATE_INTENT` consumes the candidate attempt and never
permits candidate replay. Candidate-source drift may enter the already bound
rollback path only when the rollback plus the complete helper closure still
pass fresh exact checks; rollback or helper-closure drift parks as
`RECOVERY_REQUIRED` without launching changed bytes. A mismatch after rollback
release likewise never permits another rollback.

After an owner crash, no vanished FD is reconstructed as proof. Recovery
reopens every still-needed path with the same flags and requires the complete
durable `artifact-identity-v1` tuple, directory identities, size, and SHA256
before observation or the already-authorized rollback path. A mismatch keeps
the candidate consumed and parks without candidate or rollback replay.

### Interpreter and transport executable identity

Source hashes do not identify the programs that interpret or transport those
sources. The owner capability therefore hardcodes exactly one ordinary
absolute `PYTHON_EXECUTABLE` path and one ordinary absolute `ADB_EXECUTABLE`
path. Neither path may come from the manifest, an approval, a CLI argument,
`PATH`, `PYTHONPATH`, `shutil.which`, `/usr/bin/env`, a shell, or another
runtime lookup. A bare or relative executable name is `NO_GO`.

Before approval, the owner opens both executable **canonical realpaths**, the fixed
`a90_boot_only_f1_helper_bootstrap.py`, and every helper source with
`O_RDONLY|O_CLOEXEC|O_NOFOLLOW`. Candidate, rollback, and repository source
objects retain the invoking-host-identity ownership rule. System executables
instead require one direct root-owned (`uid=gid=0`) regular file, link count
one, no group/world write bit, and a complete realpath ancestor chain that is
root-owned and not group/world writable. The current fixed paths are
`/usr/bin/python3.14` and `/usr/lib/android-sdk/platform-tools/adb`; the
symlink spellings `/usr/bin/python3` and `/usr/bin/adb` are rejected rather
than followed. The owner otherwise applies the same held-FD, size, digest, and
pathname-identity rules as `artifact-identity-v1`. It
records an `executable-identity-v1` tuple containing the complete artifact
identity plus the executable role, exact capability-qualified version-receipt
SHA256, and exact runtime-closure SHA256. These FDs remain held until the
helper process group and every descendant have exited and been reaped. The
owner repeats FD hash and pathname identity checks at approval, immediately
before each release, and after every normal or abnormal return. Crash recovery
reopens both absolute paths and requires the complete durable tuples; it never
reconstructs executable identity from a version string.

The Python trust boundary is explicit. `PYTHON_EXECUTABLE` is not considered
closed merely because its main executable bytes match. Capability
qualification generates and pins `python-runtime-closure-v1`: the interpreter
identity and implementation/version/cache-tag receipt, isolated-mode `-I`
launch contract, exact stdlib roots and `sys.path`, every imported stdlib or
extension-module file needed by the owner and generated helper import closure,
and their ELF interpreter/library dependencies where applicable. Likewise,
`adb-runtime-closure-v1` pins the ADB executable and its ELF
interpreter/library dependency closure. An unresolved file, user site,
environment-injected module, dynamic dependency outside the generated set, or
runtime-closure drift is `NO_GO`. The capability review signs both aggregate
digests; no claim treats an executable hash or version string as its complete
runtime.

Python `-I` deliberately removes the script directory from `sys.path`, so the
owner does not execute `native_init_flash.py` directly and does not re-add its
directory. It also does not ask Python to reopen the bootstrap pathname. The
owner passes its already validated bootstrap FD as the sole inherited FD to a
capability-bound `-c` loader, with `close_fds=True` and exact
`pass_fds=(bootstrap_fd,)`. That loader `fstat`s, rewinds, reads, size-checks,
and SHA256-checks the same inherited FD, closes it, and compiles only those
bytes. The bootstrap pathname is diagnostic metadata and the lexical anchor
for the downstream fixed source set; it is never opened by the loader. A
pathname swap and restoration therefore cannot select executed bootstrap
bytes, and direct pathname execution is rejected.

The fixed bootstrap runs under isolated safe-path mode and opens each exact
owner-bound downstream source once with `O_RDONLY|O_CLOEXEC|O_NOFOLLOW`. It
requires `fstat` regular-file type, link count one, exact size, and the
capability-bound SHA256; reads and compiles only the bytes from that same FD;
and installs only their fixed module names in `sys.modules`, in one fixed
dependency order. A pathname is never reopened after validation. It rejects a
preloaded local name, non-canonical bootstrap path, identity or digest mismatch,
source-directory `sys.path` entry, or any `sys.path` change. The generated
import inventory and source digests must equal that fixed table; a new
dependency or source byte requires a new owner capability review.

The sole helper launch vector is structurally fixed as
`[PYTHON_EXECUTABLE, -I, -c, FD_EXEC_PROGRAM, BOOTSTRAP_FD,
HELPER_BOOTSTRAP, BOOTSTRAP_SIZE, BOOTSTRAP_SHA256, fixed owner arguments,
--adb, ADB_EXECUTABLE]`, with `shell=False`, `close_fds=True`, the exact one-FD
`pass_fds` tuple, a fixed minimal environment, and no caller-supplied
executable or FD field. `FD_EXEC_PROGRAM` and its command builder are pinned in
`a90_boot_only_f1_fd_exec.py`; that file is part of the owner capability
closure, not a manifest input. Thus `native_init_flash.py` never uses its bare
`adb` default in this owner lane. A fake executable earlier in `PATH`, a
substituted bootstrap pathname, or an unreviewed Python file beside the helper
cannot affect the launch. The owner passes the same absolute ADB path to every
candidate, rollback, observation, and recovery helper invocation.

The approval binding and every launch/result record carry the exact
`pythonExecutableIdentity`, `pythonRuntimeClosureSha256`,
`adbExecutableIdentity`, and `adbRuntimeClosureSha256`. A path, inode, content,
version receipt, dependency, or aggregate mismatch before intent is a host
rejection. After candidate or rollback intent it follows the existing
consumed/no-replay branch and cannot authorize another dispatch.

### Execution closure

Deliberately small:

- `a90_boot_only_f1_owner_v1.py`;
- a small shared module for canonical JSON and the append-only journal;
- the generated exact non-stdlib import closure rooted at
  `workspace/public/src/scripts/revalidation/native_init_flash.py`;
- `a90_boot_only_f1_fd_exec.py`, containing the fixed inherited-FD loader and
  command builder used by the owner;
- `a90_boot_only_f1_helper_bootstrap.py`, whose fixed module order must equal
  that generated import closure;
- the generated `python-runtime-closure-v1` and `adb-runtime-closure-v1`;
- the manifest schema;
- the hostile state-machine tests.

The helper is not treated as a closed executable merely because its own bytes
are pinned. Its source imports `a90ctl`, which imports the observation parser
and serial lock, and those modules have further local imports. Before a
capability review, an AST walk recursively resolves every same-directory Python
import. A top-level import is admissible only when it is in Python's declared
stdlib set or resolves to an exact file in this generated closure. An unresolved
non-stdlib import, a local package, or a dynamic import is `NO_GO`; it is never
silently omitted.

The current generated closure is exactly:

| file under `workspace/public/src/scripts/revalidation/` | size | sha256 |
|---|---:|---|
| `a90_boot_only_f1_fd_exec.py` | 3,493 | `b55959a4362d459df0058a7b6bca7630a27978e0b1246868cb993ef1380abf57` |
| `a90_boot_only_f1_helper_bootstrap.py` | 4,767 | `26b98c3714ea5f8865cb552abb191fbbb6cb5eb3472ddfbb6a03bc308d8e9233` |
| `_workspace_bootstrap.py` | 1,255 | `7a8322f9760c8aa3672e094b01df0231fb5b0a85ceaeb5ad73042fcd3f3a6ffe` |
| `a90_observation_pipeline.py` | 24,478 | `6fa353b4e28ad26e76ec98d0e2c30089b493356fb314b36b962ce97e34a00adb` |
| `a90_serial_lock.py` | 2,860 | `663dd16f5121e35fc1047d563bdbe55148695224cf0c6ca5ab59c0433b6191c7` |
| `a90_transition_contract_v2.py` | 13,734 | `64e640dfb54d016f8e5548aea0da167e7f6917bf40c02fbc971773ef181b1c7e` |
| `a90ctl.py` | 16,380 | `4d72b87b42ef49c5997ddcd24d0c6bb4fe94766c2c7fddaa21b07ff218009f8c` |
| `native_init_flash.py` | 43,118 | `366dd38304625d37607916e92ea98a95271bbc4d9dfdc7eea106a5437b6dfe53` |

The canonical aggregate is SHA256 over the lexically sorted records
`relative-name NUL decimal-size NUL lowercase-sha256 LF`. Its current value is
`9907a2864988817a41f5133dd390a387c362fa81c1fff4dd81f4f100ca229f10`.
The capability review signs this generated aggregate, not a hand-maintained
subset. Any member-byte change, added or removed local dependency, unresolved
external dependency, or import-graph change expires the capability binding.

**The owner must not import `a90_v3403_f1_orchestrator.py`.** That would pull
~7,900 lines back into the closure. The per-candidate runners are stdlib-only
today and the owner keeps that property; it is a closure constraint, not a
style preference. This applies to the owner module itself; it does not erase the
invoked helper's generated transitive closure above.

## Manifest is data, never authority

The owner hardcodes, and the manifest cannot express:

- the `boot` partition as the only writable target;
- exactly one candidate attempt;
- exactly one rollback attempt;
- `--boot-block` and `--remote-image` at their defaults, so a caller-supplied
  path cannot widen the payload surface; and
- the Python interpreter or ADB transport path, version, or runtime closure.

A manifest cannot name a command, a partition, or a retry count. It carries:

| field | for H27 |
|---|---|
| `expected_start` | H24 `0.11.192` + build + boot identity |
| `candidate` | path, size, sha256, expected H27 `0.11.194` version/build |
| `rollback` | path, size, sha256, expected V2321 identity |
| `flash_helper` | size and sha256 |
| `timeouts` | bounded |
| `hazards` | hazard IDs with their qualification digests |
| `owner_closure_sha256` | the reviewed owner it may run under |

### The manifest must match the device, not only a healthy device

Preflight proves two separate things, and conflating them is how the H18
predecessor survived 32 bindings in the H27 runner:

- the device is healthy;
- the device **is the resident this manifest expects**.

An H27 manifest presented against any resident other than H24 `0.11.192` stops
before any effect.

## Approval is exact live authority

The manifest remains data. After fresh preflight, the owner constructs one
`approval-binding-v1` as canonical typed JSON. Its parser rejects duplicate
keys, unknown or missing fields, bool/integer substitution, non-canonical
numbers or strings, and any byte encoding other than the one exact schema. The
binding contains:

| field | bound value |
|---|---|
| target | exact target profile and live target evidence digest |
| boot/run | current boot ID, run ID, and journal namespace |
| manifest | manifest SHA256 |
| transfer bytes | candidate SHA256, rollback SHA256, and helper SHA256 |
| closure | owner closure SHA256 |
| implementation | helper version, exact Python/ADB executable identities and version receipts, and both runtime-closure SHA256 values |
| observation | observation timeout and acceptance rule |
| recovery | mandatory recovery plan |
| hazards | hazard IDs and qualification digests |
| freshness | expiry and nonce |

The private live-target evidence is created by the fresh preflight for this
physical A90 and current boot; the approval carries its digest, never the
private identifiers. The owner creates the run directory and empty journal
before approval, so the run ID and journal namespace already exist and cannot
be chosen after authorization.

The owner repeats target continuity, current boot, run/journal, artifact,
closure, implementation, observation, recovery, and hazard checks immediately
before `CANDIDATE_INTENT` and recomputes the binding bytes. The
operator-visible token derives from the whole approval-binding SHA256, not from
the manifest alone. A no-replace approval record is file- and directory-fsynced
and atomically consumed for that exact run before intent; reuse, expiry, a
foreign consumption marker, or any changed field stops before an effect.

`APPROVED`, `CANDIDATE_INTENT`, every rollback record, and every terminal carry
the same approval-binding SHA256. A terminal cannot substitute a later binding,
and a token for the same manifest on another A90, boot, run, or journal is
invalid even when its resident version and build happen to match.

## The success terminal is candidate-neutral

The reusable owner emits the target-contract terminal
`PASS_A90_RESIDENT_INSTALLED`; a candidate generation never appears in the
terminal name or in an owner-code constant. Candidate identity lives only in
one canonical typed `resident-install-terminal-v1` payload containing exactly:

| field | bound value |
|---|---|
| schema and terminal | `resident-install-terminal-v1` and `PASS_A90_RESIDENT_INSTALLED` |
| target/run | live target evidence SHA256, run ID, and journal namespace |
| candidate data | manifest SHA256 and the runtime-revalidated candidate SHA256 |
| expected identity | candidate version and build from the exact manifest |
| observed identity | post-transfer candidate version and build |
| reviewed execution | owner closure SHA256 and approval-binding SHA256 |
| observation | exact observation result and acceptance-rule digest |
| hazards | the exact manifest hazard IDs and qualification digests, each with `accepted: true` |
| health | exact `RESIDENT_HEALTHY` final-health receipt digest |

The producer uses the same duplicate-key rejecting, unknown/missing-field
rejecting, strict-type canonical JSON rules as `approval-binding-v1`. The
terminal record binds the SHA256 of those canonical payload bytes and is
published no-replace with file and directory `fsync`.

A consumer takes the exact manifest bytes as an input, recomputes their SHA256,
and requires the payload's manifest and candidate hashes, expected identity,
hazard set, owner closure, and approval binding to match that manifest and run.
It separately requires observed identity to equal expected identity, the
observation result to satisfy the bound acceptance rule, and final health to be
`RESIDENT_HEALTHY`. It never infers a candidate generation from the terminal
name. A candidate-specific terminal name, cross-manifest payload, changed
candidate hash, or expected/observed identity mismatch is invalid rather than
an alternate spelling of success.

Consequently H27 and H28 use identical owner bytes, schema, and terminal name
while their manifest, candidate, version/build, hazard, and canonical payload
digests remain distinct. Adding H28 data cannot alter the owner closure.

## Hazard binding

A boolean in data that nothing enforces is decoration. This session produced
that mistake twice — an empty invariant tuple that read as "nothing required",
and an `experiment_proof` field no consumer validated — so the hazard is bound
at three points:

1. a reviewed hazard-qualification artifact exists for
   `RKP_CFP_DISABLED_RESIDENT`, and the manifest binds it by digest;
2. its ID and qualification digest appear inside the complete approval binding,
   so approval cannot be given without the hazard in view;
3. the terminal records the same hazard ID with `accepted: true`, so what was
   accepted stays durable after the run.

An unknown or unqualified hazard ID stops the owner before any effect.

`RKP_CFP_DISABLED_RESIDENT` is the operator's 2026-08-17 decision to accept a
reduced kernel exploit-mitigation posture for as long as the self-built kernel
is resident, rather than proving the boot and returning to V2321.

## Rollback is a separate one-shot transaction

`CANDIDATE_INTENT` does not account for a later rollback dispatch. Before the
owner can prepare rollback, it proves the candidate helper process group and
every descendant quiescent. It then publishes each rollback transition as a
separate no-replace journal record with file and directory `fsync`:

1. `ROLLBACK_INTENT` binds the exact target identity, run ID, rollback SHA256,
   helper SHA256, transport generation, and attempt `1`. If this intent exists
   without `ROLLBACK_LAUNCHED`, a restart may resume only the same bound
   rollback. It cannot substitute bytes, target, helper, transport generation,
   run, or attempt.
2. The owner starts that helper in its own process group behind a one-byte
   release gate. Before releasing it, `ROLLBACK_LAUNCHED` binds the exact
   process-group identity, release-gate identity, log identity, and all fields
   from `ROLLBACK_INTENT`. `ROLLBACK_LAUNCHED` is the one-shot consumption
   point. The child cannot exec the flash helper or open the transport until it
   reads the exact release byte; EOF or any byte other than the exact release
   byte makes it exit without the helper. After the launched record is durable,
   the parent performs one release write. From then on a restart may reconcile
   only that process group, gate, and log; it must never start a second helper.
3. One complete helper return and transport receipt may publish
   `ROLLBACK_RESULT`. It binds the same identities, the exact return class,
   transfer/session evidence, output digests, and whether release was proved.
   `ROLLBACK_RESULT` never reconstructs a missing helper return and final
   resident health never substitutes for transfer provenance.

An intent-only prefix may still launch its same bound attempt because no launch
or release is proven. A launched prefix with no complete result permits
observation and health reconciliation only. A lost helper return, torn or
missing result, uncertain release, missing process/log evidence, or identity
mismatch becomes `ROLLBACK_RELEASE_UNCERTAIN`; it never admits another helper
or rollback transfer and closes only as `RECOVERY_REQUIRED`. Even an apparently
healthy V2321 resident cannot relabel that transfer as completed.

## States

```text
PREPARED
  -> APPROVED
  -> CANDIDATE_INTENT
       -> PASS_A90_RESIDENT_INSTALLED
       -> ROLLBACK_INTENT
            -> ROLLBACK_LAUNCHED
                 -> ROLLBACK_RESULT
                      -> NO_PROOF_ROLLED_BACK
                      -> RECOVERY_REQUIRED
                 -> ROLLBACK_RELEASE_UNCERTAIN
                      -> RECOVERY_REQUIRED
```

- `PASS_A90_RESIDENT_INSTALLED` — the candidate-neutral record type whose exact
  payload proves the manifest-bound candidate identity and health.
- `NO_PROOF_ROLLED_BACK` — boot failure, timeout, observation failure, or
  ambiguity, followed by one complete bound rollback result and verified V2321
  health.
- `RECOVERY_REQUIRED` — rollback health could not be verified, or rollback was
  released but its exact result or provenance is uncertain.

There is no `REFUTED`. Two review rounds went into its semantics and the
attribution receipt it would need, for a terminal this question does not
require. Cause analysis happens afterwards, as a separate H0 over the private
logs; an F1 terminal does not adjudicate why a kernel failed to boot.

## Retiring the per-candidate runners

Leaving them live would recreate the namespace collisions already seen. They
remain as historical recovery evidence and must not execute a new candidate:

```
a90_h15_ufs_f1_runner_v1.py   a90_h15_ufs_d1_runner_v1.py
a90_h16_ufs_f1_runner_v1.py   a90_h16_ufs_d1_runner_v1.py
a90_h17_ufs_f1_runner_v1.py   a90_h17_ufs_d1_runner_v1.py
a90_h18_ufs_f1_runner_v1.py   a90_h18_ufs_d1_runner_v1.py
a90_h24_ufs_f1_runner_v1.py   a90_h24_ufs_d1_runner_v1.py
a90_h27_ufs_f1_runner_v1.py
```

- a new manifest is consumable only by `A90_BOOT_ONLY_F1_OWNER_V1`;
- their approval prefixes (`A90-H15-F1-APPROVE:` … `A90-H27-F1-APPROVE:`) and
  journal namespaces (`h15-f1-live` … `h27-f1-live`) are forbidden to the owner;
- new run directories are keyed by owner version, manifest digest, and run ID,
  so no two runs can share a journal.

The H27 runner is retired before ever executing. Its candidate, builder version
`phase3-minimal-h27`, digests, and the kernel build behind them are unaffected
and carry forward.

## Hostile corpus

The owner is only as good as what it refuses. At minimum:

- manifest naming a non-`boot` partition, an extra partition, or a command;
- manifest asking for more than one candidate or rollback attempt;
- manifest presented against a resident other than `expected_start`;
- candidate or rollback whose runtime hash differs from the manifest;
- absent, symlinked, or non-regular candidate, rollback, or helper;
- hardlinked, group/world-writable, or wrong-owner artifact or containing
  directory;
- pathname `st_dev:st_ino` different from the held FD before release;
- candidate, rollback, helper, or helper-import size/SHA256 drift while the
  helper runs or after it returns;
- candidate artifact restored after a transient different-byte substitution —
  the helper's independently verified sealed copy must still match the bound
  size and SHA256;
- flash helper whose hash differs from the pinned value;
- approval token that does not derive from the complete approval-binding
  SHA256;
- approval token missing the hazard ID, or naming an unqualified hazard;
- approval from another A90 with the same resident;
- approval from an earlier boot ID;
- approval from another run or journal namespace;
- changed observation rule or recovery plan after approval;
- changed owner closure, helper, Python/ADB executable identity, version
  receipt, or runtime closure after approval;
- bare or relative Python/ADB executable, either canonical path replaced by a
  symlink, caller-selected `--adb`, PATH lookup,
  fake ADB earlier in `PATH`, direct `python -I native_init_flash.py`, direct
  bootstrap pathname execution, or a launch omitting the fixed inherited-FD
  loader, its one-FD `pass_fds` binding, or isolated Python mode;
- bootstrap pathname swap before Python startup, swap-execute-restore, wrong
  inherited descriptor/type/link-count/size/digest, extra inherited FD, or
  loader argument supplied by a caller/manifest;
- bootstrap source directory added to `sys.path`, preloaded local module,
  reordered/missing/extra local dependency, or source outside the exact held
  helper closure;
- source pathname swapped between validation and read, initial symlink,
  wrong-size/digest source, short read, or trailing source bytes;
- same Python/ADB version string with different executable bytes, inode,
  dependency, stdlib/extension module, or runtime-closure digest;
- reused or expired approval;
- non-empty journal at start;
- crash after `CANDIDATE_INTENT` and before result — must resume without
  candidate replay;
- candidate retry attempted after a failure;
- post-candidate artifact drift followed by candidate retry;
- rollback or helper-closure drift followed by rollback launch;
- rollback attempted before candidate intent;
- crash before `ROLLBACK_INTENT` — no rollback helper or effect exists;
- crash after `ROLLBACK_INTENT` and before `ROLLBACK_LAUNCHED` — only the same
  bound rollback may proceed;
- crash after `ROLLBACK_LAUNCHED` and before release — reconcile only the bound
  process group, gate, and log; never start another helper;
- lost helper return after rollback dispatch — observation and recovery only,
  with no rollback replay and no completed-transfer inference;
- crash while publishing `ROLLBACK_RESULT` — only a complete no-replace record
  with file and directory `fsync` is recognized;
- duplicate or mismatched rollback intent or result, wrong process group,
  wrong release gate, wrong log, or wrong transport generation;
- candidate-specific success terminal name instead of
  `PASS_A90_RESIDENT_INSTALLED`;
- terminal payload from another manifest or carrying another candidate SHA256;
- expected and observed candidate version/build mismatch;
- terminal missing the hazard acceptance record;
- run directory colliding with a retired runner's namespace.

## What this design does not do

- It does not provide a live-capable owner. The H0 contract/state-machine core
  exists, but production target preflight, final observation, runtime
  qualification, and crash-prefix resume remain deliberately absent and the
  live CLI is hard-disabled.
- It does not qualify anything, and creates no approval, manifest, or hazard
  qualification.
- It does not authorize an F1. `GOAL_A90.md` still records that no successor
  candidate, transfer, or reboot is authorized.
- It does not claim the H27 candidate is correct; that stands or falls on its
  own build evidence.
- It does not remove the one-time cost. The owner needs a full capability
  review before first use. The saving is that H28 and later pay manifest and
  hazard review only.

## Sources

- `AGENTS.md`
- `docs/operations/targets/A90_TARGET_CONTRACT.md`
- `docs/operations/DEVICE_ACTION_PROCESS_V2.md`
- `GOAL_A90.md`
- `docs/plans/A90_SELF_BUILT_KERNEL_F1_DESIGN_2026-08-16.md`
- `docs/reports/A90_SELF_BUILT_KERNEL_H0_2026-08-16.md`
- `workspace/public/src/scripts/revalidation/native_init_flash.py`

## Boundary

Produced host-only from repository documents. Device, `/dev`, USB, network,
S22+, and S20+ contacts are zero. No ordinal, identity, candidate,
qualification, approval, manifest, or command is created, and no D0, D1, or F1
authority is granted or implied.
