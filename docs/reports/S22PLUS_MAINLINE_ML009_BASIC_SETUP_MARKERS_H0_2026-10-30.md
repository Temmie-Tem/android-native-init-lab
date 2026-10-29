# S22+ ML009: before/after basic-setup progress witnesses

Preparation checkpoint: **READY_H0_AND_CURRENT_D0_NO_EXPERIMENT**.
Candidate build/artifact qualification, independent review, production task
preparation and the first fixed preapproval D0 passed. The remaining bounded
unit requires exact new one-operation attended approval, one physical
experiment, original-A recovery and the existing post-closure retained-log
read. Readiness freshness and all effect-time checks remain mandatory. No approval, grant or device
operation is armed. A90 and S20+ remain untouched.

## Selection and evidence limits

The consumed, healthy-closed [ML008 run](S22PLUS_MAINLINE_ML008_RUN_2026-10-30.md)
recovered five post-kthreadd-wait records and no post-async-sync record. Its
complete raw log, returned-boot health brackets and independent decoding agree.
All 116 USB snapshots showed absence. The operator reported the same boot-loop
interval as earlier experience; no numeric period or cause was established.
The missing second frame does not identify a failure interval or prove
non-execution. The first frame does not prove its own helper's later return.

Two-round Claude Opus 5.5 and Gemini 4 Argon High discussion and independent
static analysis selected calls immediately before and after `do_basic_setup`
in `kernel_init_freeable`. This brackets a broad coherent phase rather than
adding per-initcall writes. It can extend positive evidence through early
kernel-thread preparation, regular driver/subsystem initcalls, or toward the
remaining initramfs/access/async tail. No outcome is presumed.

The discussion corrected several proposed checks and claims: the early/pre-SMP
`do_one_initcall` site is before the first marker, while the regular-loop site
is between them; the relevant functions are inlined; this build emits neither
`do_ctors` nor KUnit calls; and the helper is compiled from a generated header
inside `init/main.o`. No build-id, normalized instruction-body gate, forced
scheduler/migration test, generic CFG framework or partial-frame decoder was
adopted. A later positive proves return from the preceding helper call on
that candidate's path, which may have skipped writing and some or all cleanup.
It does not prove that an earlier record committed or that both frames share
one boot. Existing full-frame, positive-only interpretation is unchanged.

A pre-basic positive would establish the recording point after early initcalls,
SMP/scheduler, workqueue/async/padata and late page-allocator preparation. It
would not prove its own return or entry into basic setup. A post-basic positive
would establish the point after driver-model setup and regular initcall
traversal returned. Initcall return codes are discarded by the loop; traversal
is not driver/probe success. `populate_rootfs` schedules exclusive-domain async
work, so post-basic is not initramfs completion. Deferred work and the remaining
explicit initramfs wait, console/access/integrity tail and global async barrier
remain distinct. Neither point proves userspace exec or authenticated USB.

Missing frames locate nothing. Five historical frames are not five boots, and
ML008 is not a same-build ML009 control. Static frames do not encode live
PID/CPU/preemption/DAIF or establish the last attempt, period or reset cause.

## Smallest change and safety scope

V7 uses a distinct schema, magic, integrity domain and stages 13/14 named
`pre-basic-setup` and `post-basic-setup`. Both V6 calls are removed. Complete
source comparison against the unmarked base finds only `init/main.c` and its
generated header changed. The writer template, fixed two 128-byte slots,
untouched header, guards, bounded Normal-NC/XN maps, header recheck, prefix-last
commit and reverse cleanup remain unchanged. There is no IRQ/preemption,
config, DT, forced-command-line, watchdog, storage or RAM-responder change.

Both calls remain in the preemptible kernel PID1 initialization thread under
SYSTEM_SCHEDULING before init-memory freeing. V6 already covered this task
context and post-initcall worker/async concurrency class. The scoped independent
static recheck found the same global mapper-reference inventory and unchanged
input exclusions, with FIX_BTMAP ownership confined to the early mapper and
other fixmap slots separate. One CPU, an IRQ mask or an async barrier is not
used as a serialization argument. A writer-local guard would not serialize a
peer suspended after selecting a slot; no such enabled caller was found.

The covering bare no-map/non-reusable reservation still has no compatible,
phandle, memory-region consumer or overlapping explicit non-memory range.
PSTORE remains disabled. The same OF/memblock paths keep these pages reserved
and outside buddy allocation. This does not establish exclusive ownership
against firmware or physical coherency/retention.

The late early-map leak check runs in PID1 between the sites. Successful first
helper mappings must already be removed before it is reached; the helper can
also return without mapping or writing. The leak check does not certify the
later writer. Qualification checks restoration of the prior slot/PTE state,
including intentional occupied-slot fixtures, rather than assuming all tests
begin with empty slots.

## Qualification

A focused `init/main.o` compile passed before the full build, reusing its
outputs in the same private build directory. Its actual relocations place
`page_alloc_init_late -> pre marker -> cpuset_init_smp` and
`kfree -> post marker -> wait_for_initramfs`. No `do_basic_setup` call or old
instruction address is invented. Fresh linked qualification confirms both
boundary calls, the early and regular per-initcall back edges, and the regular
level-loop back edge against the emitted eight-level table. The parent returns
from `kernel_init_freeable`, then async synchronization, then stores value 2
to the actual `system_state` symbol before freeing init memory. Caller, helpers,
frames and mapper metadata remain within their live init range. PAC/canaries
and fixmap TLB barriers are retained. The allocator-failure panic edge remains
a permitted nonreturning exit; the post marker is not required to always run.

The new format reuses V6's same-build compiler/config layout derivation and
PID0/PID2 calibration, with actual PID1 equal to the initial namespace reaper
and the task at `kernel_init` entry. Each helper's entry/return must show one
online CPU0, low preemption count zero, IRQs unmasked, SYSTEM_SCHEDULING and
late-map selection. All 13 real EL1/VHE EL2 mapping cases passed those four
entry/return observations with freshly derived layouts. These are qualified
VM/source properties, not live fields in a physical frame.

The mapping fixture retains the exact physical candidate initramfs and stops
after the second helper before userspace. The separate full RAM-PID1 VM keeps
its distinct VM initramfs and invalid-header write-skip path. It is not a
positive marker or physical USB test. All 318 actual linked C cases and 13
real mapping cases passed, including all 512 no-map pages, positive adjacent
RAM, temporary Normal-NC/XN attributes and cleanup. Full same-Image RAM PID1
VM and its offline raw recheck passed. The loader passed 20 cases, 1,051 copy
cases and actual EL1/EL2 entry with EL3 refusal. Two 96-MiB boot images and
AP archives are identical. The complete ARM64 build has no errors, warnings
or section mismatches. Image SHA-256:
`ba9a6a8546f0f0fd908b6c5fdf87f8b5e0821aa0a5065cd99467ca66b6114b44`.

All 86 focused host tests passed: 18 marker, 22 retention/admission and 46
other mainline tests; touched Python compiled. The first marker-test and full-VM launcher invocations
omitted the already retained Unicorn dependency path, causing imports to fail.
The test rerun passed using that path. The VM import failure occurred before
QEMU started; its command/source snapshot and failure log remain preserved,
and the corrected invocation passed in fresh `vm-2`. No dependency
install, source assertion change or device effect was needed. Historical V1-V6 complete raw captures rederive 12/12/10/12/10/5
records unchanged, with protected proof/journal bytes preserved. V7 decoding
of the complete ML008 raw log yields no V7 record.

Past-failure applicability: ABI binds fresh layouts and real EL/PAC/canary;
SEMANTIC/WIRE preserve positive-only claims and old formats; ROUTE/ARTIFACT
bind the inlined call/loop boundaries and physical-initramfs fixture; PERSIST
keeps actual producer/consumer receipts; HOST retains build/VM evidence;
RETURN keeps original-A ownership, health and no replay. No display or live
transport change is selected.

## Independent review and production preparation

Final independent review returned **PASS_GO with no findings**. It verified
68 current source pins and frozen copies, 378 artifact/raw-evidence pins,
37 capability sources, 44 backend sources and both unchanged worker sources.
It independently reproduced source/frame generation, actual linked loops and
lifetime, all 13 raw mapping outputs and contexts, full-VM authentication,
physical initramfs/package joins and historical V1-V6 decoding. The descriptive
unit-test import-failure record is distinguished from the raw VM failure log.
The V7 capability and backend v18 receipts now select this reviewed closure.
The existing worker remains connected with unchanged loaded source identity.
PASS_GO qualifies the capability, not a device run.

Production image qualification and exact task preparation succeeded against
the closed ML008 predecessor. The current-production retained-log projection
also reproduced ML008's result offline with acquisition blocked and all
protected proof/journal bytes unchanged. The fixed preapproval D0 collected a
complete seven-read rooted Android health transcript, with no device control
or partition transfer. No approval file, grant or operation exists. If its
five-minute freshness expires before grant opening, the existing fixed
read-only readiness is refreshed before execution; exact new approval and
actual attendance remain required.

| Receipt | SHA-256 |
| --- | --- |
| Marker qualification | `a980db539fd6aba6d233501490b4e16b4e8c5dd6c3ecb869a2b6eae488b2cd80` |
| Independent final review | `48df029de3e169a622bc86d6037a6343ab401673cdc77c1fe3e400550805c4fe` |
| Exact prepared task | `db650fdf94f9dfea0cbadbb10f482e317a441fd7858adb3dfda39a2ad1e7aec7` |
| First readiness summary | `322af143117fb403964bf32a19a4a905d55a2422e7a5fd6a2b7a4e5df96c7fc2` |
| Historical production projection | `069b23ab4335a99ccdf99fa3707966507b954ae13d8f06c4871fdb015e48fba0` |

## Private evidence and external-model accounting

Discussion:
`workspace/private/outputs/s22plus-mainline-ml008-next-discussion-20261030-1/`.
Fresh candidate:
`workspace/private/outputs/s22plus-mainline-ml009-h0-20261030-1/`.

All four model calls completed without failure, refusal or fallback. Claude
reported 4 uncached input, 45,599 cache-creation input and 20,369 output tokens,
including 12,840 thinking tokens. Its CLI list-price equivalent was USD
0.772188, not subscription billing. Argon reported 60,944 input and 17,667
output tokens, including 10,351 thinking tokens, for 78,611 total; cost was
unavailable. Claude five-hour utilization snapshots moved from 29% to 32%.
Fresh-session Argon weekly remaining snapshots moved from 70.68% to 68.69%.
These account-wide changes are not exact per-call attribution. Before/after
snapshots, token reports and accounting were appended privately without
credentials.
