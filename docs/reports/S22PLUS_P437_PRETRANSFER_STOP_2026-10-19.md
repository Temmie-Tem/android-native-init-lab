# S22+ P437: stopped before candidate transfer; Android healthy

Status: **NO_N_TRANSFER_ANDROID_CLOSED_HEALTHY**. The attended operation is
consumed and closed. P437's candidate was neither transferred nor globally
claimed. One original-A transfer completed, followed by full changed-boot
rooted Android/GPT/Android32 health. No F1 owner remains.

## Selected operation and observed outcome

The operator returned the exact prepared P437 approval and stated attendance
and usable Download recovery. The one-operation, 3600-second task selected
`debian-autoboot-v1` / `p437` / `v0.10.0-rc.1`, under contract revision 51 and
the qualified [P437 H0 implementation](S22PLUS_AUTOBOOT_RCS_P437_DESIGN_2026-10-18.md).
Current source/review/artifact/host binding and the preserved source snapshot
passed before opening the grant. Fresh initial Android health also passed.

The owner issued one Android Download request and completed that step. The
next candidate-transfer step stopped with `OdinTransitionError` before a
candidate transfer intent. Both retained Odin snapshots reported one live
endpoint with the same immutable identity. There is no N launch receipt,
AP-command capture, transfer intent or global candidate claim. The reviewed
control flow requires the launch receipt and intent before AP dispatch; the
failed call returned before that point. This is evidence of no candidate
transfer, not an inference from missing USB or Debian logs.

Research stopped at that point. The existing recovery owner used the observed
Download state to transfer the exact original Android A once. No candidate
boot, native_data writer, installed Debian service, NCM attempt or SSH workload
was started by this operation. The original terminal retains scientific
`NO_PROOF`; the separate closure describes the more specific pre-transfer stop.

## Recovery and closure

The first post-A health attempt observed Android returning but its root-health
ADB read returned exit 1 with `error: closed`. That raw failure is preserved.
The next invocation reconstructed the already completed A transfer and acquired
only a new health attempt. It did not repeat A or issue another mode change.

Final root/boot/supporting-image health, changed Android boot identity,
complete GPT metadata and Android32 statfs passed. Reported total capacity was
34,357,624,832 bytes, with the native partition still present. This establishes
Android health; it is not a native_data filesystem inspection.

The closure audit rederived initial health, the Download request, the unique
A transfer and final health from their original raw captures, with subprocess
and device acquisition disabled. It verified 332 raw captures, the single
failed post-A read, the unchanged 12-row journal and original terminal. The
host/runtime source snapshots match their execution bindings. The finite task
is closed with one consumed operation, **N=0, A=1**, and no remaining owner.

Canonical elapsed times are relative to grant opening:

| Event | Seconds | Evidence |
| --- | ---: | --- |
| Initial Android preflight complete | 119.817 | Original health captures |
| Android Download intent | 154.650 | Unique durable control intent |
| Android Download step complete | 163.922 | Original request result |
| Candidate-transfer step entered | 175.471 | Step start only |
| Pre-transfer stop | 211.606 | `OdinTransitionError`; no N intent |
| Candidate transfer/startup | — | Not started |
| Original-A transfer intent | 286.175 | Unique recovery intent |
| Original-A transfer complete | 287.712 | Original Odin raw result |
| Final Android health complete | 353.059 | Changed-boot Android32 proof |
| H0 task closure complete | 427.415 | Durable close and raw audit |

## Host-side timing finding and diagnostic limit

The reachable adapter gives `revalidate_endpoint_ticket` a 10-second window.
Its observer factory calls the full execution guard. The transition primitive
constructs that factory for enumeration and again for post-receipt endpoint
revalidation, so both full guards run inside the same short window. The guard
re-enters the candidate's artifact and qualification consumers. Those are
substantial H0 checks, rather than just the current endpoint/source checks.

Independent H0 inspection confirms this timing conflict while preserving the
original evidence. The two saved snapshots retain the same immutable endpoint
and generation. This supports a host-side budget problem, not a claimed change
to Debian, its kernel, the target's USB behavior or its stored root.

The normal guard validates the same image twice: once through protected-root
task validation and once through `image_valid`. Across the two observer
constructions this is four full qualification passes. Two pure saved-image H0
measurements took 3.361 and 2.912 seconds; four times the smaller measurement is
11.648 seconds before other guard work. The production revalidation consumer
rejects an unchanged saved endpoint/generation under that timing model, while
zero-cost and a wider synthetic-window control accept. These controls change
no live deadline and issue no device command. They reproduce the current
design defect, not the missing original exception message.

The original owner saved the exception type and recovery state, but not the
full exception message. Therefore the precise historical failing predicate is
not proved from the retained error alone. A transient post-receipt observer
failure cannot be excluded. A reproduced deadline defect must not be substituted
for an unrecorded historical exception message or used to relabel this stop.

The next useful H0 work is a scoped correction to the repeated qualification
inside the transfer's short observation window, with complete exception
diagnostics. Preserve exact current target/source/artifact checks, the existing
deadlines and the original no-replay rules. The affected scope is prospective
P437 automatic-boot transfer; it must be reviewed before the next such attempt.
Retirement evidence is a real saved-package guard/observer test that fits the
existing window while rejecting changed inputs, plus independent review of the
reachable correction. This review trigger is the next prospective use, not a
new standing device grant. No runner or capability was altered during recovery.

## Retained records and limits

Private evidence is under
`workspace/private/outputs/s22plus-autoboot-rcs-p437-h0-20261018-1/`:

- `physical-authorization-1.json`, `physical-grant-1.json` and execution/recovery logs;
- `ready-1/task/operation-0001/`: original journal, raw captures and terminal;
- `ready-1/task/closure-audit.json` and `closed.json`: H0-audited task closure;
- `host-source-snapshot-1/` and `build-3/source-snapshot/`: execution provenance;
- `review/physical-pretransfer-stop-1/`: independent H0 incident analysis.

The H0 image/VM results remain historical qualification evidence. They do not
become a physical rcS, service or SSH result. The original grant is exhausted
and closed even though the N artifact remains unclaimed. No consumed journal,
approval, prior review or P434/P435 prerequisite was rewritten. A90/S20+
devices and their preexisting work were untouched.
