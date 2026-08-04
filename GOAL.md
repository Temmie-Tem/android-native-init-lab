# Goal: S22+ repeatable native PID 1

Build a repeatable path from the FYG8 Android vendor boot chain and
source-matched kernel to a custom static `/init` running as PID 1, then grow
that entry point into a minimal observable and recoverable runtime.

This file reports current S22+ state and grants no authority. The binding
layers are `AGENTS.md`,
`docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md`, and the selected
shared process documents. A90 state and authorization remain separate.

## Current Frontier

P3.01 is the latest closed live unit. Its boot-only candidate and exact Magisk
rollback each transferred exactly once with no replay. The operator observed a
normal candidate boot with no boot loop. A transient USBFS re-enumeration race
during the physical rollback handoff stopped the first execution safely;
durable `--recover` performed only the preapproved rollback and final checks.
The transaction is `CLOSED`, `recovery_required=false`, and exact rooted FYG8
Android health passed. A90 received zero commands.

The two byte-identical 2,097,136-byte post-rollback reads contain one exact,
integrity-clean P3.01 pair. Generation 106 is detail `0xD70`,
`probe-ok-start-rc0-ingress-device-other-only-link-0`: the probes armed,
`__dwc3_gadget_start()` returned zero, both EP enable calls ran, trace/profile
loss stayed zero, cleanup passed, one or more non-RESET/non-CONNECT_DONE device
events reached the raw dispatch boundary, and link state remained zero.
Generation 107 is detail `0x5003`, final-state index 2: UDC `not attached`,
speed `UNKNOWN`, `COREIDLE=1`, and `SUSPHY=0`. The result explicitly has
`subtype_claimed=false`; P3.01 did not retain which other event type occurred.

Immediate H0 comparison found the cause in the P3.01 userspace contract, not a
new device-time state. The subtype path is guarded by hard-coded expected final
detail `0xE06`, which decodes to `attached/UNKNOWN/COREIDLE=1/SUSPHY=0`.
P3.00 retained `0xE02`, and P3.01's decoded legacy final tuple maps to that
same `0xE02` value: the campaign's established
`not attached/UNKNOWN/COREIDLE=1/SUSPHY=0` tuple. The mismatch therefore forces
the designed final-drift branch before subtype encoding on the very state that
P3.01 was intended to refine. The retained record is valid and device health
is unambiguous, but the subtype objective is `NO_PROOF_OBSERVER`.

The narrow userspace-only correction is now host-complete. The expected final
detail is derived from the canonical P3.00 encoder as `0xE02` instead of copied
as a literal. Generated C uses that same value at one definition site, executes
the known/unknown subtype and all four bucket branches at `0xE02`, and retains
the final-state and ingress-mismatch drift branches. The fixed P3.00 Image and
15-probe descriptor are unchanged; no kernel or Full-LTO rebuild occurred.

The new immutable overlay intent has semantic SHA-256 `996f0885...`; the new
static `/init` is 66,384 bytes at SHA-256 `17eae28a...`. Independent candidate
A/B packages are byte-identical at AP SHA-256 `d281bef8...`, each containing
only `boot.img.lz4`, and both recover the unchanged Image SHA-256 `01457240...`.
The static checker passes, the combined userspace/inherited/sidecar regression
passes 33/33, and the ready-manifest rehearsal reproduces SHA-256
`dcb9a96f...`. The contract-required narrow independent check reviewed only
the changed selection closure and package binding and returned `PASS_GO` with
no finding. No device command or A90 action occurred.

The next step is fresh connected D0 preparation against
`s22plus_fyg8_p301_r1_process_v2_ready_1.json`. If the closed P3.01 retained
record is still the baseline, one attended normal Android reboot may rotate it
before a second clean D0. Do not reuse the consumed P3.01 transaction or
candidate.

## Selected Bounded Unit: P3.00 Event-Ingress/IRQ Attribution (Closed)

The source and existing Full-LTO evidence close the design question. The
actual P2.98 A/B `vmlinux` pair is byte-identical and keeps
`dwc3_interrupt`, `dwc3_thread_interrupt`, `dwc3_process_event_buf`,
`dwc3_process_event_entry`, and `dwc3_check_event_buf` out of line. Linked
control flow directly connects top-half return `w0`, threaded processing, raw
event dispatch, and the RESET/CONNECT_DONE handlers. The inlined
`dwc3_gadget_interrupt` helper is explicitly not a probe target.

P3.00 will add one noinline built-in snapshot beside the existing successful
run-stop snapshot. Its eight arguments carry the exact `dwc` and event-buffer
pointers, DEVTEN, GEVNTSIZ, GEVNTCOUNT, and the event buffer's length, count,
and flags. The readback is immediate rather than terminal: count zero means
only zero at that instant, while count nonzero plus no top-half proves a
strictly narrower IRQ-delivery boundary.

The exact Waipio tree has one `dwc3@a600000`, so entry/return pairing may rely
on strict nonnesting only while every later pointer matches that one snapshot.
The P2.98 A/B `vmlinux` contains several generic role/VBUS helpers, but the
active S22+ `vbus_active` and notifier state lives in external `dwc3-msm.ko`.
None is a sound 16th event in the candidate window, so one slot remains spare.
Before a future type-C/extcon/PHY follow-up, H0 must first prove its exact target
is built into `vmlinux`; otherwise it repeats P2.94's pre-device delivery stop.

The H0 implementation and static validation now pass. The fresh
transform/schema/streaming parser/decoder/source contract preserves every
inherited P2.98 payload source byte. Its host C fixtures execute the generated
setup, trigger, recording-window, cleanup, pointer, raw-mask, line/header
parser, and profile-relation paths. Ring-stat parsing, final aggregate stream
counts, and profile `nmissed` readback are source-order and integrated-compile
validated but are not claimed as executed fault branches. The generated patch
clean-applies to the exact inherited source and two static AArch64 `/init`
links are byte-identical. The
verdict is `PASS_P300_EVENT_INGRESS_IRQ_IMPLEMENTATION_HOST_ONLY` and the
focused telemetry verdict is
`PASS_P300_EVENT_INGRESS_IRQ_TELEMETRY_CLOSURE_HOST_ONLY`.

The first independent pass found and stopped an unclosed profile/recording
window plus preliminary build adapters whose qualification module did not yet
exist. The window now opens and closes without a probe-active/tracing-off gap
on the no-cutoff path, its cutoff-close race states are fault-tested, and the
preliminary candidate/build/package adapters were removed from this core
closure. The final independent review returned `PASS_GO` for the exact
remediated core. It qualifies this unchanged observer capability rather than a
candidate run and is reusable while its execution-critical bytes and hazard
assumptions remain unchanged; it is not a per-candidate review gate.

The candidate/build/qualification and exact same-attempt USB-sidecar closure
are now complete. Canonical Tier-1 intent remains unchanged at 159/159 source
keys. Two clean Full-LTO builds reproduce the exact Image and linked vmlinux,
and two boot-only packages reproduce an AP containing only `boot.img.lz4`.
The candidate AP SHA-256 is
`1d80017becd5974f9c64e25ecd8b9d800d001a49e165e6949822d692b58d8d7b`;
the exact Magisk rollback AP SHA-256 is
`d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`.

The changed Process-v2/live-sidecar capability passed independent review at
bundle SHA-256
`633483479729112c46fc3bee404707957868b2a482b8c3454c6c68822f6e8a8c`
and execution-closure SHA-256
`1edd315f40bd6148e99203cbd2f49131a65f76eb0d21827821067583b20d6166`.
Its fault closure proves that observer witness or shutdown failure cannot block
the mandatory rollback, and interrupted observer descendants are reaped before
another attempt.

The first connected preparation stopped before F1 arm on a historical retained
marker. One attended normal Android reboot rotated that baseline and returned
the exact rooted FYG8 health. A fresh D0 then passed with zero candidate-family
markers and created the reopened prepared binding
`1ec284f2213a71c56de2afa1c202864cef8fa6638348f2f63a03d4dc563d8ad1`
under
`workspace/private/runs/device-action-f1-live-v2/p300-ready1-prepared-20260804-2`.
That exact binding has now completed one attended Process-v2 transaction. The
operator observed a normal candidate boot with no loop. Candidate ACM timed
out, but the two retained slots are valid and byte-identical across both final
reads. Generation 106 reports `DEVICE_OTHER_ONLY` at link state 0 with exact
probe setup, gadget-start return zero, two EP0-enable hits, verified streaming,
zero ring loss, zero missed return probes, and no RESET or CONNECT_DONE.
Generation 107 remains not-attached/UNKNOWN/COREIDLE=1/SUSPHY=0.

The host USB sidecar is `UNKNOWN` and is not used for a host-visibility
conclusion. H0 replay shows that both monitors were alive before the requested
stop, captured without truncation, and then exited zero after handling SIGTERM;
the reviewed verifier overconstrained clean shutdown to return code `-15`.
This host-only mismatch does not invalidate the device-retained result and does
not justify another F1.

Post-live H0 source analysis proves that P3.00 discarded the exact subtype:
the raw trace carried it, but the parser folded every non-RESET/non-CONNECT_DONE
device event into one bit. A bounded live prerequisite then read
`GSNPSID=0x33313130`; its high half is the exact `DWC31_IP` value `0x3331`.
Consequently the DWC3-only pre-2.50a predicate is false, LINK_STATUS_CHANGE is
not enabled, and the DWC3-only pre-2.30a predicate is also false so SUSPEND is
enabled. The unresolved set is exactly DISCONNECT, WAKEUP, SUSPEND,
ERRATIC_ERROR, CMD_CMPL, and OVERFLOW. DISCONNECT is the best-fitting
hypothesis, not a proof. CMD_CMPL is source-disfavoured because the exact
device-generic-command writer polls `DGCMD.CMDACT` without setting
`DGCMD.CMDIOC`. EventOverflow, if present, is separate from the already-proved
zero ftrace-ring loss and must be reported as controller-event incompleteness.

## Closed Bounded Unit: P3.01 Subtype Refinement Attempt

P3.01 is a userspace-only subtype refinement over the
exact qualified P3.00 kernel Image and unchanged 15-probe descriptor. The fixed
Image accepts wide details only as `FAILURE`, excludes `0x4000`, `0x5000`, and
`0x6000`, and becomes terminal after the first non-progress write. It separately
contains all 176 exact progress rules at `0xD00-0xDAF`; the later false tuple
stub does not make those earlier exact rules unreachable. P3.01 must therefore
keep A as the existing 11-family/link progress detail and use B as the terminal
wide-band detail, not the reverse.

For an integrity-clean `DEVICE_OTHER_ONLY` repetition with the inherited exact
final tuple, B uses `0x4001 + (((mask - 1) * 16 + first_info) * 4 + bucket)`.
The six-bit nonzero mask has 63 values, `first_info` is the first other device
event's low nibble, and `bucket` is `1`, `2-3`, `4-7`, or `8+`; all
`63 * 16 * 4 == 4032` values occupy exactly `0x4001-0x4FC0`, leaving 63 valid
codes in that band. This family itself implies the inherited
not-attached/UNKNOWN/COREIDLE=1/SUSPHY=0 final tuple. A changed valid final state
instead uses an exact 132-value `0x5001 + state_index` family and intentionally
does not claim a subtype; observer contradictions use the `0x6001` band. This
preserves information on drift without pretending that two retained slots can
carry both full Cartesian products. DEVTEN is now fixed by measured DWC31, and
the three immediate queue booleans are not retained in P3.01.

This requires reproducible userspace/boot-only packaging, not another Full-LTO
A/B. Bundle the future-only clean-zero sidecar shutdown correction into the same
implementation/review unit so it cannot consume a separate F1.

The P3.01 H0 implementation now satisfies that contract. Generated payload
comparison changes only `p290_e3_runtime_include`; the candidate patch,
checkpoint client, 15-probe descriptor, and exact qualified P3.00 Image remain
byte-identical. Runtime and schema hard-bind A to ordinal 105 with outcome
`PROGRESS`, verify the 105 -> 106 -> 107 checkpoint transition, and reserve
`0x4FC1` for any undefined/disabled device-event subtype before the guarded
`mask - 1` arithmetic. Types 8 and 12, a known/unknown mixture, all four count
buckets, a synthetic zero-mask contradiction, and wrong starting generations
104/106 execute in the generated-C closure.

Nine P3.01 payload `SOURCE_KEYS` were printed and hashed before the overlay
intent. The intent preserves the Image-bound P3.00 run ID and no key changed
afterward. Two static userspace links and two complete candidate packages are
byte-identical. The candidate AP SHA-256 is
`35a1621716702ef553c2db83b8fbb075543c37a4b56507b1fa0c4ef86668c41b`;
it contains only `boot.img.lz4`, injects zero modules, and reuses fixed Image
SHA-256 `01457240881b432f725b0f2d795813c38ef7cca4365633f9b0fc7c3a62744a3f`.

The shared sidecar verifier now accepts direct SIGTERM death or clean zero
exit after the recorded SIGTERM request while retaining every prior
alive-before-stop, ownership, no-error, no-truncation, receipt, and same-window
requirement. Focused independent review returned `PASS_GO` for the exact
current P3.01 overlay, decoder/model, boot-only packaging, and sidecar change
set. Process-v2 candidate/static/live binding remains; the artifacts and
capability review alone grant no F1 authority.

One later adversarial review found that the P3.01 static checker could accept a
self-consistent substituted P3.00 result and the same A build in both slots.
The repaired checker now pins the exact 80,509-byte parent result and exact
125,025-byte pre-LTO qualification, requires the canonical A/B directories,
distinct directories and artifact inodes, and validates the complete
byte-identical, linked-audit, adapter, build-header, and qualification
identities. The reproduced bypass is rejected. Nine focused tests, the full
static replay, and ready-manifest rehearsal pass; static output remains
`de4e3b7e...` and the ready manifest remains `eb536d44...`. Independent
rereview returned `PASS_GO` with no residual blocker.

The exact firmware metadata used to derive the candidate plan was also
rechecked against stock. The planner already pins and parses first-stage
`modules.load` (140 rows), recovery `modules.load` (446 rows), and
`modules.dep` (441 rows), recursively closes hard and soft dependencies, and
uses stock order only as a tie-break. A fresh exact-device D0 found a distinct
356-row late `/vendor` list and 482 currently loaded stock modules; every one
of the candidate's 60 runtime names was loaded in stock. Stock also loads
`usb_notifier_qcom`, but the inherited explicit `mode=peripheral` path already
proves `vbus_active`, `B_SESS_VLD`, start-peripheral, and HS-PHY notify-connect
without that automatic Type-C bridge. No module-plan change is selected.

The P3.01 candidate and exact rollback each transferred once. The transaction
is durably `CLOSED`, final rooted FYG8 health passed, recovery is not required,
the sidecar left zero owned processes, and A90 received zero commands. The
retained pair is `0xD70/0x5003`: it repeats integrity-clean
`DEVICE_OTHER_ONLY` at link zero, then records the established not-attached
final tuple as drift because this implementation incorrectly selected `0xE06`
rather than P3.00's exact `0xE02` as its subtype precondition. No exact subtype
is claimed from this run.

The full design and limitation statement is recorded in
`docs/reports/S22PLUS_FYG8_POST_P298_EVENT_INGRESS_IRQ_ATTRIBUTION_H0_2026-08-04.md`.
The implementation receipts and remaining gates are recorded in
`docs/reports/S22PLUS_FYG8_P300_EVENT_INGRESS_IRQ_IMPLEMENTATION_H0_2026-08-04.md`.
The reusable capability-review receipt is recorded in
`docs/reports/S22PLUS_FYG8_P300_EVENT_INGRESS_IRQ_INDEPENDENT_REVIEW_2026-08-04.json`.

## Closed Bounded Unit: P2.98 Live Attribution

P2.98 is the fresh successor contract
`s22plus-fyg8-p298-gadget-start-event-attribution-v1`. Its host implementation
and canonical Tier-1 intent are complete. The reproducible static userspace
also passes. Pre-Full-LTO qualification now passes on the qualified build host:
the focused closure is 130/130, the shared Process-v2 regression is 110/110,
and 33,662,164,992 bytes physical RAM, 12,884,893,696 bytes swap, and
37,085,384,704 bytes free disk satisfy the mandatory resource predicates. The
receipt has SHA-256
`f3533d20ef3edc5c4feaf410296492820138dcd2c56861ee81be02fca78b89eb`
and recorded `full_lto_started=false` before either build. Independent
execution-code rereview returned `PASS_GO` for the exact Tier-2 repair with no
finding, and the current common-policy and S22+ document receipts were rebound
before build.

Two clean Full-LTO builds now close the host unit. Both produced the same
41,490,944-byte `Image` at SHA-256
`689d71487788777e28efbdb48eb783462dde271f5af5a8ba0d2aa6348541ce87`
and the same 476,979,440-byte `vmlinux` at SHA-256
`3067680949754f7c5bd418136bc8c21cc9522f55aa8394a666fa0b21e1a2968d`.
The official result is
`PASS_P298_TWO_CLEAN_BUILD_REPRO_AND_LINKED_AUDIT_HOST_ONLY`: all six compared
artifacts are byte-identical, random and absolute host clang paths are absent,
and 138 clang-resource paths are mapped beneath `/private-repo`. No device
action is part of this bounded unit.

This continues the **Gadget-Start Return Host Implementation (H0)** lineage:
the entry plus signed `$retval:s32` pair remains subject to a mandatory
post-Full-LTO A/B disassembly audit, now extended with EP0 and event
attribution.

The bind descriptor now contains 12 events: the inherited seven, one
`__dwc3_gadget_start()` entry/return pair, one entry-only
`__dwc3_gadget_ep_enable()` event, and controller-attributed RESET and
CONNECT_DONE handler entries. The parser requires the exact PID/counter order,
the exact controller pointer, zero missed events, and exact equality between
trace records and per-event profile hits.

The result contract is information-bearing on every valid observer outcome:

1. A negative gadget-start return plus one EP-enable entry proves the EP0-OUT
   command boundary; the same return plus two entries proves EP0-IN. The exact
   source restricts expected errno to `-EINVAL`, `-EAGAIN`, or `-ETIMEDOUT`.
2. A zero return is accepted only with exactly two EP-enable entries. The
   observer stays active through final sampling so the same run records RESET
   and CONNECT_DONE presence plus the link state.
3. The final A/B family itself implies successful probe setup, one returned
   gadget-start call, `start_rc == 0`, two EP-enable entries, exact read/profile
   agreement, and verified cleanup. Earlier setup checkpoints may be overwritten
   safely by the adjacent two-slot terminal publication.
4. Registration failure, no reach, no return, positive return, hit-count
   contradiction, parse/readback failure, cleanup failure, and profile mismatch
   remain distinct retained details.

P2.96 is the explicit historical no-probe behavioral control. Do not spend a
dedicated F1 control unless unexplained prefix/tuple drift, probe-provenance
contradiction, a new health anomaly, or a new hazard class reopens that choice.
Probe installation is evidence of installation only; it does not by itself
exclude observer effect.

The mandatory linked proof disassembles both actual Full-LTO images. It must
show all four probe targets out of line, two ordered and checked EP-enable
calls, the pullup caller discarding gadget-start `w0` before direct run-stop,
and the resume caller immediately testing the signed return. Inline, clone,
tail-call, missing, return-consuming, or A/B-divergent forms fail closed.

The pre-intent freeze covers 136 Tier-1 source keys and reports
`CHANGED_KEYS=[]`. The one canonical intent and static AArch64 userspace are
derived. Two independent links reproduce the 66,384-byte `/init` at SHA-256
`e35e2a1d978d2c9f4af0d6b3ac254239324c6f503312107b1a5a89c91f702daa`
and the 720-byte child at SHA-256
`9a57b30aa3fb08ee0aab4d045d2805dd36875bb80bcba7b0b6606f619df71639`.
The final direct P2.98 suite passes 20/20 and the whole focused closure passes
130/130. A read-only audit of the historical P2.96 A/B pair passes the
new six-function call-shape checks. The fresh P2.98 A/B pair independently
passes the mandatory linked proof: all probe targets remain out of line, the
ordered two-call EP0 enable chain is retained, pullup discards gadget-start
`w0` before direct run-stop, and resume immediately tests the signed return.

## Ordered Execution

1. Keep every P2.96 `SOURCE_KEY` immutable and retain P2.96 as the historical
   behavioral baseline.
2. Freeze the complete P2.98 Tier-1 set before deriving its one canonical
   intent. Do not edit a Tier-1 byte afterward.
3. Reproduce the static AArch64 userspace, replay inherited focused gates, and
   bind the exact linked-audit metadata into pre-Full-LTO qualification.
4. Apply the runbook's physical-RAM, swap, disk, toolchain, source, and clean
   worktree gates before Full-LTO A/B. The qualified build host and shared
   110-test regression now pass; retain their exact receipts and never bypass
   either gate.
5. Retain the fresh independent `PASS_GO` for the exact reviewed
   trace/schema/parser and postbuild closure only while its named hashes remain
   unchanged. Fresh Full-LTO closure is complete. A later unit must
   independently satisfy package, exact rollback, D0, attended F1, recovery,
   and final-health gates. Never reuse the consumed P2.96 run.

Trial policy adds no per-candidate approval, but the legacy runner still
requires its fresh immutable token until aligned. The consumed P2.96 token,
prepared binding, journal, and candidate attempt are never reusable.

## P2.98 F1 Execution Result

P2.98 passed the last read-only boundary before F1. The new
Process-v2 promotion and ready-manifest adapters passed an exact nine-file
independent review after two fail-closed findings were repaired. The immutable
ready manifest is
`workspace/public/src/device-action/manifests/s22plus_fyg8_p298_process_v2_ready_1.json`
at SHA-256
`369b9037dd394bdea36bec7d1a207ac425c416cb46a83572d2f1562c3e5a7130`.

The first connected preparation correctly stopped on one historical retained
long-family record. One reviewed, attended D1 normal reboot then rotated that
baseline exactly once and returned exact rooted FYG8 health with a changed
boot ID. It issued no Download transition, Odin call, payload, partition
transfer, or command to A90.

The fresh production `--prepare` passed with a 2,097,136-byte clean
`/proc/last_kmsg` read, zero related-family records, and exact candidate,
rollback, target, manifest, and execution-closure binding. The prepared run is
private under `workspace/private/runs/device-action-f1-live-v2/`; its approval
binding SHA-256 is
`34df56c1527aafec28b4ef5e933661c89aa3e255a1daa4dd91c68639569d2613`.
The attended F1 consumed that binding exactly once. Candidate observation timed
out without an ACM endpoint, then the physical Download handoff encountered a
transient USBFS re-enumeration identity failure. Durable recovery continued
without candidate replay. Exact rollback transferred once; a second transient
host endpoint measurement failure occurred after the durable rollback. A final
recovery reopen performed only the remaining health and retained-evidence
reads, never another transfer.

The durable transaction is `CLOSED`: candidate/rollback transfer accounting is
1/1, `recovery_required=false`, and exact rooted FYG8 final health passed. The
two final 2,097,136-byte retained reads are byte-identical and prove
`start_rc=0`, two EP-enable entries, event mask zero, link zero, then
not-attached/UNKNOWN/COREIDLE=1/SUSPHY=0. A production reopen validates the
complete journal, transfer receipts, timeline, final health, and retained
semantics. A90 received zero commands.

The downstream H0 design is now complete and selects P3.00 event-ingress/IRQ
attribution. Do not claim a specific run/connection, PHY, or VBUS cause from
that design. No device attempt follows until its new host implementation,
fault closure, independent review, qualification, and Full-LTO A/B proof are
complete.

## Evidence That Remains Binding

- The nonzero-detail retained-state `-ESTALE` defect is repaired in P2.92;
  accepted states must remain resumable through the whole declared sequence.
- Four pre-P2.92 runs establish a stable generation-88 prefix; P2.92 extends
  the live stable prefix through generation 106.
- The 45-byte two-slot retained ABI is unchanged. A and terminal B must be
  adjacent on every materialized execution path.
- P2.64 Stage C separates payload identity from qualification/evidence and
  live closure. Verifiers and documents may stay outside identity only when
  the contract declares that split and the approval bundle binds exact bytes.
- P2.84/P2.86/P2.88/P2.90/P2.92/P2.94/P2.96 are historical and immutable. Do
  not replay or silently repair them.

Load-bearing reports:

- `docs/reports/S22PLUS_FYG8_P292_F1_FINAL_NOT_ATTACHED_2026-08-01.md`
- `docs/reports/S22PLUS_FYG8_P292_POST_RUN_STOP_BOUNDARY_AND_VALUE_TELEMETRY_H0_2026-08-01.md`
- `docs/reports/S22PLUS_FYG8_P294_MODULE_DELIVERY_STATIC_STOP_H0_2026-08-02.md`
- `docs/reports/S22PLUS_FYG8_P294_DWC3_VALUE_TELEMETRY_IMPLEMENTATION_H0_2026-08-01.md`
- `docs/reports/S22PLUS_FYG8_P296_F1_BUILTIN_DWC3_REFUTED_2026-08-03.md`
- `docs/reports/S22PLUS_FYG8_POST_P296_GADGET_START_RETURN_ATTRIBUTION_H0_2026-08-03.md`
- `docs/reports/S22PLUS_FYG8_P296_EXECUTION_CRITICAL_INDEPENDENT_REVIEW_2026-08-03.json`
- `docs/reports/S22PLUS_FYG8_P298_GADGET_START_EVENT_IMPLEMENTATION_H0_2026-08-03.md`
- `docs/reports/S22PLUS_FYG8_POST_P298_EVENT_INGRESS_IRQ_ATTRIBUTION_H0_2026-08-04.md`
- `docs/reports/S22PLUS_FYG8_P298_EXECUTION_CRITICAL_INDEPENDENT_REVIEW_2026-08-03.json`
- `docs/operations/S22PLUS_FYG8_CANDIDATE_BUILD_QUALIFICATION_RUNBOOK.md`
- `docs/operations/DEVICE_ACTION_PROCESS_V2.md`

The full preceding working history is archived at
`docs/archive/roadmaps/GOAL_THROUGH_P294_MODULE_DELIVERY_2026-08-02.md`.
Archived text is evidence only and grants no authority.

## Success and Stop Conditions

The current device is healthy and the P3.00 campaign is closed at transfer
accounting 1/1. P2.98 refuted gadget-start or EP0-enable failure; P3.00 now
proves that the raw device-event boundary is reached but sees only another
device event, not RESET or CONNECT_DONE. H0 has exhausted that retained result:
the exact subtype was compressed away and cannot be recovered statically. The
next unit is the userspace-only subtype-retention and future-only sidecar fix
described above. Do not rerun unchanged P3.00 merely to repair the
non-authoritative host axis. Symbol-only proof, stock-path observation,
implicit success on an invalid trace, or a resource-gate bypass remains
insufficient for a successor.

Stop on a repeated material pre-session failure, any post-device-session
unexplained failure, target ambiguity, missing rollback, forbidden archive
member, source mutation after intent, external-module dependency, or evidence
that cannot distinguish the declared USB link-state branches. Never trade a
permanent safety boundary for speed.
