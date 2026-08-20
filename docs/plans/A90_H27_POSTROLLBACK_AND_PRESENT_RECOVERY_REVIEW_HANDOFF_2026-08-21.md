# A90 H27 postrollback and present-recovery full-review handoff — 2026-08-21

## Scope

Perform one independent, host-only, public-tree full review of the A90 minimal
boot-only F1 execution closure after the H27 boot-loop incident. Do not contact
USB, `/dev`, ADB, Native serial, the device, another target, network, or
`workspace/private`; do not infer live authority from a PASS.

This is not a delta-only review. Re-read `AGENTS.md`, then
`docs/operations/targets/A90_TARGET_CONTRACT.md`, then `GOAL_A90.md`, and attack
the complete execution closure named by the owner.

## Claims to break

1. An ordinary rollback uses one fixed helper invocation. A strict ADB
   inventory either reuses one already-present recovery endpoint only when its
   serial hash is the qualified A90, or observes no recovery endpoint and sends
   Native recovery once. It never selects a caller serial, accepts a foreign or
   ambiguous recovery endpoint, or retries Native recovery, boot write, or TWRP
   System return.
2. The fixed H27 postrollback reconciler accepts no caller input and dispatches
   no device effect. It binds the exact manifest and nine-record incident,
   requires the active and candidate guards before publication, obtains only a
   fresh read-only exact V2321 health snapshot, publishes
   `41-recovery-closed.json`, removes only the active guard, and leaves the H27
   candidate guard consumed.
3. The new recovery record never relabels the manual rollback as proved. Its
   exact value is `UNPROVED_EXTERNAL_CONTINUATION`, with candidate and rollback
   replay both false. Because postrollback observation intentionally skips the
   H27 marker paths, it records `freshStateObserved=false` and
   `freshStateAbsent=false` rather than inventing absence.
4. A crash before publication removes nothing. Publication and active removal
   share one review lease; a crash between them parks with the active guard
   retained and never resumes cleanup from the mutable dynamic snapshot. A
   later invocation reports completion only if the active guard is absent.

## Measured execution closure

The owner currently names 13 paths. At this handoff checkpoint its canonical
digest is
`e58746ea93270c43a28db5df20695a61a687eec942a5a665f562f4fe5173f077`.
Recompute it with `execution_closure_sha256()` and stop if it differs. The
closure includes both incident reconcilers, the owner, adapter, flash helper,
Native observation/bridge sources, and the archived historical review named by
the original manifest. Tests and this handoff are review evidence, not runtime
members.

## Required hostile cases

- already-present correct recovery; no recovery; wrong recovery; two recovery
  endpoints; changed foreign endpoint; malformed ADB inventory;
- caller serial, mixed mode flags, missing serial digest, internal resend, or
  legacy retry behavior entering the minimal rollback path;
- missing/drifted incident record, manifest, active guard, candidate guard,
  current review, V2321 identity, health, recovery evidence, or other-target
  disposition;
- unhealthy/wrong resident attempting publication; publication loss; active
  cleanup loss; second invocation; any candidate/rollback/reboot method call;
- deleting the candidate guard, proving the external rollback, permitting
  candidate replay, or removing the active guard before the durable record.

## Reviewer output

Only after a clean full review, create
`docs/reports/A90_BOOT_ONLY_F1_MINIMAL_POSTROLLBACK_INDEPENDENT_REVIEW_2026-08-21.json`
using the exact schema consumed by `_validate_qualification_review()`. It must
bind the unchanged H27 candidate and V2321 rollback, the recomputed current
closure digest, exact recovery/hazard/fresh-state objects, empty H/M/L findings,
zero contacts/writes, and `liveAuthority: false`. The reviewer chooses the
verdict and identity; this handoff does not prefill either.

A `PASS_GO` qualifies only these execution bytes. It does not close the H27
guard, authorize the connected read, qualify H28, create an approval, or grant
F1.
