# S22+ FYG8 candidate build qualification runbook

This runbook defines the reusable H0 sequence for qualifying a final FYG8
native-init candidate. It composes the existing checked build, candidate, and
Process v2 tools. It does not replace their source contracts or weaken their
fail-closed checks.

This is not the implementation-loop default. Use focused tests and
development-only thin/no-LTO builds while changing code. Run this clean
Full-LTO sequence only after the candidate source contract and userspace have
been frozen.

## Choose the build lane first

Do not start a build until the change is classified. The lane decision is part
of the build record.

| Change | Required work | Full-LTO A/B rebuild |
|---|---|---|
| Kernel source, candidate patch, kernel config, pinned compiler, build environment, reproducibility controls, or canonical source path | Freeze a new candidate identity, then run this whole qualification | Yes |
| Kernel source contract changes what bytes or config the candidate must contain | Derive a new intent and patch, then run this whole qualification | Yes |
| Linked-audit implementation changes while the frozen kernel contract and bundles remain unchanged | Re-run the changed audit against both immutable bundles, its negative tests, independent closure, and downstream promotion | No |
| Host decoder, evidence verifier, Process v2 parser, or report changes without changing the kernel/source contract | Run focused and historical compatibility tests, then re-run only the affected downstream host checks | No |
| Native userspace or ramdisk content changes without a kernel change | Rebuild the affected userspace, package twice, and repeat static closure and promotion | No kernel rebuild |
| Candidate packager changes without changing kernel or userspace inputs | Package twice and repeat package/static/promotion checks | No kernel rebuild |
| Documentation only | Validate the documentation diff | No |

When the answer is not clear, compare the exact frozen kernel inputs and the
six immutable build artifacts before deciding. A later host-only verifier
failure does not retroactively invalidate a successful kernel build. P2.55 is
the reference case: its typed-evidence verifier fix required tests and
downstream host validation, but no P2.54 kernel rebuild.

Do not confuse a versioned contract's generated **base/template kernel patch**
with the final candidate patch. Candidate intent derives the run ID and
UNSAT tag from the selected source-contract ID and its bound source receipts,
then adds both values to kernel config. Therefore:

```text
template patch byte-identical
    does not imply
final candidate patch or Image byte-identical
```

After any source-contract ID or identity-input change, derive the fresh intent
before choosing the build lane. Compare its exact final patch, config lines,
and run ID with the qualified candidate. If any differ, the existing Image
cannot satisfy the new candidate contract and clean Full-LTO A/B builds are
required. This decision must be covered by a focused test; prose comparison of
the template patches is not sufficient.

The candidate wrapper is deliberately a Full-LTO qualification tool. Do not
add a convenience no-LTO switch to it. Development builds, focused static
cross-compiles, and unit tests are non-promotable evidence and must use
separate output directories.

## Scope

- Tier: H0 host-only.
- Outputs: two clean kernel bundles, one reproducibility result, two
  deterministic boot-only packages, one independent static result, and one
  offline Process v2 promotion.
- No device connection, Odin session, manifest binding, approval, or live
  authority is created.
- All firmware, kernel outputs, images, tool logs, and receipts stay under
  `workspace/private/`.

## Fixed prerequisites

Require all of the following before spending a Full-LTO build:

- one source-matched FYG8 source contract with a frozen intent and patch;
- focused implementation, decoder, mutation, and static-link tests passing;
- one canonical absolute repository and source-tree path used for both builds;
- the pinned AOSP clang `r416183b` toolchain;
- a nominal 32 GiB build host, with at least 30 GiB visible physical memory;
- at least 8 GiB swap and 30 GiB free disk;
- the pinned stock baseline and both source archives;
- either GNU AArch64 `nm`/`objdump` on the build host, or a named controlled
  verification host that has them, decided before build A;
- the CPU frequency lane recorded below, including the privilege to apply a
  frequency cap when that lane is selected;
- no existing `$SOURCE_TREE/out` tree and a new result directory; and
- no source, intent, patch, adapter, dispatcher, or candidate-enforcement
  change after intent derivation.
- the exact two-link userspace build has passed its source-contract-specific
  stock-closure entrypoint check before kernel build A.
- when the selected runtime changes generic configfs/libcomposite/gadget-serial
  behavior covered by a checked QEMU harness, its exact non-overlay execution
  verdict has passed before kernel build A.

The exact resource and provenance predicates are owned by the build wrapper.
Do not bypass a failed preflight based on a manual estimate.

The userspace/closure check is deliberately before Full LTO. An executable
entrypoint is a linked-output property and may move when a versioned runtime
changes even if file size and the kernel template patch do not. A contract
must not inherit a previous runtime's numeric entrypoint without rebuilding
the current exact userspace and comparing both `init` and child ELF metadata.
If this check fails, fix the source-bound closure adapter, derive a new intent,
and repeat the cheap userspace check before starting either kernel build.

### Generic userspace execution gate

For P2.60-style E3 changes, run the checked generic-arm64 QEMU harness before
Full LTO. It includes the exact candidate runtime and uses real configfs,
libcomposite, dummy-hcd, gadget serial, `ttyGS0`, and host-side `ttyACM0`.
Only the exact verdict is qualification evidence. Temporary syscall or
readback overlays may localize a defect, but they are forensic evidence only
and must never qualify a candidate.

This gate proves the generic runtime sequence and catches dynamic ordering,
value, symlink, queueing, and error-path mistakes that token/static checks
cannot. It does not emulate or prove Qualcomm DWC3-MSM, SS/HS/eUSB2 PHY,
peripheral-role control, VBUS/Type-C, Samsung notifier behavior, or physical
host enumeration. Those remain target-specific F1 evidence.

## Build record before preflight

Create one private run directory and record these values before build A:

```text
candidate run ID
source contract ID and verdict
intent path, size, and SHA256
patch path, size, and SHA256
canonical source-tree realpath
pinned clang repository and commit
jobs
physical RAM, swap total, and free disk
GNU AArch64 nm/objdump availability and the selected audit host
CPU frequency lane
build A/B result and immutable-bundle paths
tmux session names
```

The wrapper result remains authoritative; this record is an operator index,
not a second source of truth. Paths must stay under `workspace/private/` and
must not include credentials or target identifiers.

Use one Full-LTO process at a time on the qualified 32 GiB host. Do not overlap
a build with another kernel link or the linked proof audit. The observed build
peak is close enough to host capacity that concurrency can turn a healthy run
into swap pressure or an OOM failure.

`ccache` may be used for explicitly non-promotable development compiles. Do
not inject it into the final qualification environment: the wrapper constructs
a hermetic `PATH` and does not qualify a ccache wrapper. Qualification builds
A and B must both use the wrapper's pinned environment.

## 1. Preflight

Run the candidate build wrapper in `preflight` mode with explicit paths:

```bash
PYTHONPYCACHEPREFIX=/tmp/android_native_init_pycache \
python3 workspace/public/src/scripts/revalidation/s22plus_fyg8_p234_build.py \
  --mode preflight --jobs 8 \
  --work-tree "$SOURCE_TREE" \
  --clang-repo "$CLANG_REPO" \
  --result-dir "$RUN_ROOT/preflight-a" \
  --stock-baseline "$STOCK_BASELINE" \
  --intent "$RUN_ROOT/intent/candidate-intent.json" \
  --patch "$RUN_ROOT/intent/candidate.patch"
```

Require:

- `build_allowed=true`;
- the exact intended run ID;
- source-overlay, symlink, timestamp, KMI-path, kernel-debug, and VDSO controls
  all verified;
- clean-output precondition verified; and
- all resource gates verified.

## 2. Clean build A

Run the same wrapper in `build` mode from a detached session. Capture
`/usr/bin/time -v`, stdout, stderr, and the shell exit code outside the result
directory. The result directory itself must be new.

Do not hand-nest several shell quote layers around the completion hook. Build
the argument vector first, encode it exactly once, and give `tmux` one
shell-quoted command. The following launcher has been checked to retain a
failing exit status:

```python
import shlex
import subprocess
from pathlib import Path

session = "fyg8-candidate-a"
build_wrapper = Path(
    "workspace/public/src/scripts/revalidation/s22plus_fyg8_p234_build.py"
)
time_file = Path("/absolute/private/run/build-a.time")
stdout_file = Path("/absolute/private/run/build-a.stdout")
stderr_file = Path("/absolute/private/run/build-a.stderr")
rc_file = Path("/absolute/private/run/build-a.rc")
build_argv = [
    "python3",
    str(build_wrapper),
    "--mode",
    "build",
    # Append the same explicit arguments that passed preflight.
]
timed_argv = ["/usr/bin/time", "-v", "-o", str(time_file), *build_argv]
command = (
    "set +e; "
    + shlex.join(timed_argv)
    + f" >{shlex.quote(str(stdout_file))}"
    + f" 2>{shlex.quote(str(stderr_file))}; "
    + 'rc=$?; printf \'%s\\n\' "$rc"'
    + f" >{shlex.quote(str(rc_file))}"
)
wrapped = "exec /bin/bash -lc " + shlex.quote(command)
subprocess.run(
    ["tmux", "new-session", "-d", "-s", session, wrapped],
    check=True,
)
```

An empty, malformed, or literal `$?` completion file is a hook failure. It
does not override an otherwise authoritative wrapper result, but it must be
recorded and fixed before the next build.

The detached session may be quiet for long periods during Full LTO. Observe it
with read-only commands only:

```bash
tmux has-session -t "$SESSION"
tmux capture-pane -p -t "$SESSION" -S -80
ps -eo pid,ppid,etimes,rss,stat,comm,args
```

Do not start a replacement build merely because stdout is quiet. Completion is
decided by the wrapper result, its build/provider return codes, the completion
file, and `/usr/bin/time -v`. If those disagree, preserve all records and stop
for host-side triage.

Build A is accepted only when:

- the shell exit code and both result return codes are zero;
- `p234_build_pass=true`;
- the exact run ID is present;
- the output gate is verified;
- stderr is empty or contains only explicitly reviewed non-fatal output;
- the source tree is restored to its pre-build hashes; and
- the wrapper reports no device contact, write, Odin, or live authority.

Copy only the six reproducibility artifacts plus `result.json` into a private
immutable A bundle:

```text
Image
vmlinux
.config
System.map
vmlinux.symvers
abi.xml
build-result.json
```

Verify every copied file against the size and SHA256 recorded in
`result.json` before deleting generated output.

Do not delete `$SOURCE_TREE/out` until the immutable bundle copy and hash
verification have both passed. A missing bundle artifact after deleting that
tree requires a new clean build; a post-build audit or packaging failure does
not. A repository-root `out/` is unrelated and must not be used as the
clean-build predicate.

## 3. Clean build B

Resolve both paths before cleanup and require the generated tree's parent to
be the canonical source tree:

```bash
source_real=$(realpath -e -- "$SOURCE_TREE")
output_real=$(realpath -e -- "$SOURCE_TREE/out")
test "$(dirname -- "$output_real")" = "$source_real"
rm -rf --one-file-system -- "$output_real"
test ! -e "$SOURCE_TREE/out"
```

Remove only that generated `$SOURCE_TREE/out`. Keep the A bundle and all
receipts. If the exact tree is already absent, do not substitute another
`out/` path.

Run a fresh B preflight. It must independently prove the same run ID,
canonical source path, source-overlay identity, symlink controls, clean output,
and resource gates.

Run build B with the same wrapper arguments and canonical absolute paths.
Never build B from a renamed source tree: source paths and the GNU build ID can
change linked bytes even when source content is identical.

Bundle B exactly as A and require byte equality for all six reproducibility
artifacts. A near match, matching `Image` only, or matching source hashes is
not sufficient.

## 4. Linked proof audit

Run the versioned linked-audit adapter selected by the exact source contract.
The audit must consume both build bundles and prove the contract-specific
tables and control flow in final Full-LTO `vmlinux`.

For P2.54 this includes:

- exact item, classifier-stage, and classifier-detail table bytes;
- exact table-base and load-width dataflow;
- writer-to-request-validator and request-validator-to-subvalidator calls;
- validator success guarding the retained head, all retained flushes, and all
  retained stores;
- the failure edge not rejoining a retained write; and
- a negative failure return.

GNU AArch64 binutils are the default audit tools. If the build host instead
has no `/usr/bin/aarch64-linux-gnu-nm` and
`/usr/bin/aarch64-linux-gnu-objdump`, transfer the two private bundles to a
controlled verification host that has them. The linked audit is memory-heavy
enough that it must run only after the Full-LTO build process has ended.

Do not silently substitute the pinned LLVM `nm`/`objdump` pair. The FYG8
builder lacks their default `libc++.so.1` search path, and a qualified P2.54
trial with the library path supplied expanded range-disassembly processing to
more than 24 GiB RSS without completing in 25 minutes. The GNU tools completed
the same versioned audit in seconds. Treat a future LLVM qualification as a
separate H0 tool-compatibility unit.

Supplying `LD_LIBRARY_PATH` is not an approved substitution. It only makes the
unqualified tool load, after which the documented range-disassembly cost
returns. When the build host has no GNU AArch64 binutils, the prescribed
recovery is the verification host above, not a library-path workaround.

Do not accept a generic linked audit when the source contract requires the
versioned adapter.

## 5. Deterministic boot-only packaging

Use the checked candidate builder twice with separate new output directories
and the exact reproducibility result. Both packages must contain exactly one
regular member named `boot.img.lz4`.

The builder's Odin AP is under `odin4/AP.tar.md5` inside each candidate output
directory. Pass that exact nested path to offline Process v2 promotion; there
is no AP at the candidate directory root.

Require byte equality for:

- `boot.img`;
- `boot.img.lz4`; and
- `AP.tar.md5`.

Host build-system `boot.img`, `dtbo.img`, `vendor_boot.img`, `vendor_dlkm.img`,
or `super.img` outputs are not the candidate and are never promoted by this
runbook.

## 6. Independent closure and offline promotion

Run the independent candidate static checker against both packages, the two
kernel build bundles, exact userspace, base boot, vendor ramdisk/vendor boot,
source contract, intent, and patch.

Require:

- exact kernel and userspace receipts;
- effective stock-rootfs and module closure;
- exact executable entrypoints;
- deterministic boot-only AP structure;
- the versioned linked-audit adapter result; and
- no forbidden authority or partition signal.

Only then run the Process v2 offline promotion. Offline promotion still creates
no D0/F1 binding or authority.

## Interrupted-build recovery

An interrupted wrapper can leave temporary reproducibility-control edits in
the source tree. Never infer that only the candidate patch needs restoration.
The affected set can include `_setup_env.sh`, `build.sh`, the common kernel
`Makefile`, and both VDSO Makefiles.

Run preflight again and use its source-overlay mismatch list. Restore only the
listed regular files from the pinned base/delta archive that owns their final
content. Before replacement, prove the extracted bytes equal the reconstructed
final-members manifest. Then rerun preflight from a new result directory.

Do not continue from partial `$SOURCE_TREE/out`, manually edit read-only
archive files, or reuse a failed result directory.

## Failure triage before rebuilding

Classify a failure by the earliest authoritative boundary:

1. **Preflight/source failure:** no build is valid. Repair the named host input,
   use a new result directory, and rerun preflight.
2. **Compile/link/provider failure:** preserve logs and partial receipts,
   restore the source tree, remove only generated `$SOURCE_TREE/out`, and run
   a new clean build after the cause is fixed.
3. **Bundle-copy/hash failure:** the completed wrapper result may still be
   valid, but do not delete `$SOURCE_TREE/out`. Repair the copy step and verify
   again.
4. **Reproducibility mismatch:** both builds are evidence, not a candidate.
   Compare canonical paths, toolchain/environment, source identities, and all
   six artifact hashes before rebuilding.
5. **Linked-audit/tool failure:** keep both immutable bundles. Fix or move the
   host audit and rerun it; do not rebuild unless a frozen kernel input changed.
6. **Userspace/package/static/promotion failure:** keep qualified kernel
   bundles. Re-run only the affected downstream stage unless its input bytes
   changed.
7. **Reporting/parser failure after a proven host stage:** do not repeat the
   proven stage. Repair the consumer and resume from its immutable input.

Every incident record should state the stage, symptom, authoritative evidence,
whether frozen kernel inputs changed, whether a rebuild is required, the
bounded recovery, and the recurrence control. “Try the whole build again” is
not an acceptable recovery without a compile/link or input-identity reason.

## Observed failures and recurrence controls

These are host incidents already encountered by the FYG8 build line. They are
not hypothetical policy requirements.

| Symptom | Correct interpretation | Recovery | Recurrence control |
|---|---|---|---|
| Preflight reported five source-overlay mismatches after an interrupted build | The old wrapper stopped after editing reproducibility controls | Restore only `_setup_env.sh`, `build.sh`, the common `Makefile`, and the two VDSO Makefiles named by preflight from the hash-verified pinned archive; discard partial `$SOURCE_TREE/out` | Never start Full LTO until a fresh preflight reports zero overlay mismatch; verify post-build source restoration |
| Detached-build completion file contained literal `$?` or was empty | The shell hook was quoted incorrectly; it did not by itself invalidate a complete wrapper result | Judge the finished build from the wrapper result, its two return codes, and `/usr/bin/time`; repair the hook before another build | Use the single-encoding Python launcher above and reject malformed completion files |
| Build host lacked GNU AArch64 `nm`/`objdump`; LLVM substitution consumed over 24 GiB for more than 25 minutes | The versioned audit is qualified against GNU binutils, not that LLVM range-disassembly behavior | Stop the non-authoritative LLVM run and audit the copied immutable bundles on a controlled GNU-binutils host | Check GNU tools before build or reserve a verification host; do not select tools by basename fallback |
| Offline promotion was given `candidate-a/AP.tar.md5` | Candidate generation succeeded, but the caller used the wrong path | Re-run only the host promotion with `candidate-a/odin4/AP.tar.md5`; do not rebuild or repackage | Treat `odin4/AP.tar.md5` as the candidate-builder output contract and verify it before promotion |
| A clean build used a different absolute source-tree name | Source path and build-ID inputs changed, so linked bytes differed despite equivalent sources | Re-run B from the same canonical path after a clean preflight | Pin one canonical absolute source path in both build invocations |
| A new source contract added a reachable-record field that the generic evidence verifier did not recognize | Kernel, userspace, packages, and static closure were already valid; the downstream verifier had a stale hard-coded shape | Fix the typed verifier, run focused plus historical compatibility tests, and re-run host-ready validation | Derive the expected record from the selected versioned source contract; use the lane table and do not rebuild qualified kernel bundles |
| Full-LTO build output was quiet for an extended period | Full LTO can spend a long time in a link with little stdout; silence alone is not a failure | Inspect the detached session and process/resource state read-only; wait for authoritative completion records | Always launch with tmux, `/usr/bin/time -v`, and a validated completion hook; never start a duplicate build from silence |
| An SSH-inline nested shell expanded `rc=$?` and `"$rc"` before tmux started | The build had a malformed completion hook even though the visible command looked correct | Stop an immediately detected host-only attempt, preserve its launcher receipt, remove only partial generated `$SOURCE_TREE/out`, and rerun fresh preflight | Copy or generate the reviewed Python `shlex.join()` launcher on the build host; inspect the running `/proc/<pid>/cmdline` and require literal `rc=$?` plus `"$rc"` before allowing the long build to continue |
| Build B preflight twice reported `clean build requires absent output tree: <canonical-source>/out` after a repository-root `out/` was removed | The operator cleaned the wrong path; Build A correctly writes under `$SOURCE_TREE/out`, and the wrapper's fail-closed clean gate prevented a non-clean B | Stop after the second identical rejection, preserve the empty failed result directories, verify Build A's immutable bundle, then remove only the exact canonical `$SOURCE_TREE/out` in a new H0 recovery unit | Spell every cleanup/check as `$SOURCE_TREE/out`, verify `dirname(realpath($SOURCE_TREE/out)) == realpath($SOURCE_TREE)` before deletion, and never use repository-root `out/` as evidence |
| A monitor used `tmux has-session -t build-name`, then outlived the build because its own `build-name-monitor` session prefix matched | `tmux -t` accepts unique prefixes; the monitor was observing itself, not a running build | Stop only the monitor after the build result and time receipt are complete; preserve all build artifacts | Compare exact names from `tmux list-sessions -F '#{session_name}'`; never use prefix matching as a completion predicate |
| A 4.4 GHz Full-LTO link burst reached 69.1 C while the host critical point was 70 C | The overclocked P-state has insufficient sustained thermal margin even under a mostly single-thread link | Return to the stable 2.9 GHz cap, finish the build, and restore the normal governor afterward | Select and record a CPU frequency lane; never pin a high P-state manually unless cooling or an intermediate P-state is separately qualified |
| A new source contract had a byte-identical template patch, so an earlier Image was selected for reuse | Candidate identity also binds the source-contract domain, source receipts, derived run ID, UNSAT tag, and final config patch; template equality is below the actual candidate boundary | Derive and verify the fresh intent first; compare final patch/config/run ID, and rebuild when they differ | Keep a focused cross-contract identity test and make fresh intent derivation precede every build-lane decision |
| P2.58A userspace linked reproducibly, but the stock-closure adapter inherited P2.57's older `/init` entrypoint and rejected the packaged candidate only after two Full-LTO builds | The kernel and packages were reproducible, but a source-bound host proof adapter was stale; a downstream-only shim would split static, promotion, and evidence semantics | Fix the P2.58A adapter itself, derive a new intent because its source receipt changes, and rebuild the invalidated candidate | Before Full LTO, build the exact userspace twice and compare both ELF entrypoints with the selected stock-closure adapter; test scoped adapter state restoration and historical-contract isolation |
| A new E2 runtime intentionally wrote bounded sysfs/configfs state, but the generic package metadata still claimed `no_userspace_sysfs_or_configfs_write=true` | Candidate safety was selected only by broad profile and duplicated in builder and checker, so a reproducible package could carry a false authority statement | Stop before packaging, move safety selection to one exact-source-contract function, make the checker consume it, source-receipt that selector, and derive a fresh intent | Before Full LTO, evaluate the exact candidate contract's generated safety dictionary and mutation-test both the new bounded authority and unchanged historical profile behavior |
| P2.60 reached configfs stage `0x88` and failed because `P260_CONFIGFS_MAGIC` used sysfs magic `0x62656572` instead of configfs magic `0x62656570` | The source contract SHA-pinned the runtime and checked that the operation existed, but never compared the external semantic constant with its authoritative kernel definition | Correct the constant, invalidate the source receipt, and stop before Full LTO unless the versioned source contract parses and verifies the exact value | Register every load-bearing external literal in the selected source contract and mutation-test a plausible sibling value; byte identity and token presence are not semantic validation |
| P2.69 passed static and Full-LTO qualification, but exact QEMU gadget creation failed with `ENOENT`; an absolute target then exposed a second readback mismatch | Configfs resolves a symlink target through `kern_path()` from the process working directory and returns a canonical configfs-relative readlink. The candidate assumed ordinary link-relative creation plus a shorter readback target | Retire the frozen candidate before D0, separate absolute creation and canonical readback values, source-bind both, and derive a new intent | Run exact generic configfs/ACM QEMU execution before Full LTO for covered runtimes; authoritative string checks and mutation tests remain required, while diagnostic overlays never qualify |
| P2.60 Process v2 promotion emitted terminal `0x8f` although its selected decoder defines `0x90` | Two downstream consumers read the shared legacy E2 model's profile terminal instead of the selected versioned decoder terminal; the already-qualified kernel and package bytes were unaffected | Quarantine only the stale promotion/ready outputs, preserve immutable A/B bundles and AP, fix the host consumers, run legacy plus versioned compatibility tests, then re-promote the same AP | Resolve terminal stage through one version-aware selector: selected decoder terminal first, legacy profile fallback only when no versioned terminal exists; require legacy E2=`0x8f`, P2.60=`0x90`, and reject a stale P2.60 `0x8f` mutation |
| Remote preflight failed after only the intent JSON and patch were copied | The intent contract also owns its complete `materialized-sources/` tree; transferring two visible files produced an incomplete candidate input without starting a build | Preserve the failed preflight, copy the complete immutable intent directory, and rerun only preflight in a new result directory | Transfer and rehash the complete intent directory as one unit; never reconstruct its required members from a hand-written file list |
| A long shell invocation was submitted twice and the second package/static helper collided with an already-complete output | Output paths were exclusive, so the duplicate stopped safely, but command submission was not serialized and made a valid first result look ambiguous | Do not regenerate; validate the existing result, all receipts, and byte equality, then retain the first complete output | Wrap each output-producing post-build helper in a nonblocking `flock`, use a unique output directory, and treat an existing output as read-only evidence to validate rather than overwrite |
| The independent closure rejected a P2.70 candidate for an absolute-path authority mismatch, missing one expected string that a compiler had incidentally emitted into the earlier binary | The candidate contained no new forbidden path. The adapter asserted exact-set equality over a set that also held incidental link artifacts, so a benign code-layout change failed it | Split the assertion into required, optional, and forbidden sets; because the adapter is source-bound, derive a new intent and rebuild the invalidated candidate | Never assert set or count equality over values that are not invariants, such as compiler-emitted strings, unrelated sibling devices, or inherited numeric addresses. Assert required membership, permit unrelated members, and reject only registered-forbidden ones |
| The linked audit stopped before starting because an isolated copy of the LLVM tools could not find `libc++.so.1` | A tool-loading failure, not an artifact verification failure. Supplying the library path then reproduced the documented range-disassembly cost instead of fixing it | Run the versioned audit against the copied immutable bundles on a verification host that has GNU AArch64 binutils | Decide the audit host before build A and record GNU tool availability in the build record; treat a library-path workaround for the unqualified tool pair as a stop condition |

## Time and resource expectations

The qualified P2.54 pair took `38:11.82` and `38:27.73`, peaked at about
`24.25 GiB` RSS, and completed without swap. These measurements are a planning
baseline, not pass criteria. A large timing change should trigger inspection of
jobs, memory pressure, source path, toolchain, and whether an audit was
accidentally run concurrently.

The corrected P2.58A pair took `39:05.92` and `39:34.50`, with Build B peaking
at about `24.26 GiB` RSS and no process swaps. A measured 4.4 GHz link burst
reached `69.1 C` and did not reduce total wall time relative to Build A. The
high-clock result is a negative thermal/performance finding, not a default
optimization.

### CPU frequency lanes

Clock policy changes wall time and temperature only. It does not change the
built bytes, so it never affects reproducibility or A/B equality. Record which
lane a qualification pair used.

| Lane | Setting | Requires | Notes |
|---|---|---|---|
| Capped | `performance` with `scaling_max_freq` at the stable cap, restored to `schedutil` afterwards | root on the build host | Preferred when the privilege is available; avoids sustained operation near the critical point |
| Default | `schedutil` with the stock maximum and kernel/hardware throttling | none | Acceptable. Temperature must be recorded read-only, with no automatic build kill |

Do not pin a high P-state manually unless cooling or an intermediate P-state
has been separately qualified. Do not block a qualification build only because
the capped lane cannot be applied; select the default lane and record it.

A P2.70 pair ran the default lane and reached a `69.5 C` peak under kernel
throttling, above the `69.1 C` burst recorded for the capped decision. That is
a thermal observation about this host, not a build defect.

The corrected P2.60 v4 pair took `40:43.23` and `40:45.31`, peaked near
`24.25 GiB` RSS, and completed without swap. A later Process v2 terminal-stage
consumer bug required only downstream host regeneration; rebuilding this
byte-identical pair would have been incorrect recovery.

Do not spend this cost during source iteration. The candidate source contract,
userspace, proof adapters, selector, and enforcement must be frozen first.
Full LTO is the final qualification step, not the development compiler.

## Final operator checklist

Before build A:

- [ ] The lane table says a kernel rebuild is required.
- [ ] Candidate source contract, intent, patch, and userspace are frozen.
- [ ] Exact two-link userspace entrypoints match the selected stock-closure
      adapter before kernel build A.
- [ ] Canonical source realpath, clang pin, jobs, and private output paths are
      recorded.
- [ ] Fresh preflight passes with absent `$SOURCE_TREE/out` and a new result
      directory.
- [ ] Memory, swap, and disk gates pass.
- [ ] GNU AArch64 linked-audit tools are available on the build host, or the
      verification host that has them is named.
- [ ] The CPU frequency lane is selected and recorded.
- [ ] One detached launcher has a validated completion hook.

Between A and B:

- [ ] Build A wrapper result and return codes pass.
- [ ] Source restoration passes.
- [ ] All six artifacts plus `build-result.json` are copied and hash-verified.
- [ ] Only generated `$SOURCE_TREE/out` is removed after its canonical parent
      check.
- [ ] B uses the same canonical source path and arguments.

After B:

- [ ] All six artifacts are byte-identical.
- [ ] Versioned GNU linked audit passes against both immutable bundles.
- [ ] Userspace and package generation are repeated where required.
- [ ] Both boot-only packages are byte-identical and contain only
      `boot.img.lz4`.
- [ ] Independent closure and offline Process v2 promotion pass.
- [ ] Failures are resumed from their earliest invalid boundary, not from the
      beginning.
- [ ] Private outputs remain ignored and tracked diffs contain no private
      identifiers.

## Stop conditions

Stop the candidate build line when:

- source-overlay, toolchain, resource, clean-output, or source-restoration
  checks fail;
- the source, intent, patch, or a source-bound proof adapter changes;
- either clean build fails;
- any of the six artifacts differs;
- the linked audit or independent static checker fails;
- a package contains anything except `boot.img.lz4`; or
- private artifact identity becomes ambiguous.

Fix host inputs and derive a new candidate identity when required. Do not
convert an H0 build failure into a device experiment.
