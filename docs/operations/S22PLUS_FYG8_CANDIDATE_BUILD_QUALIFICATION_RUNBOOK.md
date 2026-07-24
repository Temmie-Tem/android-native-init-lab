# S22+ FYG8 candidate build qualification runbook

This runbook defines the reusable H0 sequence for qualifying a final FYG8
native-init candidate. It composes the existing checked build, candidate, and
Process v2 tools. It does not replace their source contracts or weaken their
fail-closed checks.

This is not the implementation-loop default. Use focused tests and
development-only thin/no-LTO builds while changing code. Run this clean
Full-LTO sequence only after the candidate source contract and userspace have
been frozen.

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
- no existing `out/` tree and a new result directory; and
- no source, intent, patch, adapter, dispatcher, or candidate-enforcement
  change after intent derivation.

The exact resource and provenance predicates are owned by the build wrapper.
Do not bypass a failed preflight based on a manual estimate.

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

## 3. Clean build B

Remove only the generated source-tree `out/`. Keep the A bundle and all
receipts.

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

Do not continue from partial `out/`, manually edit read-only archive files, or
reuse a failed result directory.

## Observed failures and recurrence controls

These are host incidents already encountered by the FYG8 build line. They are
not hypothetical policy requirements.

| Symptom | Correct interpretation | Recovery | Recurrence control |
|---|---|---|---|
| Preflight reported five source-overlay mismatches after an interrupted build | The old wrapper stopped after editing reproducibility controls | Restore only `_setup_env.sh`, `build.sh`, the common `Makefile`, and the two VDSO Makefiles named by preflight from the hash-verified pinned archive; discard partial `out/` | Never start Full LTO until a fresh preflight reports zero overlay mismatch; verify post-build source restoration |
| Detached-build completion file contained literal `$?` or was empty | The shell hook was quoted incorrectly; it did not by itself invalidate a complete wrapper result | Judge the finished build from the wrapper result, its two return codes, and `/usr/bin/time`; repair the hook before another build | Use the single-encoding Python launcher above and reject malformed completion files |
| Build host lacked GNU AArch64 `nm`/`objdump`; LLVM substitution consumed over 24 GiB for more than 25 minutes | The versioned audit is qualified against GNU binutils, not that LLVM range-disassembly behavior | Stop the non-authoritative LLVM run and audit the copied immutable bundles on a controlled GNU-binutils host | Check GNU tools before build or reserve a verification host; do not select tools by basename fallback |
| Offline promotion was given `candidate-a/AP.tar.md5` | Candidate generation succeeded, but the caller used the wrong path | Re-run only the host promotion with `candidate-a/odin4/AP.tar.md5`; do not rebuild or repackage | Treat `odin4/AP.tar.md5` as the candidate-builder output contract and verify it before promotion |
| A clean build used a different absolute source-tree name | Source path and build-ID inputs changed, so linked bytes differed despite equivalent sources | Re-run B from the same canonical path after a clean preflight | Pin one canonical absolute source path in both build invocations |

## Time and resource expectations

The qualified P2.54 pair took `38:11.82` and `38:27.73`, peaked at about
`24.25 GiB` RSS, and completed without swap. These measurements are a planning
baseline, not pass criteria. A large timing change should trigger inspection of
jobs, memory pressure, source path, toolchain, and whether an audit was
accidentally run concurrently.

Do not spend this cost during source iteration. The candidate source contract,
userspace, proof adapters, selector, and enforcement must be frozen first.
Full LTO is the final qualification step, not the development compiler.

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
