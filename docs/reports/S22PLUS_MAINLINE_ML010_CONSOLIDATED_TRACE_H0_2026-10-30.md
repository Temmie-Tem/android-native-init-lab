# S22+ ML010: consolidated initcall progress evidence

Status: **READY_H0_AND_CURRENT_D0_NO_EXPERIMENT**.

The selected bounded unit replaces repeated two-point physical trials with one
candidate that records all regular initcall dispatches and the following
pre-free-init milestones. No ML010 approval, grant or device operation is armed.
ML009 remains consumed and closed healthy; A90 and S20+ remain untouched.

## Selection

The operator asked whether the next progress observations could be collected
in one experiment. The earlier two-slot limit was a reviewed implementation
choice, not a hardware requirement. An initial two-point proposal was abandoned
before instrumentation or a device effect. The revised candidate collects
entry/return records for every regular initcall, plus six fixed milestones,
within the same exact Samsung 2 MiB log slice.

Two-round Claude Opus 5.5 / Gemini 4 Argon High discussion supported full
coverage. Their second-round preference for a single ordinary `ioremap_wc`
rested partly on unmeasured timing estimates. Independent source analysis found
the existing transient mapper reusable with new writer/cardinality evidence.
That smaller mechanism was implemented and measured first. It holds no early
mapping across an initcall or the level-7 early-map leak check. A persistent
mapping's additional realm-hook, allocation and teardown obligations were not
introduced without a demonstrated need.

The discussion's omitted prefix invalidation, unsupported runtime estimates,
insufficient realm-hook shortcut and missing-return localization language were
not adopted. A new recording format does not make absent records causal proof.

## Records and bounds

The final Image contains **1,825 regular entries**, distributed across levels
0–7 as `8 / 151 / 58 / 138 / 193 / 65 / 1106 / 106`. These are fresh signed
four-byte PREL32 entries, resolved against that Image's ELF. Counts measure
neither runtime nor successful driver registration/probing.

V8 uses **3,656 records / 467,968 distinct payload bytes**. Slots 0–5 record:

1. Before basic setup, after late page-allocator preparation.
2. After `driver_init` returns.
3. Before regular-initcall command-line allocation.
4. After basic setup returns.
5. After the explicit initramfs wait returns.
6. After async synchronization returns, before init-memory freeing.

Slots `6+2*k` / `7+2*k` record before and after regular dispatch k. The wrapper
uses the original entry pointer and preserves the existing call order. Early
initcalls and module dispatches are unchanged. No runtime HMAC, clock read,
return-code collection, IRQ/preemption wrapper, config/DT change, watchdog
change, Linux storage access or new device command is introduced.

Each record invalidates eight prefix bytes, writes the 120-byte body, checks
the header again, then commits the eight-byte prefix with barriers. Thus the
selected candidate's maximum is **497,216 log byte stores**, all within the
467,968-byte slot span; the format ceiling is 4,096 slots / 512 KiB of distinct
payload and 557,056 stores. A firmware reboot loop has separate per-attempt
windows and bounds, not one fixed span for the entire operation.

The first eligible distinct event latches one four-word header snapshot and
one contiguous window. A short index retains only available complete slots,
prioritizing the six milestones and then early ordinal pairs. It does not
silently require the entire expanded span to fit before recording anything.
Every later record checks the same header before stores and before commit;
drift disables that attempt's remaining writes. A skipped event is never
retried. A later distinct event may establish the first window or proceed after
a mapping failure. Successful mappings are always removed in reverse order.

Returned log length or offsets do not reveal the candidate's original index,
window capacity or shared boot. The existing reader model verifies visibility
for eligible short prefixes and wrapped buffers without changing the header.

## Qualification

Only `init/main.c` and its generated header differ from the unmarked kernel
source. A focused ARM64 `init/main.o` compile preceded the full build. The
complete build has no errors, warnings or section mismatches. The fresh Image
SHA-256 is
`60c1b773132cc9f2bac203b18c86320631a30e02eadb94fa778f02235800ec87`.

Fresh linked inspection confirms the six fixed arguments and boundaries,
the unchanged early dispatch, and one entry/return wrapper pair around the
regular dispatch. The compiler copies the original entry to the argument
register before advancing its saved induction pointer. Actual level/table
bounds, all embedded frames, PAC/canary protections, late-fixmap barriers and
live init-memory extents are checked. The last trace returns before the actual
SYSTEM_FREEING_INITMEM store and free path.

All **380 actual linked-C cases** pass, including first/middle/last slots,
short-history/span/wrap boundaries, CPU guards, both mapping failures, drift
before stores and before commit, interrupted writes, invalid ordinals/phases,
and later eligible events after a failed mapping. No write escapes its slot,
declared init state or stack; mapped APIs are mocked only in this instruction
suite.

All **11 real-MMU fixtures** pass with the exact physical candidate initramfs.
Normal EL1/EL2, page-crossing and separate timing runs recover all 3,656 events;
short history recovers six; first header/slot mapping failures recover 3,655;
both drift cases recover 1,827; invalid header recovers none. Every correctness
fixture counts each event exactly once in the declared execution order through
the final pre-free call. Actual PID1/reaper/CPU/preemption/IRQ context uses fresh
compiler/config layout derivation and PID0/PID2 calibration. The 512-page
no-map hole, adjacent positive controls, Normal-NC/XN temporary attributes and
complete prior mapping-state restoration pass at the selected points.

Timing runs use no per-record debugger breakpoints. With the same new physical
initramfs and QEMU shape, one sample per Image/EL measured the pre-basic through
post-async region at 1.313/1.326 seconds for retained V7 and 1.474/1.465 seconds
for V8. The observed difference is 0.161/0.140 seconds. This is a small H0
comparison with host/VM variability, not a physical watchdog-margin guarantee
or an isolated mapping microbenchmark. It provided no demonstrated need to
replace the transient mapper.

The separate full RAM-userspace-PID1 VM passes in 3.902 seconds, with its own
VM initramfs and invalid-header skip path; its offline raw recheck passes.
Loader tests pass 20 actual-instruction cases, 1,051 copy cases and real
EL1/EL2 entry with EL3 refusal. Two boot-v4 images and boot-only AP archives are
identical. H0 does not prove physical g0q boot, coherency, retention or USB.

All **94 focused mainline host tests** and touched-Python compilation pass.
The real durable retention writer/reader reopens a maximum 4 MiB synthetic
capture containing 32,768 records within the existing 2 MiB result bound.
Grouping duplicate offsets preserves them without turning counts into boots.
Admission rejects old two-site evidence, missing cases, repeated/reordered
events, missing mapping attributes and counting-instrumented timing claims.
The new decoder dependency is capability-bound but remains outside original-A
recovery prerequisites. The full PID1 VM records that dependency and preserves
historical capture shapes.

Current decoding reproduces all historical V1–V7 captures unchanged:
`12 / 12 / 10 / 12 / 10 / 5 / 5` records. V8 finds no V8 record in ML009's raw
capture. Consumed task/proof/journal bytes remain unchanged. A private historical
recheck initially used the wrong raw-module import name; correcting the import
completed the same host-only check without changing evidence or device state.

Past-failure applicability: ABI binds the actual compiler/layout/PREL32 shape;
WIRE/SEMANTIC preserve prefix-last and positive-only interpretation; PERSIST
tests the actual maximum durable projection; ROUTE/ARTIFACT bind the fresh
loops, frame array and physical-initramfs fixture; HOST retains complete build
and VM inputs/outputs; RETURN keeps original-A ownership, health and no replay.

## Interpretation and remaining work

An entry record proves the point before dispatch, not callback-body entry. A
return record proves dispatch returned, not return-code success, matched
hardware, completed probing or async work. Later fixed milestones prove their
named returns; they do not prove successful initramfs unpack, global quiescence,
userspace exec or USB. Low milestone IDs mean that the highest numeric event
is not necessarily the deepest overall progress.

Each intact record is at-least-once evidence for this candidate's attempts.
Missing returns cannot identify a culprit, last attempt or reset cause. Full
coverage can reduce avoidable physical trials; loss, async interference or a
large callback's internal work may still require a targeted follow-up.

Final independent review returned **PASS_GO with no remaining findings**.
It verified 73 current source pins and frozen copies, 359 artifact/raw pins,
38 capability sources, 44 backend sources and two unchanged worker sources.
The codec-dependency/recovery exclusion and full-VM no-map/provenance findings
were corrected and independently rechecked. It independently decoded the final
table, complete frame array, all 11 VM byte outcomes and historical captures.

The new V8 capability and backend v19 receipts select that reviewed closure;
the existing ordinary-terminal worker is connected with unchanged loaded
source identity. Production image qualification, task preparation from closed
ML009, and current fixed preapproval D0 passed. Seven complete rooted Android
health captures rederive correctly. No approval file, grant or operation exists.
If the five-minute readiness freshness expires before grant opening, the same
fixed read-only readiness is refreshed; effect-time checks still apply.
Current production projection also reproduces closed ML009 offline with
acquisition blocked and its protected proof/journal bytes unchanged.

Any physical run requires the mainline policy's separately returned exact
one-operation approval, actual attendance and usable original-A Download
recovery. No old grant or H0 result supplies that authority.

| Receipt | SHA-256 |
| --- | --- |
| Marker qualification | `02fad8378a0c2d7db78a77af727bc8867e34205037345dc78327fe2b459d9804` |
| Independent final review | `0e82682f0bf25ab5224a0cd4d5ac6f8479606151ba964796be5e6b763a1f2dc9` |
| Exact prepared task | `627522f1247ee96ec32cf700a22ff7407c0f53014b3baaf3b44868a6477477d8` |
| First fixed readiness | `240b7ab7030907a67a7e9bc3fbacc430df7368a556db9b4a8a0c3a42c996dc0b` |
| Preparation summary | `c9925931ddbd74c46275891257c2815216274943576f6ae4f2439465fdc6fa54` |

Private evidence: `workspace/private/outputs/s22plus-mainline-ml010-h0-20261030-1/`.
Discussion: `workspace/private/outputs/s22plus-mainline-ml009-next-discussion-20261030-1/`.
All four external-model calls completed without failure/refusal/fallback.
Claude reported four uncached input, 33,145 cache-creation input and 27,868
output tokens, including 19,677 thinking tokens; its CLI list-price equivalent
was USD 0.822536, not subscription billing. Argon reported 48,549 input and
25,709 output tokens, including 15,916 thinking tokens, for 74,258 total;
cost was unavailable. Claude five-hour utilization snapshots moved from 0%
to 3%; fresh-session Argon weekly remaining snapshots moved from 68.64% to
66.40%. These account-wide changes are not exact per-call attribution.
Before/after snapshots and token accounting are preserved in the private
append-only usage ledger without credentials.
