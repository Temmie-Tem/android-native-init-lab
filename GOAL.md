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

## Selected Bounded Unit: Gadget-Start Return Observable Contract (H0)

Do not name, build, package, manifest, or run a successor candidate yet. The
next bounded unit freezes one exact boot-deliverable observable for the
selected predicate.

Required behavior:

1. Define one matched entry/return trace pair on built-in
   `__dwc3_gadget_start()` and capture signed `$retval:s32` inside the existing
   authoritative bind window.
2. Require exactly one pair nested between pullup-on entry and run-stop entry.
   Missing, duplicate, unpaired, or out-of-order events are trace-source
   contradiction, never implicit success.
3. Make `rc < 0` an early gadget/EP0-start terminal and `rc == 0` the sole gate
   that permits a later event- or PHY-level experiment.
4. Prove the observable and all parser inputs are delivered by `boot.img`; do
   not reintroduce the rejected external `dwc3-msm.ko` dependency.
5. Preserve the full P2.92 prefix, P2.96 adjacent-slot result, 45-byte retained
   ABI, and Stage-C identity split. Stop before candidate intent or build.

## Ordered Execution

1. Preserve the closed P2.96 result and the post-P2.96 H0 attribution report.
2. Freeze the exact gadget-start entry/return grammar and same-invocation
   pairing rules without modifying historical P2.96 sources.
3. Specify exhaustive negative, zero, missing, duplicate, and ordering
   outcomes while retaining the two-slot publication contract.
4. Prove the symbol, dynamic trace facility, parser closure, and runtime input
   are boot-deliverable with no external-module dependency.
5. Stop before candidate intent or build. Any later implementation begins at a
   complete fresh `SOURCE_KEYS` freeze, qualification, Full-LTO A/B, boot-only
   package, changed-closure review, D0, and attended Process-v2 execution.
   Never reuse the consumed P2.96 run.

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
- `docs/operations/S22PLUS_FYG8_CANDIDATE_BUILD_QUALIFICATION_RUNBOOK.md`
- `docs/operations/DEVICE_ACTION_PROCESS_V2.md`

The full preceding working history is archived at
`docs/archive/roadmaps/GOAL_THROUGH_P294_MODULE_DELIVERY_2026-08-02.md`.
Archived text is evidence only and grants no authority.

## Success and Stop Conditions

The current H0 unit succeeds only if it freezes one exact, paired
`__dwc3_gadget_start()` return observable, proves boot delivery, and makes a
zero return the explicit prerequisite for any later event or PHY hypothesis.
A speculative probe list, implicit success on a missing trace, or a new
candidate name is not success.

Stop on a repeated material pre-session failure, any post-device-session
unexplained failure, target ambiguity, missing rollback, forbidden archive
member, source mutation after intent, external-module dependency, or evidence
that cannot distinguish the declared USB link-state branches. Never trade a
permanent safety boundary for speed.
