# S22+ FYG8 R4W1-D contiguous retained proof

Date: 2026-07-21 KST
Scope: HOST-ONLY
Status: two complete-overlay builds passed; core reproducibility proven; final restoration hardening focused-tested and reviewed

## Prior result

The first Process v2 F1 run transferred the exact candidate boot and restored
the exact Magisk boot. Final device health passed, but the durable verdict was
`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`.

Both retained observer reads were identical:

- size: 2,097,136 bytes, the complete FYG8 log payload;
- SHA256: `bbc7c88c42fbaeaf478075df63e5a839384d4d482c22fb2365ccee0389d9497b`;
- R4W1-B family count: one;
- exact 99-byte R4W1-B marker count: zero.

The retained data matches the first 73 bytes of the exact marker, including its
leading newline. The remaining 26 bytes are replaced by following boot-log
content. The vendor log source writes a circular payload and splits writes at
the payload end. `sec_log_buf` is built as a module, so it cannot be an active
writer before the first successful `/init` transition. Together these facts
identify ring-boundary splitting followed by warm-boot overwrite as the
load-bearing failure mode; the earlier general multi-writer hypothesis is not
the observed failure.

## R4W1-D design

R4W1-D writes one 45-byte proof token only after:

- `kernel_execve("/init")` returned success on the unique ramdisk-init edge;
- `task_pid_nr(current) == 1`;
- the FYG8 retained log magic is exact; and
- the ring index proves the 2,097,136-byte payload has already saturated.

The token is placed as one contiguous range behind the current append cursor.
If the cursor is at least 45 bytes into the payload, the range ends at the
cursor. Otherwise it occupies the last 45 bytes of the payload. The code does
not change `idx`. This prevents proof splitting and leaves subsequent forward
writers starting after the proof. No separate diagnostic record is emitted.
The explicit tradeoff is that exactly 45 bytes of preexisting retained log are
overwritten; the full-ring saturation gate ensures the proof remains visible
to `/proc/last_kmsg` despite not advancing the cursor.

The exact token is:

`[[S22P1D|0e13f28e8558dde01ce3345f16408673]]`

Its ID is derived from the exact target, base `init/main.c`, carrier boot and
carrier init SHA256 values, exec-success semantics, and contiguous backfill
layout.

## Contract improvements

The host contract now:

- opens and hashes the exact carrier boot and init instead of trusting preimage
  literals;
- reapplies the patch to exact base files and pins every resulting source hash;
- matches the complete backfill helper and exec guard, rejecting operator,
  index, copy, barrier, saturation, and index-publication mutations;
- reruns DT and vendor ABI checks against the current source overlay, while
  retaining the old result only as historical corroboration;
- models both cursor sides, the observed 73/26 split, unsaturated indices, and
  the 32-bit index boundary; and
- requires the final build to contain exactly one proof in `Image` and
  `vmlinux`, `CONFIG_SEC_LOG_BUF=m`, and a separate regular `sec_log_buf.ko`.

## Validation

The combined R4W1-D contract, build-adapter, and Process v2 classifier suite
passes 46 tests. Python bytecode compilation and `git diff --check` pass.
`ruff` is not installed on this host.

An independent `gpt-5.6-sol` high-reasoning review found no critical, high,
medium, or blocking issue and returned
`GO_HOST_ONLY_TO_CLEAN_FULL_LTO_BUILD_AND_STATIC_AUDIT`. Its three low findings
were closed by making the observed 73/26 convention explicit, renaming the
mocked-lineage unit test, and requiring the generated module to be nonempty and
start with an ELF header in addition to `CONFIG_SEC_LOG_BUF=m`.

The local recovered kernel source is intentionally insufficient for promotion:
it lacks the complete current DT/vendor overlay and the local machine does not
meet the Full-LTO memory gate. The complete build-PC overlay was therefore used
for the build below. No candidate manifest, device authority, or live action was
produced by this unit.

## First complete-overlay build

The clean Full-LTO build completed with build command return code 0 and all
original output gates passing. Its measured build phase took 35:57.23, reached
24,242,136 KiB maximum RSS, and recorded zero swaps. Key output evidence:

- `Image`: 41,490,944 bytes, SHA256
  `bb768461a55a8ed4b36b4e5777e12e37953fa76fa3703b332b4273d653cbdcd9`;
- exact stock Image size and fixed ramdisk start preserved, with 1,536 bytes of
  pre-ramdisk slack;
- compact proof count exactly one in `Image` and one in `vmlinux`, with both
  historical marker families absent;
- exact FYG8 kernel banner match and `CONFIG_CRYPTO_FIPS=y`;
- 2,397 generated modules and both provider-module closures verified; and
- `sec_log_buf.ko`: regular ELF, 1,626,912 bytes, SHA256
  `f7b215634cfc47231693632970c5b6b6e56d69686c37c70872edc92d35eaf1bd`,
  with vendor config exactly `CONFIG_SEC_LOG_BUF=m`.

The build created Samsung's normal host packaging outputs, including a
`boot.img`. They remain unpromoted build byproducts: no candidate was
constructed and no device contact or flash was authorized.

The first run also exposed one source-hygiene gap outside the three patched
files. Samsung's build rewrote three archive-owned audio-header symlinks from
their original `/home/dpi/...` targets to the active work-tree path. The source
overlay audit caught the same shape before the final clean run, and a post-build
check proved the mutation recurred. The three links were restored to exact
archive targets. The adapter now derives all five absolute archive symlinks
from the content-addressed reconstructed member list, refuses a dirty starting
state, and atomically restores target and timestamps after success or failure.
The expanded local suite initially passed 48 tests; the build PC passed 19
focused tests, and the control recognized all five links against the actual
FYG8 manifest. This restoration behavior was added after the first build, so it
was not retroactively claimed by that result.

## Independent B build and reproducibility

An independent B source tree with a distinct inode and absent output root
passed the updated preflight. The preflight reopened the complete source
overlay and verified all five manifest-derived absolute symlinks before build.
The second clean Full-LTO build then completed in 35:56.34 with 24,239,016 KiB
maximum RSS, zero swaps, and exit status 0.

Its restoration runtime observed exactly the three expected vendor mutations:

- `vendor/qcom/opensource/audio-kernel/include/soc/internal.h`;
- `vendor/qcom/opensource/audio-kernel/soc/core.h`; and
- `vendor/qcom/opensource/audio-kernel/soc/pinctrl-utils.h`.

All three were atomically restored to the archive `/home/dpi/...` targets. The
two toolchain absolute links remained unchanged, and all five targets were
reopened successfully after build. The three patched source files also returned
to their exact base hashes.

The A and B builds are byte-identical for every core GKI artifact recorded by
the builder: `.config`, `Image`, `Image.lz4`, `vmlinux`, `System.map`,
`vmlinux.symvers`, `abi.xml`, `modules.builtin`, and
`modules.builtin.modinfo`. The generated `boot.img` is also byte-identical.

The durable result identities are:

- A `result.json`: `b6ba4be438752e1858aa7fd28b62237104a1ead1e818d5509ce724c8db7e6527`;
- B `result.json`: `a39c94f070ea61443abe9e169ae248a7e74516f9f25cd8a933ae1ccdd665cc4d`;
- `.config`: `8cedb52f86427c78e275060324db54946bd853e6d49df5b5ff08dadf8e2273c4`;
- `Image`: `bb768461a55a8ed4b36b4e5777e12e37953fa76fa3703b332b4273d653cbdcd9`;
- `Image.lz4`: `4c84a204d5b4a4a0661aac5b5b32609812a138b40f9978632570dc683d84f293`;
- `vmlinux`: `c53fc635dcb8317fa47fa35740c22ba32d0fa327fc0caffd00609732cfbd7d92`;
- `System.map`: `4087de55bc77e621aae25c6ddf492bae53d7f463c41001eaf4f7f09c5042f337`;
- `vmlinux.symvers`: `fd75413401617a427ddf6c264d0ae4f5452b46cde02b4575b9af09f19601ca19`;
- `abi.xml`: `3660c592e1884ab323816c09a3abd197744c8b2f78aed890b02c3e69dbc1c55c`;
- `modules.builtin`: `f9711ca3f001167eccec6a60924e23eecbd30f126a1a5b4121412ce4136399c4`;
- `modules.builtin.modinfo`: `632c673947987d480515fcf472ce152dcb97098555f7298108d0c341be5ab7a6`;
- generated `boot.img`: `74e0550fb87343f3a7bde64627bce3ebbe0b99b716939b147897cc6a437d8696`.

Some unpromoted vendor packaging outputs and the raw `sec_log_buf.ko` differ.
The module has the same size and vermagic in both builds. On temporary copies,
removing debug sections and `.note.gnu.build-id` makes the two modules exactly
identical at SHA256
`84085a8950ff3d7a750aaa3c8650c641335580ef98c158fb867a8f58c456e666`.
The differences are therefore path-derived debug/build-id material, not
loadable code. `vendor_boot.img`, `vendor_dlkm.img`, and `super.img` inherit
that non-load-bearing module metadata and are neither candidate inputs nor
promoted outputs for this boot-only rung.

## Restoration failure-path hardening

An independent adversarial review after the B build found that the initial
restoration implementation was sufficient for the observed successful path but
unsafe under namespace and cleanup failures. A replaced parent directory could
redirect path-based restoration outside the source tree, one restore failure
could leave later links unprocessed, and metadata-only changes could pass. A
follow-up review also found that simultaneous build-body and cleanup failures
could hide the source-corruption diagnosis at the CLI.

The final adapter closes those cases by:

- opening the work-tree root and every controlled parent directory before the
  build, traversing components with `O_NOFOLLOW`, and retaining those
  descriptors through cleanup;
- restoring each link through its bound parent descriptor, attempting every
  link before raising an aggregate failure;
- restoring and comparing symlink atime and mtime even when the target did not
  change;
- reopening every path through the pinned root and requiring exact parent
  device/inode, target, type, and timestamp identity; and
- reporting both the guarded body failure and aggregate cleanup failure in the
  primary exception text when both occur.

Regression tests cover parent replacement without out-of-tree writes, an
injected first-link restore failure with later-link recovery, metadata-only
mutation, and simultaneous body/cleanup failure. The final combined local suite
passes 52 tests; the build host passes 23 focused tests against the actual B
source tree and recognizes all five archive-owned links with pinned root and
parent identities. Targeted bytecode compilation and `git diff --check` pass.
The same independent reviewer returned `GO` with no remaining critical, high,
or medium issue.

Both full builds preceded this final descriptor-bound hardening. Therefore the
B result proves the real vendor mutation shape, successful restoration, and
core output reproducibility; the exact final failure-path revision is claimed
only from focused local/build-host tests and review, not retroactively from a
third full build.

## Next gate

Adapt the full R4W1-B static audit and reproducibility checker to the R4W1-D
proof contract, reopen both independent build results and artifacts, regenerate
the FIPS evidence, and emit one durable host-only verdict. Candidate
construction and fresh Process v2 approval remain downstream of that gate.
