# Goal: S22+ repeatable native PID 1

Build a repeatable path from the FYG8 Android vendor boot chain and
source-matched kernel to a custom static `/init` running as PID 1, then grow
that entry point into a minimal observable and recoverable runtime.

This file reports current S22+ state and grants no authority. The binding
layers are `AGENTS.md`,
`docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md`, and the selected
shared process documents. A90 state and authorization remain separate.

## Current Frontier

P2.98 is the latest closed live unit. Its boot-only candidate and exact Magisk
rollback each transferred once with no replay, and final FYG8 Android/root
health passed. The operator observed one candidate boot with no boot loop. The
formal Process-v2 verdict is `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK` because no
host CDC-ACM endpoint appeared during the bounded observer window, while the
experiment result is information-bearing `REFUTED`: two byte-identical
post-rollback reads contain one exact, integrity-clean P2.98 terminal failure
record.

The adjacent valid slots are generation 106
`probe-ok-start-rc0-events-0x0-link-0`, then generation 107
`probe-ok-start-rc0-final-not attached-UNKNOWN-coreidle-1-susphy-0`. The exact
profile proves both EP0 enable calls were reached, `__dwc3_gadget_start()`
returned zero, trace readback and cleanup agreed, neither RESET nor
CONNECT_DONE was observed, and the link remained zero. Connection speed stayed
`UNKNOWN` and UDC stayed `not attached`.

The P2.92 prefix remains binding. It proves the native PID1 path completed
restart helper, FEMTO power-on/init, child resume, notify-connect, exact UDC,
configfs bind, and authoritative direct `DCTL.RUN_STOP` with
`DEVCTRLHLT=0`. P2.96 narrowed the remaining boundary beyond that prefix to
the interval where the built-in controller snapshot reports link-state zero
but no physical attach or connection speed materializes.

Post-P2.96 H0 attribution identified the tested source branch. The terminal
`UNKNOWN` is the later sysfs UDC speed, not retained raw `DSTS.CONNECTSPD`.
The exact `dwc3_gadget_pullup(true)` source ignores the signed return from
`__dwc3_gadget_start()` and overwrites it with the later run-stop result. An
EP0 initialization failure can therefore coexist with P2.96's nominal
run-stop snapshot. P2.98 now proves that failure did not occur in this run:
both EP0 enable calls executed and gadget-start returned zero. The ignored
return defect remains present in source, but it is not the active explanation
for this candidate result.

The exact P2.96 Full-LTO A/B disassembly closes the inlining hazard for that
build. `dwc3_gadget_pullup()` contains an actual `bl` to the out-of-line
`__dwc3_gadget_start`, discards its `w0`, then saves only run-stop's `w0`.
`dwc3_gadget_resume()` calls the same symbol and immediately tests `w0`.
Future builds must repeat this call-site proof; a local-text symbol alone is
not sufficient.

The P2.98 observer has one exact execution location. Candidate ramdisk `/init`
runs as PID 1, arms the inherited isolated tracefs instance immediately before
its one configfs UDC bind, keeps it active through the bounded final sampling
window, and disables, reads, profiles, and removes it before publishing the
terminal pair. Stock Android and rollback do not arm these dynamic probes and
cannot answer the candidate-path return or downstream-event questions.

Post-P2.98 H0 source and linked-binary analysis now selects P3.00,
`s22plus-fyg8-p300-event-ingress-irq-attribution-v1`. The next observer must
cover event-buffer/DEVTEN readback, the DWC3 top-half entry/return result,
threaded-handler count/flags, and the raw event-dispatch boundary in the same
bind-to-final window. The result family now has eleven exact classes:
no-top/count-zero, no-top/count-nonzero, top-none-only, handled-no-wake,
wake-no-thread, thread-empty-pass, thread-nondevice-only, other device events,
RESET without CONNECT_DONE, CONNECT_DONE without RESET, and both events.

The design uses 15 bind events, within the existing capacity of 16. It keeps
the first ten P2.98 events, replaces the RESET/CONNECT_DONE handler probes with
one controller-attributed raw device-event probe, and adds one event-config
snapshot plus matched `dwc3_interrupt` entry/return and threaded-handler entry.
Hard-IRQ and thread probes use all-context filters because `common_pid` can be
zero and filtered profile hits are not record counts. The IRQ return probe is
explicitly `r32`, matching the exact `CONFIG_NR_CPUS=32` concurrency bound.
The raw-event profile delta distinguishes non-device entries only when no
cutoff fired. A conditional post-trigger retains the first CONNECT_DONE record
then stops tracing. The exact recording window opens in
`tracing_on -> group-enable -> trigger-arm` order and closes by removing the
trigger while tracing still records, reading the post-removal tracing state,
then disabling the group before tracing itself. Its armed count, final
cutoff/race state, streaming parser, ring-loss checks, zero missed probes,
exact pointer agreement, and verified cleanup are all required by every
accepted pair.

The A detail space is fixed at `0xD00-0xDAF`, eleven 16-value families with
link state in the low nibble. CONNECT_DONE without RESET and with RESET are
separate mandatory families. The final B family remains `0xE00-0xE83`; new
observer contradictions occupy the free `0xF73-0xF7F` range. The existing
private host USB trace sidecar is selected for the same later F1 window, so
host visibility and device ingress can form one 2-by-2 diagnostic result
without another candidate boot. Its exact campaign, attempt, candidate, and
journal binding is still a pre-F1 H0 gate; the current core implementation
does not claim that integration.

This is the first honest measurement of the project's long-standing direct
PID1 enumeration boundary. O1.1 is the only candidate-side ACM exchange
success and it used Android's existing USB stack. No minimal PID1 candidate
has yet proved host enumeration.

P2.94 was designed to retain two adjacent value records: DSTS `USBLNKST`,
then a conditional terminal state containing the remaining digital-control
classification. Its Full-LTO A/B and candidate identity are valid, but formal
linked replay found a delivery blocker before packaging or device contact:

- built-in `s22_p294_dwc3_state_snapshot` is linked into `vmlinux`;
- `s22_p294_wrapper_vbus_snapshot` is built only into external
  `dwc3-msm.ko`;
- the boot-only candidate builder injects zero modules and reuses the stock
  vendor ramdisk; and
- the runtime requires both snapshots, so P2.94 cannot produce its intended
  terminal telemetry on device.

P2.94 therefore remains an H0 static stop. It must not be packaged, promoted,
manifested, or used for F1.

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

The candidate and exact rollback each transferred once. The transaction is
durably `CLOSED`, final rooted FYG8 health passed, recovery is not required,
the sidecar left zero owned processes, and A90 received zero commands.

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
device event, not RESET or CONNECT_DONE. The next unit is H0 analysis of that
exact `DEVICE_OTHER_ONLY` branch and a proportional future-only sidecar
shutdown fix. Do not rerun P3.00 merely to repair the non-authoritative host
axis. Symbol-only proof, stock-path observation, implicit success on an invalid
trace, or a resource-gate bypass remains insufficient for a successor.

Stop on a repeated material pre-session failure, any post-device-session
unexplained failure, target ambiguity, missing rollback, forbidden archive
member, source mutation after intent, external-module dependency, or evidence
that cannot distinguish the declared USB link-state branches. Never trade a
permanent safety boundary for speed.
