# S22+ P428 adversarial diagnosis: real init arguments rejected before logging

Status: **H0_REPRODUCED_DEFECT; CORRECTED_AND_VALIDATED; INDEPENDENT_PASS_H0_CORRECTION**.
P428/P429 remain consumed and closed healthy. This unit contains no connected
read, device action, grant, physical candidate or replay. A90 and S20+ are
outside scope.

## Bounded question and intended capability

Explain why successive experiments did not separate internal progress from
evidence loss. Reconstruct consumed artifacts, execution order and raw evidence;
attack the explanation independently; reproduce a concrete defect using the
consumed ARM64 executable; then correct the demonstrated binding error and its
representative VM coverage. Completion is an evidence-backed diagnosis and
checked H0 correction, not another device trial.

The product objective remains FYG8 kernel -> Debian initramfs shell as initial
host PID1 -> necessary board/storage preparation -> installed Debian init,
services and same-boot SSH. The retained FYG8 kernel and stock modules supply
hardware support; small fixed helpers supply preparation and evidence. A healthy
Android return proves recovery only, not this Debian capability.

| Experiment | Purpose and execution order | What physical evidence establishes |
| --- | --- | --- |
| P425 | Initial Debian shell; platform preparation; parent measurement; native_data admission; installed-init/services/SSH | Authenticated preparation prefix only: seq 146, `i2c_msm_geni` BEGIN after `gpi` DONE. No authenticated full platform completion or handoff. |
| P426 | Move fixed UFS preparation and an exclusive evidence file before the final six platform clients | 156 authenticated records, 75 modules completed, then `ufs_qcom` BEGIN. P427 found no exact file in its clean protected mountless view. |
| P428 | Supervise preparation and writer separately so worker return, error and outstanding work can be distinguished from primary-log failure | Returned RAM has neither record family nor a fresh candidate kernel epoch. P429 found no exact file in its clean protected mountless view. |

These are different last observed boundaries. No last BEGIN establishes an exact
hang, returned syscall or terminal cause. The new P428 defect cannot be assigned
as the historical cause of P425/P426's earlier missing progress.

## Confirmed defect and actual-artifact reproduction

P425 and P426 raw kernel transcripts explicitly print `Run /init as init process`
and arguments `/init`, `bootconfig`, `nohyp_uart`. Their kernels match the kernel
in consumed P428. P426/P428 also have identical boot-header command lines,
`/init`, sourced script and shell inode bytes. The apparent zero-length shell
archive member is a newc hardlink whose actual payload was resolved and hashed.

The retained kernel's `init/main.c` forwards `argv_init` to `kernel_execve`;
`fs/binfmt_script.c` replaces argv[0] with interpreter/script and preserves the
remaining operands. The resulting shell cmdline is 36 NUL-separated bytes:

```text
/bin/sh\0/init\0bootconfig\0nohyp_uart\0
```

The consumed [PID1 measurement](../../workspace/public/src/debian/s22plus_initramfs_h0/pid1-measure.h)
accepted only the 14-byte `/bin/sh\0/init\0` tuple. The check therefore rejects
valid observed FYG8 input with EPROTO before reaching the shell/init hash checks.
Exact executable bytes alone did not make the invocation representative.

The predicate first appeared in P417 commit `6f2b535af0`. Frozen P418/P419
observers run it before gadget setup; P421/P426 file writers run it after
preparation; P425 measures before handoff. P428 moved it ahead of the first
preparation worker. This is code reachability, not proof each physical run
reached that check.

The decisive comparison used the **unmodified consumed P428 initramfs and
physical helper**, a generic ARM64 VM kernel, no disk and no NIC. No module-mocking
helper was substituted. The additional arguments were forced after `--` so a
generic kernel could not consume `bootconfig` as its own option.

| Consumed physical helper input | Authenticated result |
| --- | --- |
| Minimal VM tuple | Initial PID1 measurement passes, worker starts, then the expected generic-board guard returns 104. |
| Observed FYG8 tuple | `OBSERVER_START_ERROR`, EPROTO 71, initial PID1 not measured, no worker entry. |
| Supplemental sourced-script instrumentation only | Direct `/proc/1/cmdline` dump confirms 14 versus 36 bytes; physical-tuple helper exits 112. `/init`, shell and helper bytes are unchanged. |

This proves a code compatibility defect with the actual consumed executable.
It is a strong conditional explanation for P428: if execution reaches the
supervisor with the same FYG8 operands, it rejects before preparation. P428's
physical exit 112 is **not recovered evidence**, and an earlier target-only
failure remains possible.

## Why the failure disappeared from retained evidence

The exact consumed execution order is:

```text
FYG8 kernel -> /init (Debian shell PID1) -> sourced scripts/fyg8-dev
  -> fyg8-prepare -> fo_supervise
     -> root/direct-parent check -> shared state -> measure_pid1
        -> EPROTO: attempted S22DIAG1 -> return 112 -> shell parks
     -> only on success: fork worker -> board guard -> primary BEGIN
        -> sec_log_buf insertion/binding -> remaining prefix and UFS
  -> only after preparation succeeds: supervised file-log
     -> parent/helper/log measurement -> protected root admission
     -> bounded native_data file and synchronized records -> six clients
```

Sources are [file-first-prepare.c](../../workspace/public/src/debian/s22plus_initramfs_h0/file-first-prepare.c),
[failure-observer.h](../../workspace/public/src/debian/s22plus_initramfs_h0/failure-observer.h),
[integrated-prepare.c](../../workspace/public/src/debian/s22plus_initramfs_h0/integrated-prepare.c)
and [file-log.c](../../workspace/public/src/debian/s22plus_initramfs_h0/file-log.c).
The report's exact historical ordering was checked in the consumed source
snapshot; current links are navigation aids, not substitute provenance.

The two authenticated record families are logically distinct but share one
retention route: `checked_kmsg` -> ordinary printk -> stock `sec_log_buf` reserved
RAM -> returned `/proc/last_kmsg` -> bounded host capture. The rejected-entry
branch attempts its diagnostic **before this candidate loads the retained
writer**. A successful ordinary-ring write/readback is not retained-backend
initialization, synchronization or reset-survival proof. The persistent file is
later still, so its absence cannot independently observe this early rejection.

The worker's own primary BEGIN and module-BEGIN records must pass tmpfs write,
fsync and ordinary-ring readback before logger insertion. Evidence collection
can thus stop preparation. No observed P428 record distinguishes those other
pre-logger errors; the argument defect already gives a concrete earlier failure.

P428's complete 2,097,136-byte retained capture contains old Android shutdown
records and firmware transitions, with zero primary/diagnostic markers, kernel
banner, `/init` startup or logger probe from the candidate. All 13,240 kernel-style
timestamps belong to the old Android uptime. Comparable P425/P426 regions have
fresh kernel prefixes and hundreds of kilobytes of preparation output. The
candidate firmware handoff to the next warm-reset header spans only 693 bytes in
P428, versus 435,558 and 374,356 in P425/P426. Firmware text supplies context,
not authenticated candidate execution proof.

## Adversarial alternatives and limits

Three independent assignments examined entry/artifact identity, retained-carrier
behavior, and qualification/observer ABI. They considered counterexamples as
well as supporting evidence.

| Question | Evidence and present conclusion |
| --- | --- |
| Did a parser or wrong key hide valid records? | Receipts, full raw sizes and hashes reverified. Zero marker literals in P428 rules out parser filtering as the reason these bytes yield no record. Do not weaken decoding. |
| Was the shell, hardlink, helper ELF or parent relationship wrong? | Exact-archive minimal control starts the physical helper, measures PID1 and forks. These do not explain the controlled argument-dependent failure. Target-specific failures remain outside that VM proof. |
| Did mmap, wait, clocks or shared-state atomics cause the observed A/B difference? | The observed-argument case fails before fork; target UAPI/ELF inspection and twelve isolated ARM64 observer cases found no competing ABI/state defect. This does not prove Samsung scheduling or memory conditions. |
| Did two readers consume each other's records? | Kernel source gives each `/dev/kmsg` descriptor its own cursor; reads do not clear the global ring. This proposed mechanism is contradicted. |
| Can START race logger registration? | Yes: early printk import precedes hook registration. A START-only loss is possible, but it cannot alone erase the entire imported kernel epoch and earlier primary records. |
| Did Android overwrite last_kmsg after recovery? | Stock logger copies the previous ring to a private snapshot before importing current Android printk. Ordinary later Android activity does not rewrite that snapshot. Earlier firmware generation selection remains distinct and unresolved. |
| Can retained writes still be lost? | Stock DTBO selects a direct-mapped reserved ring; its append path has no explicit cache-clean/readback. Firmware also restores this medium. Cache/firmware retention is a possible alternative, not a demonstrated P428 cause. |
| Is P426's UFS endpoint the cause of P428? | Unsupported. P428 adds a demonstrated rejection before all module preparation. P426's last `ufs_qcom` BEGIN remains its own unresolved boundary. |

The same stock logger module, imports, Image and corrected structural binding
worked far enough to yield P426 records. A new generic ABI mismatch is therefore
less plausible than the reproduced pre-worker rejection. This is evidence-based
ranking, not proof that logger insertion happened in P428.

## Why the previous qualification missed it

All 26 consumed VM boots supplied only `console=ttyAMA0 rdinit=/init panic=1`.
They retained the shell/init bytes but omitted the actual kernel-provided argv.
Moving measurement before the first worker moved an old latent rejection ahead
of the only retained writer. The tests exercised later states after passing an
unrepresentative entry condition.

Prior signed-record unit tests validated decoders and proof separation; their
synthetic clock/error fields did not execute failed target syscalls. ARM64 VM
filesystem, byte-provenance and process tests were real, while Samsung module
insertion, provider readiness and UFS discovery were substituted. Their passes
remain evidence for those tested properties. They did not establish physical
entry compatibility or board readiness. The earlier review missed this
representativeness requirement despite the argv evidence already being present
in returned raw logs. Adding more downstream cases could not correct that miss.

## Narrow correction and validation

The correction was selected in this report before source editing. The shared
matcher now admits only the exact minimal tuple and the exact observed FYG8
tuple. It retains full length, NUL separators, order, executable path, shell/init
hashes, root IDs and parent checks. Unknown, reordered, duplicated, extra and
malformed arguments are rejected. A prefix is accepted only if it is itself the
complete already-allowed minimal tuple; arbitrary suffix acceptance is absent.

Six related FYG8/Debian VM consumers now use one `KERNEL_COMMAND_LINE` declaration
with `-- bootconfig nohyp_uart`. The narrower retired `stage-probe.c`, its policy
and `stage_probe_vm.py` are unchanged: their separate exact-minimal predicate is
an identified compatibility defect, not part of the current shared P428 path.
They require their own correction/review before physical reuse.

The [native/ARM64 regression harness](../../tests/s22plus_debian_pid1_argv_harness.c)
includes the production header. Its [tests](../../tests/test_s22plus_debian_pid1_argv.py)
exercise both valid tuples, actual VM operands, every truncation/single-byte
mutation, partial/reordered/extra operands, alternate script/shell command and
read failure. Fresh physical preparation/writer helpers are cross-compiled and
identified as static AArch64 ELF with unchanged shell/init identities.

Completed validation:

- Five new test groups pass with both native static binaries and actual ARM64
  binaries under QEMU; 17 existing diagnostic/owner tests also pass.
- All seven touched Python files compile. Both physical helpers cross-compile
  with repository warning/error flags and pass AArch64 `file` inspection.
- A two-helper-only overlay of the consumed archive preserves every other
  entry and metadata, including `/init`, shell and sourced script. Minimal
  and observed FYG8 tuples now both authenticate measurement and worker entry,
  ending at expected generic-board guard 104. An unexpected extra operand
  still produces authenticated EPROTO before worker entry. No disk/NIC is used.
- One complete updated ARM64 file-pilot VM case passes with physical init
  operands. Both supervisors authenticate measured PID1 and successful worker
  completion. A separate mountless-reader VM boot retrieves all 10,972 bytes
  and 14 authenticated records, including six client begin/return pairs.
  Outside-native_data bytes are unchanged. Samsung module/provider/UFS effects
  remain virtual substitutes; the file protocol asserts pre-unmount records,
  not physical retention or installed Debian ownership.

Independent review is **PASS_H0_CORRECTION**, zero blocking findings. The reviewer
pins all nine changed source/test files, independently redecodes the three
actual-helper comparisons and complete VM/file evidence with the frozen decoder,
and checks the exact two-binary overlay. Receipt:
`qualification/fix-review.json`, SHA-256
`1fb88f4f79e7d264c1f9af0bbfec5074c220977ed1eed4b655f507cc60168270`.
This verdict covers the H0 correction, not a fresh physical qualification.
Scoped link/privacy/diff checks pass; all 46 preexisting dirty/untracked files
are unchanged, and GOAL remains at 800 lines.

Old artifacts, raw captures, consumed claims and review pins stay unchanged.
The new source is H0 development only: old source-bound qualification is not
silently transferred, and no physical candidate or authority is created.

## Evidence location and remaining boundary

Private evidence root:
`workspace/private/outputs/s22plus-p428-adversarial-diagnosis-20261015-1/`.
`entry/` binds extracted consumed entries, raw argv excerpts with offsets,
original commands/logs and frozen production decodes. `retention/` binds raw
captures, source/DTBO audit and firmware-region comparisons. `qualification/`
binds prior command coverage and ABI/control-flow falsification. New build,
regression and review receipts belong to this same H0 unit.

Correcting entry does not establish UFS return, clean root admission, persistent
file evidence, installed Debian services or SSH on the phone. The next physical
claim, if separately selected and qualified, must establish a new observed
boundary beyond entry rather than infer it from another healthy rollback. This
unit does not rerun P428 or investigate optional retention mechanisms by effect.
