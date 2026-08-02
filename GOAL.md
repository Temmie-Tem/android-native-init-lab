# Goal: S22+ repeatable native PID 1

Build a repeatable path from the FYG8 Android vendor boot chain and
source-matched kernel to a custom static `/init` running as PID 1, then grow
that entry point into a minimal observable and recoverable runtime.

This file reports current S22+ state and grants no authority. The binding
layers are `AGENTS.md`,
`docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md`, and the selected
shared process documents. A90 state and authorization remain separate.

## Current Frontier

P2.92 is the latest closed live unit. Its boot-only candidate and exact
rollback each transferred once with no replay, and final FYG8 Android/root
health passed. Retained generation 106 proves the native PID1 path completed
restart helper, FEMTO power-on/init, child resume, notify-connect, exact UDC,
configfs bind, and authoritative direct `DCTL.RUN_STOP` with
`DEVCTRLHLT=0`. The UDC nevertheless stayed `not attached`, speed stayed
`UNKNOWN`, and no host ACM endpoint appeared.

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

## Selected Bounded Unit: P2.96 Built-in DWC3 Telemetry

P2.96 is a fresh boot-only successor. It removes the undeliverable external
`dwc3-msm.ko` dependency and preserves only the built-in DWC3 snapshot, which
is carried by `boot.img`.

Required behavior:

1. Preserve the P2.92 path and the stable generation-106 prefix.
2. Capture `USBLNKST`, `RUN_STOP`, `DEVCTRLHLT`, `COREIDLE`, `PRTCAP`,
   `SUSPHY`, and `CONNECTSPD` from built-in DWC3 code.
3. Retain adjacent A/B records: 16-value `USBLNKST`, then the conditional
   132-value terminal state.
4. Gate the already proven direct-bind predicates. Mismatches remain explicit
   failure records; no wrapper-VBUS observation is claimed.
5. Preserve `ACCEPT_TO_RESUME_CLOSURE`, continuous sequence walk,
   publication errno observability, SoT coherence, and exact two-slot
   adjacency.
6. Require the linked and packaged closure to contain the built-in snapshot
   and to require no candidate-only external-module symbol.
7. Capture bounded host `dmesg`/udev/USB inventory during any later F1 so the
   host-side attach observation independently cross-checks `USBLNKST`.

This unit does not add a regulator predicate, external module injection,
observer ABI, new partition payload, or policy redesign.

## Ordered Execution

1. Archive the prior 798-line goal byte-preservingly and keep it inert.
2. Implement and fault-test the P2.96 telemetry/spec/model/decoder/generator,
   built-in-only driver patch, linked audit, and package-delivery gate.
3. Freeze the complete byte-affecting change list. Print every selected
   `SOURCE_KEY` and compare it bidirectionally with Git-derived changes.
4. Derive a fresh immutable intent only after the freeze is clean. Do not
   change a selected source byte afterward.
5. Run userspace and pre-LTO qualification, then Full-LTO A/B. After A,
   require the private-root and clang-resource leak scans to pass before B.
6. Require byte-identical A/B `boot.img`, linked/static closure, deterministic
   boot-only packaging, offline promotion, and one ready manifest.
7. Run one exact connected read-only S22+ D0, explicitly leaving every other
   attached target untouched.
8. Stop after the ready manifest and exact D0 at the current Process-v2 v1
   binding handoff. Trial policy adds no per-candidate approval, but the legacy
   runner still requires its fresh immutable token until aligned; preparation
   alone never arms F1.

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
- P2.84/P2.86/P2.88/P2.90/P2.92/P2.94 are historical and immutable. Do not
  replay or silently repair them.

Load-bearing reports:

- `docs/reports/S22PLUS_FYG8_P292_F1_FINAL_NOT_ATTACHED_2026-08-01.md`
- `docs/reports/S22PLUS_FYG8_P292_POST_RUN_STOP_BOUNDARY_AND_VALUE_TELEMETRY_H0_2026-08-01.md`
- `docs/reports/S22PLUS_FYG8_P294_MODULE_DELIVERY_STATIC_STOP_H0_2026-08-02.md`
- `docs/reports/S22PLUS_FYG8_P294_DWC3_VALUE_TELEMETRY_IMPLEMENTATION_H0_2026-08-01.md`
- `docs/operations/S22PLUS_FYG8_CANDIDATE_BUILD_QUALIFICATION_RUNBOOK.md`
- `docs/operations/DEVICE_ACTION_PROCESS_V2.md`

The full preceding working history is archived at
`docs/archive/roadmaps/GOAL_THROUGH_P294_MODULE_DELIVERY_2026-08-02.md`.
Archived text is evidence only and grants no authority.

## Success and Stop Conditions

P2.96 H0 succeeds only if its source identity, complete sequence, built-in
symbol delivery, Full-LTO determinism, static closure, package, and manifest
all verify. D0 succeeds only with an unambiguous exact S22+ and bounded reads.

Stop on a repeated material pre-session failure, any post-device-session
unexplained failure, target ambiguity, missing rollback, forbidden archive
member, source mutation after intent, external-module dependency, or evidence
that cannot distinguish the declared USB link-state branches. Never trade a
permanent safety boundary for speed.
