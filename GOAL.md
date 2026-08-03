# Goal: S22+ repeatable native PID 1

Build a repeatable path from the FYG8 Android vendor boot chain and
source-matched kernel to a custom static `/init` running as PID 1, then grow
that entry point into a minimal observable and recoverable runtime.

This file reports current S22+ state and grants no authority. The binding
layers are `AGENTS.md`,
`docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md`, and the selected
shared process documents. A90 state and authorization remain separate.

## Current Frontier

P2.96 is the latest closed live unit. Its boot-only candidate and exact Magisk
rollback each transferred once with no replay, and final FYG8 Android/root
health passed. The formal Process-v2 verdict is
`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`, while the experiment result is
information-bearing `REFUTED`: two byte-identical post-rollback reads contain
one exact, integrity-clean P2.96 terminal failure record.

The adjacent valid slots are generation 106 `USBLNKST=0`, then generation 107
`digital-control-state-nominal-not attached-UNKNOWN-coreidle-1-susphy-0`.
This proves the built-in DWC3 snapshot was delivered and executed without the
P2.94 external-module dependency. It does not prove host enumeration;
connection speed remained `UNKNOWN`, UDC stayed `not attached`, and no host
CDC-ACM endpoint appeared during the bounded observer window.

The P2.92 prefix remains binding. It proves the native PID1 path completed
restart helper, FEMTO power-on/init, child resume, notify-connect, exact UDC,
configfs bind, and authoritative direct `DCTL.RUN_STOP` with
`DEVCTRLHLT=0`. P2.96 now narrows the remaining boundary beyond that prefix to
the interval where the built-in controller snapshot reports link-state zero
but no physical attach or connection speed materializes.

Post-P2.96 H0 attribution closes the next source branch. The terminal
`UNKNOWN` is the later sysfs UDC speed, not retained raw `DSTS.CONNECTSPD`.
The exact `dwc3_gadget_pullup(true)` source ignores the signed return from
`__dwc3_gadget_start()` and overwrites it with the later run-stop result. An
EP0 initialization failure can therefore coexist with P2.96's nominal
run-stop snapshot. That return is the earliest unresolved predicate; event and
PHY observations are downstream until it is proved zero.

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

## Selected Bounded Unit: P2.98 Host Closure and Candidate Qualification (H0)

P2.98 is the fresh successor contract
`s22plus-fyg8-p298-gadget-start-event-attribution-v1`. Its host implementation
and canonical Tier-1 intent are complete. The reproducible static userspace
also passes. Pre-Full-LTO qualification is now parked before any kernel build:
the shared historical regression gate is 108/110 because two A90-only document
expectations are stale, and this host has 16,317,992,960 bytes of physical RAM
against the mandatory 32,212,254,720-byte minimum. The S22+ assertion passes,
swap and disk gates pass, and neither blocker authorizes a cross-target edit or
a resource-gate bypass. Independent review returned `PASS_GO` for the exact
hash-bound H0 host capability with no findings; it does not close either gate
or authorize packaging, F1 preparation, or live use. No device action is part
of this bounded unit.

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
The final focused P2.98 suite passes 18/18 and the inherited focused closure
passes 128/128. A read-only audit of the historical P2.96 A/B pair passes the
new six-function call-shape checks, but it is only baseline evidence and never
substitutes for the mandatory fresh P2.98 Full-LTO A/B pair.

## Ordered Execution

1. Keep every P2.96 `SOURCE_KEY` immutable and retain P2.96 as the historical
   behavioral baseline.
2. Freeze the complete P2.98 Tier-1 set before deriving its one canonical
   intent. Do not edit a Tier-1 byte afterward.
3. Reproduce the static AArch64 userspace, replay inherited focused gates, and
   bind the exact linked-audit metadata into pre-Full-LTO qualification.
4. Apply the runbook's physical-RAM, swap, disk, toolchain, source, and clean
   worktree gates before Full-LTO A/B. The present physical-RAM gate is failed,
   so resume only on a qualified host with at least the exact required RAM and
   after the shared 110-test regression gate is current. Never bypass either
   gate.
5. Retain the fresh independent `PASS_GO` for the exact reviewed
   trace/schema/parser and postbuild closure only while its named hashes remain
   unchanged. A later unit must independently satisfy fresh Full-LTO closure,
   package, rollback, D0, attended F1, recovery, and final-health gates. Never
   reuse the consumed P2.96 run.

Trial policy adds no per-candidate approval, but the legacy runner still
requires its fresh immutable token until aligned. The consumed P2.96 token,
prepared binding, journal, and candidate attempt are never reusable.

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
- `docs/reports/S22PLUS_FYG8_P298_EXECUTION_CRITICAL_INDEPENDENT_REVIEW_2026-08-03.json`
- `docs/operations/S22PLUS_FYG8_CANDIDATE_BUILD_QUALIFICATION_RUNBOOK.md`
- `docs/operations/DEVICE_ACTION_PROCESS_V2.md`

The full preceding working history is archived at
`docs/archive/roadmaps/GOAL_THROUGH_P294_MODULE_DELIVERY_2026-08-02.md`.
Archived text is evidence only and grants no authority.

## Success and Stop Conditions

The current H0 unit succeeds only if host machinery enforces the exact PID-1
return pair, EP-enable hit attribution, same-run downstream event discriminator,
and direct call sites from both actual Full-LTO linked images. Symbol-only
proof, stock-path observation, implicit success on an invalid trace, or a
resource-gate bypass is not success.

Stop on a repeated material pre-session failure, any post-device-session
unexplained failure, target ambiguity, missing rollback, forbidden archive
member, source mutation after intent, external-module dependency, or evidence
that cannot distinguish the declared USB link-state branches. Never trade a
permanent safety boundary for speed.
