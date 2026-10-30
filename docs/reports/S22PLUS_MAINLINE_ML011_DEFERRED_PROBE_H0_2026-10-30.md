# S22+ ML011: bounded deferred-probe observations

Preparation checkpoint: **READY_H0_AND_CURRENT_D0_NO_EXPERIMENT**.
The subsequently approved [ML011 run](S22PLUS_MAINLINE_ML011_RUN_2026-10-31.md)
is consumed and closed healthy. It records the first deferred-probe phase and
the TLMM-associated pre-callback point; callback return and physical USB remain
unproved. The preparation statements below, including absence of a grant,
describe the historical checkpoint before execution.
No ML011 grant or experimental operation exists. ML010 remains consumed and closed
healthy; its absent return record identifies no culprit. A90 and S20+ are
untouched.

## Selected change

The operator requested the established analysis-to-experiment workflow and had
asked to consolidate useful observations into fewer physical trials. Two-round
Claude Opus 5.5 / Gemini 4 Argon High discussion and independent source review
supported observing the deferred-initcall body and worker/callback points in
one prospective candidate. Neither source nor ML010 evidence justifies a
corrective driver/DT suppression yet.

V9 uses the same 128-byte static integrity frames, exact Samsung log slice,
unchanged header, latched window, prefix-last commit and temporary Normal-NC
mappings. Its **3,914 slots occupy 500,992 bytes**, with at most **532,304 log
byte stores** per kernel-init attempt, below the retained 512-KiB/557,056-store
ceilings. There is no extra header frame or header write.

The candidate contains:

- Six fixed PID1 milestones and 84 entry/return observations for the eight
  level-first entries and ordinals 1,791–1,824. The fresh final ELF independently
  resolves all 1,825 PREL32 entries and their boundaries.
- Ten deferred-function milestones and four phase-specific worker entry/return
  observations. The two phases are sampled at hook entry, not inferred from
  workqueue trigger provenance.
- Five points per phase and OF-node bucket: pre-PM-move/bus-probe, bus-probe
  return, pre-`device_set_driver`, and the selected callback's pre/post points.
  The exact DTB yields 379 compatible/reg nodes and ancestors, plus distinct
  no-OF and unlisted-OF buckets. This is not a complete device/driver identity
  census; aliases and noncatalog associations remain explicit limitations.

Device hooks arm only inside `deferred_probe_initcall`, so earlier probes do
not consume their events. The first admitted entry attempt obtains a local
phase/node return token; nested or later entries sharing an event obtain none.
The return does not reread phase or node identity. Failed mapping consumes the
attempt too. Repeated attempts within a phase are not fully observed.

The persistent dispatcher uses process-context and sole-boot-CPU guards,
preemption exclusion, and a live init-code pointer. The same exclusion clears
that pointer at deferred-initcall exit even after recorder failure. Direct
PID1 tail markers remain available until final pre-free cleanup. Node references
are acquired/released outside exclusion. The exact forced command line,
delivered DT and enabled-caller analysis exclude competing IRQ early-map and
CPU-onlining paths during this window. This is not inferred from a CPU count
alone. No driver order, callback result, watchdog, storage or firmware behavior
is changed. The configured ten-second timeout pass may occur after disarm and
is outside the window.

## Artifact and validation

The changed kernel paths are `init/main.c`, `drivers/base/dd.c` and its generated
header. Focused ARM64 compilation and the complete build have no warnings,
errors or section mismatches. The Image SHA-256 is
`95e515527dafcee387dd85ac963614f20945e5d7142e72a1f4afdca9938bb706`.

The actual linked writer passes **361** guard, span/wrap, map-failure, sticky
drift, interrupted-store and seen-event cases. An independent actual ARM64
fixture passes **16** hook cases, including first-entry tokens, nested shared
nodes, cross-phase return, no-OF versus unresolved catalog pointers, disabled
recorder disarm, balanced reference calls and every hook operation after the
actual init range is unmapped. Its CPU, OF and mapping APIs are mocked;
it does not claim a live scheduler or real MMU.

The exact physical Image/initramfs also passes **11 real-MMU fixtures**. Normal
EL1/EL2 traversal observes all 104 fixed/sparse events once, including actual
workqueue-thread execution. Page-crossing, short-history, invalid header, both
map failures and both drift phases preserve the declared byte window and
restore mappings. Page-table walks show no linear alias over all 512 reserved
pages, with adjacent positive controls and Normal-NC/XN temporary mappings.
Same-build offsets calibrate PID1 and worker contexts. Natural QEMU traversal
has no per-node deferred callback records; those selector/token paths are
covered by the independent instruction fixture, not claimed as hardware probes.

The catalog fixture adds disabled path skeletons without altering existing
QEMU node properties. The first check exposed removal of one memory skeleton
before Linux C setup. Captured entry/live DTBs establish that exact difference;
the corrected checker joins every lookup to the actual incoming DTB, obtaining
378 references and one explicit unresolved memory path. This is a fixture
correction, not a candidate change or a physical g0q lookup result. Original
failed fixture outputs remain retained. Separate runs without event counters
measure 1.591/1.628 seconds from catalog preparation through final cleanup;
these are H0 durations, not physical watchdog-margin guarantees.

The separate RAM-userspace-PID1 VM passes in 4.662 seconds, with a complete raw
capture and successful offline recheck. Loader qualification passes 20 linked
instruction cases, 1,051 copy cases, actual EL1/EL2 entry and EL3 refusal.
Two boot-v4 images and boot-only AP archives match. All **101 focused host
tests** and **13 actual-producer admission negatives** pass. Historical V1–V8
captures decode unchanged with record counts
`12 / 12 / 10 / 12 / 10 / 5 / 5 / 12,208`; the new format finds no V9 frame in
ML010's raw capture. Consumed proofs/journals are unchanged.

The actual retention writer/reader also durably reopens a maximum 4-MiB
synthetic capture with all 3,914 event labels and 32,768 records. Its complete
result occupies 878,662 bytes within the existing 2-MiB limit. This uses a
distinct synthetic owner/key and blocks acquisition during offline reopening.

An early checker assumed the DTB manifest also contained a size field; it was
corrected to consume its actual path/digest schema. The source review also
clarified `post-timeout-schedule-call`: the marker proves return from the
scheduling call, not its boolean result. Original producer source copies and
pins are retained; exact configuration/generated-header equality proves this
label correction changed no runtime bytes. Artifact and checker provenance
remain separate. These H0 corrections introduced no physical retry.

Past-failure applicability: ABI uses the actual compiler/layout/PREL32 shape;
WIRE/SEMANTIC retain prefix-last and positive-only interpretation; PERSIST
checks a maximum grouped capture against the existing durable-record bound;
ROUTE/ARTIFACT join the fresh Image, generated catalogs, real worker contexts
and physical initramfs; HOST preserves failed and successful producer outputs;
RETURN keeps the new decoder outside original-A recovery prerequisites.

## Interpretation and remaining admission

A pre-call record proves the point before dispatch, not callback-body entry or
the recording helper's subsequent return. A post-call record proves some call
returned, not success. Static records do not establish same-boot order/pairs,
complete retries, the last attempt, a failure location, reset cause or unique
device/driver identity. Missing evidence is not a causal diagnosis. Physical
RAM PID1 and USB remain unproved.

Final independent review returned **PASS_GO with no unresolved findings**. It
verified 78 current/frozen sources and 514 artifact/raw pins, independently
redecoded the ELF, frame arrays and all VM raw regions, and repeated an EL2
fixture with byte-identical complete log contents. The V9 capability and
backend-v20 receipts bind that closure; the unchanged ordinary-terminal worker
remains connected and uses a fresh reviewed backend per request.

Production image qualification and task preparation from closed ML010 pass.
One fixed preapproval D0 invocation completed with seven successful, empty-stderr
rooted-Android health captures, rederived through the actual health consumer.
No approval, grant, experimental operation or unresolved F1 owner exists.
The current production decoder also reproduces closed ML010 offline with
acquisition blocked and all 22 protected proof/journal files unchanged.

These readiness facts describe this preparation checkpoint. If its five-minute
freshness expires before grant opening, the same fixed read is refreshed;
effect-time checks remain mandatory. A physical run requires the policy's
separately returned exact one-operation approval, actual attendance and usable
original-A Download recovery. No prior grant supplies that authority.

| Receipt | SHA-256 |
| --- | --- |
| Marker qualification | `5f3a193cea245fbb3ee24a6305e1b4b326ee3becd180c081ba4362e067aaa723` |
| Scoped source review | `5e560bbc64595534593bfa471dd79f47015ab739a6c801de27aa1d32f75841d6` |
| Frozen-import hook fixture | `69d4920a8aba60b229adac1200393df1aba1f55b80097a662facc93f0b99811e` |
| Real-MMU suite | `38bf412b86f61c8f1cdce9293429feac6656c566aaac32285a49629469c0651e` |
| Final independent review | `fc525648fc8f8e6d18f21244e088b867c4a8461583acf113a4198568dd0d197e` |
| Exact prepared task | `1a1cc7e269d06eb2f9e1b0a5c682d2e16285771e7d9b7a68b75fad2102a148ec` |
| First fixed readiness | `c7786a7f0e14897005d5b729b7aed39f4e00b2efcecc5bf05e530749d3a581b5` |
| Preparation checkpoint | `cebbf2117ff0e9ca633fa14f8abeeaedecdc03795dc9df76098a8306d4b39033` |

Private artifacts: `workspace/private/outputs/s22plus-mainline-ml011-h0-20261030-1/`.
Discussion: `workspace/private/outputs/s22plus-mainline-ml010-next-discussion-20261030-1/`.
All four external calls completed without failure/refusal/fallback. Claude
reported four uncached input, 21,272 cache-creation input and 34,925 output
tokens, including 28,054 thinking tokens; its CLI list-price equivalent was
USD 0.868692, not subscription billing. Argon reported 43,685 input and 36,772
output tokens, including 29,632 thinking tokens, for 80,457 total; cost was
unavailable. Account-wide snapshots moved from 0% to 4% Claude five-hour used
and from 66.40% to 63.36% Argon weekly remaining. These are not exact per-call
quota attributions. Private before/after records preserve the distinction.
