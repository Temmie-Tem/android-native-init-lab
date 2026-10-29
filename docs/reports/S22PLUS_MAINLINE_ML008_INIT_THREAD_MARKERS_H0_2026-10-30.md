# S22+ ML008: kernel_init wait and async return witnesses

Preparation checkpoint: **READY_H0_AND_CURRENT_D0_NO_EXPERIMENT**.
Candidate build and artifact qualification, independent review, production
task preparation and the first fixed preapproval D0 passed. No approval, grant
or device operation is armed. The remaining bounded unit requires an exact
returned one-operation attended approval, one physical experiment, original-A
recovery and the existing post-closure log read. Readiness freshness and all
effect-time checks remain mandatory. A90 and S20+ remain untouched.

## Selection and evidence limits

ML007 reached the pre-rest-init recording point, with five intact records at
each V5 site, and closed healthy original A. USB/PID1 remained NO_PROOF. The
operator reported a boot loop at the same interval as earlier experience;
no numeric period or reset cause was established. That consumed run is not
replayed, and its removed helper's return is not proved by a successor.

Two-round Claude Opus 5.5 and Gemini 4 Argon High discussion selected two V6
calls in `kernel_init`: immediately after `wait_for_completion(&kthreadd_done)`
returns, and immediately after `async_synchronize_full` returns before
`SYSTEM_FREEING_INITMEM`. Both models corrected initial outcome tables that
had improperly localized failure from missing records or treated a later-only
positive as contradictory. The final interpretation remains positive-only.
One residual Argon phrase claiming the earlier helper necessarily unmapped
is not adopted: its call may return after skipping some or all mapping/writing.

The post-wait record would prove its recording point in this candidate's
kernel initialization path. It would not prove that the wait slept, a specific
scheduling invocation, IRQ delivery or timer ticks. The post-async record would
prove the later point after the preceding helper call, `kernel_init_freeable`
and `async_synchronize_full` returned. Returned initcalls do not prove every
driver succeeded; returned initramfs/access paths do not prove successful
unpack or `/init` access. Registered-domain synchronization does not quiesce
exclusive async domains, ordinary workers, kthreads or future queued work.

Neither static frame encodes live PID/CPU/preemption/DAIF, proves its own later
cleanup/return, init-memory freeing, userspace exec or authenticated USB. A later
positive with no USB does not eliminate earlier nonfatal/deferred driver defects
or localize failure after initialization. Missing frames locate nothing; an
earlier call may skip or its record may be lost. There is no same-boot pair,
boot count, last-attempt or reset-cause claim. A kernel PID1 task witness stays
separate from the existing RAM-userspace PID1/USB result.

## Smallest change and actual context

V6 has distinct schema/magic/integrity domain and stages 11/12, named
`post-kthreadd-wait` and `post-async-sync`. Both V5 calls are removed. Only
`init/main.c` and its generated header differ from the complete unmarked base.
The C template, fixed two 128-byte slots, untouched header, Normal-NC/XN
mappings, guards, header recheck, prefix-last commit and reverse cleanup are
unchanged. No IRQ/preemption wrapper, scheduler-forcing harness, watchdog,
storage, DT, config, command-line or RAM responder change is added.

The `__ref` caller reaches both init-only helpers before init memory is freed.
Actual linked instructions put each helper directly after its named return;
after the second call, the value-2 store resolves to `system_state`, followed
by `kprobe_free_init_mem` and `free_initmem`. Helpers, frames and early-map
state remain inside the init-memory range. Linked PAC/canaries and fixmap TLB
invalidation/barriers remain. The standard ARM64 build has no errors, warnings
or section mismatches.

Unlike V5's initial task, these sites are in preemptible kernel PID1 with
SYSTEM_SCHEDULING, low preemption count zero and IRQs unmasked. The scoped
independent preliminary analysis found no enabled competing early-map caller
in post-initcall task/work/async/interrupt paths. Exact config/DT excludes the
relevant EFI/ACPI/SDEI routes and other disabled clients. The covering bare
no-map, non-reusable reservation has no compatible, phandle, consumer or
conflicting reg overlap; unmatched reserved-memory setup leaves it reserved,
and buddy handover excludes its pages. PSTORE is disabled. Final independent
artifact review confirmed these findings against the fresh source/config and
actual loader-rewritten DT.

This exclusion does not follow merely from one CPU or the async barrier. A
writer-only IRQ guard cannot serialize a peer already suspended after slot
selection, and no such peer was found. Forced need_resched manipulation would
not by itself establish a context switch or add a necessary safety assertion.

## Qualification and fixture inputs

The host-only layout probe reuses this build's actual saved asm-offsets compiler
argv, with private source, assembly and dependency destinations. It verifies
the Image's compiler/config identity and derives task PID and namespace
child-reaper offsets and widths. Derived CPU/preemption offsets must match the
same build's generated definitions. No historical offset becomes a fixed
answer, and no debug configuration or candidate bytes are changed.

Real EL1/VHE EL2 tests observe PID1, current equal to the initial namespace
child reaper, the same task as kernel_init entry, and PID0/PID2 calibration.
Both helper entries and returns must have low preemption count zero, IRQs
unmasked, SYSTEM_SCHEDULING, late selector and one online boot CPU. The existing
seeded-header matrix retains no-linear-alias checks across all 512 log pages,
positive adjacent-RAM calibration, active Normal-NC/XN attributes, bounded
failures and complete PTE/slot cleanup at both sites.

The existing marker VM had no initramfs, which was sufficient before
`rest_init`. At the new later point it would find no `/init` and enter the
namespace/mount failure path before the second witness. This was identified
from the real consumer before running the new matrix. Only V6's mapping
fixture now loads the exact hash-bound physical candidate initramfs and stops
after the second helper, before userspace. Admission joins that fixture input
to the physical image. The separate full-PID1 VM retains a distinct VM
initramfs and unseeded/invalid-header write-skip path; it is not a positive
marker test or physical USB proof.

Completed checks: 84 focused host tests plus 22 retention tests, touched-Python compilation,
318 actual linked C cases, full exact-Image RAM PID1 and offline raw recheck,
20 loader cases, 1,051 copy cases and actual loader EL1/EL2 entry with EL3
refusal. All 13 real-mapping cases passed, including four PID1 entry/return
observations per case and fresh layout calibration. Two 96-MiB boot images
and AP archives are identical. Historical V1-V5
complete raw captures rederive 12/12/10/12/10 records unchanged, with protected
proof/journal bytes preserved.

Past-failure applicability: ABI covers derived layouts and real EL/PAC/canary;
SEMANTIC/WIRE preserve positive-only claims; ROUTE/ARTIFACT bind the later VM's
required initramfs and actual calls; PERSIST binds the real producer/consumer
receipts; HOST retains compiler/VM evidence; RETURN keeps original-A ownership,
health and no replay. No display or live transport change is selected.

## Independent review and production preparation

Final independent review returned **PASS_GO with no findings**. It verified
68 current source pins and frozen copies, 358 artifact/raw-evidence pins,
37 capability sources, 44 backend sources and both unchanged worker sources.
The review separately reproduced source changes, actual linked call/lifetime
placements, all 13 raw mapping outcomes and contexts, full-VM authentication,
physical initramfs/package joins and historical V1-V5 decoding. The unchanged
worker, owner, recovery and final-health implementation retains its previous
reviewed bytes. The V6 capability and backend v17 receipts select this reviewed
closure; PASS_GO qualifies that capability, not a device run.

Production image qualification and exact task preparation succeeded against
the closed ML007 predecessor. The current-production retained-log projection
also reproduced ML007's existing result offline with acquisition blocked and
all protected proof/journal bytes unchanged. The fixed preapproval D0 collected
a complete seven-read rooted Android health transcript. It performed no device
control or partition transfer. No operator approval file, grant or operation
exists. If the five-minute readiness lifetime expires before grant opening,
only the existing fixed read-only readiness is refreshed; the experiment is
not dispatched until the exact new approval and attendance are supplied.

| Receipt | SHA-256 |
| --- | --- |
| Marker qualification | `7fbade2ac98572b588794426cea887f7de37f85ffbb16dbb1114a887a010a248` |
| Independent final review | `e65e69d9b8f4445080a1999c833eb20fa6638f53fcd3675859f42be768990f81` |
| Exact prepared task | `0bb8bbe28eb9e2463c21520d3fd62027fdef6ebcad1ae04c7684a5a1c4b9cc22` |
| First readiness summary | `e5b95187ffbc0944fefc6b6ae77b34b89fe9051c1c12787216340c2669f35762` |
| Historical production projection | `992615e058296fb10edc5c1443e372d99cb3ce0da4b74855156a5ca605c9e65b` |

## Private evidence and external-model accounting

Discussion and layout feasibility:
`workspace/private/outputs/s22plus-mainline-ml007-next-discussion-20261030-1/`.
Fresh candidate:
`workspace/private/outputs/s22plus-mainline-ml008-h0-20261030-1/`.

Four model calls completed without failure, refusal or fallback. Claude reported
4 uncached input, 50,822 cache-creation input and 18,980 output tokens, including
11,251 thinking tokens. Its CLI list-price equivalent was USD 0.786192, not
subscription billing. Argon reported 60,332 input and 17,159 output tokens,
including 9,271 thinking tokens, for 77,491 total; cost was unavailable.
Claude five-hour utilization moved from 24% to 27%. Fresh-session Argon weekly
remaining snapshots moved from 72.70% to 70.75%; intermediate same-session
views stayed at 72.70% and may have been cached or delayed. The provenance
qualification was appended privately. These account deltas are not exact
per-call attribution. No credentials were recorded.
