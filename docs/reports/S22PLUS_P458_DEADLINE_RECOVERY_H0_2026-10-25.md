# S22+ P458 deadline and original-owner recovery — H0, 2026-10-25

## Scope and incident

P458 closed **NO_PROOF / ANDROID_CLOSED_HEALTHY** after its sole Android-to-
Download command. Its 30-second departure deadline expired 2.214537 seconds
before durable intent; no departure sample or N transfer occurred. One original
A recovery and a health-only continuation closed the consumed operation. The
[run report](S22PLUS_DEBIAN_REBOOT_P458_RUN_2026-10-25.md) retains that result.

This unit fixes the host deadline ordering and missing connector recovery
entry. It performs no device observation, command, transfer, grant, worker
startup, MCP reconnection or server action. It does not replay P458, change
its saved approvals/source snapshots, or assert current native_data health.
A90 and S20+ are untouched; the 46 preexisting dirty files retain their bytes.

## Changes

The Download intent now obtains its USB generation and original 30-second
deadline after the owner's authority, consumption and no-replay checks, just
before durable intent publication. The raw producer prepares its stream files
before this callback and invokes it immediately before process creation.
Publication cannot renew the deadline. The original finite grant is rechecked
after snapshot construction and after durable publication.
Expiry after publication blocks the Android command; expiry during an observer
guard blocks a late sample. No other control deadline is redefined.

Each adapter may reuse only successful immutable automatic-boot image
qualification. Context-local hooks record the exact metadata of bytes already
verified by the existing record, raw-stream and descriptor-pin readers. Direct
runtime templates/sources are verified too; pure archive caches are cleared
before the first qualification. The entire dependency set is checked before
installing and reusing the ticket. Replacement, changed content even with
restored size/mtime, symlinks, extra links, mode/owner changes or a different
image invalidate it without requalification in the running owner.

Task/capability/source identity, grant/host epoch, ownership, journal, current
target/health and transfer artifact checks stay outside this ticket. Recovery
keeps its original separate checks. A new process performs full qualification.

The persistent connector adds `recover_approved_task` for the stopped original
automatic-boot owner. It requires the saved approval, unchanged task/source
binding, consumed operation, settled launcher, target lease and F1 owner.
It invokes only the existing fixed recovery CLI and original A. If any A
transfer was intended, raw completion is required and only health remains.
`resume_approved_health` now recognizes both `install-android` and
`recover-android`. Uncertain A, ambiguous ownership, closed tasks and unresolved
dispatches reject. The separate one-shot recovery ingress cannot bypass a
consumed health continuation. No new grant, native replay or arbitrary command
is exposed.

## Validation

Private evidence is under
`workspace/private/outputs/s22plus-p458-deadline-recovery-h0-20261025-1/`.

- Thirteen focused tests exercise delayed checks before intent, slow publication,
  late polling, nested/raw/empty-stream/archive/template changes, file identity
  replacement, warm pure caches and invalid-ticket behavior. Actual harmless
  host-process fixtures also verify stream preparation before intent and raw
  failure publication without a subprocess when the callback rejects. Grant
  expiry during publication blocks dispatch independently of the USB deadline.
  Slow USB snapshot publication consumes the same deadline and cannot start a
  fresh window after an old generation observation.
- Fifty existing owner, task, target, raw-capture and transfer tests pass.
- Thirty-seven persistent connector tests pass, including stopped pre-N
  recovery, raw-proved recovery-A health, expiry without grant renewal,
  duplicate/uncertain dispatch, orphan results, owner/lease isolation and
  retained resident/backend lifetime behavior. An initial fixture assertion
  used a nonexistent nesting key; its corrected rerun passes.
  Fourteen process tests pass again after the selected review closure expands
  to include all 20 files at the changed host boundary.
- Actual historical P458 `image_binding` results are identical through full,
  first-ticket and reused-ticket validation, with subprocess creation and raw
  acquisition explicitly denied. Measured times were 15.859, 16.559 and 0.046
  seconds respectively. The ticket contains 2,071 file identities; these counts
  and timings are observations, not admission thresholds.
- Comparison with the independent prior read inventory identifies one current
  adapter-source read performed only at module import for `TRANSFER_SOURCE`.
  It remains covered by the separate current capability/source check. Saved
  historical adapter sources and all proof/archive/template inputs are covered
  by the ticket. The initial comparison failure and its explanation are retained.

The past-failure checklist applies as follows: IO and HOST are confirmed by
clock ordering, post-guard rejection and harmless process fixtures; SEMANTIC,
WIRE and ROUTE by exact stopped-owner dispatch and both raw A step names;
PERSIST and RETURN by original intent/closure and no-replay tests; ARTIFACT and
AUDIT by complete dependency comparison, source pins and preserved raw/history.
ABI and DISPLAY are inapplicable because no device ABI or display code changes.
Unchanged ARM64 image/VM tests are reused; no C or device runtime was rebuilt.

## Review and deployment boundary

Independent patch review is **PASS_GO**, with no open findings. It binds all
150 current execution sources and the 20 selected bridge sources, reproduces
20 independent failure/dependency checks, and verifies the 46 preexisting files
and historical task/core/connector/closure pins remain unchanged. The 2,071
real qualification dependencies retain their recorded identities and the
result matches the independent pre-patch observation. The 155-file private
snapshot and final compilation receipts preserve this implementation.

The new immutable persistent-transport V3 review is selected for future use;
its actual selector/backend consumers pass H0 checks. The historical
P458 capability and versioned connector reviews remain unchanged. The next
physical task needs the new reviewed execution closure and fresh concrete
qualification/authority; this repair is not physical readiness.
All four dispatch tools reject or report consumed the actual closed P458 task
with process creation denied; its approval, terminal and closure pins remain
unchanged. Compilation, documentation links and repository-boundary checks pass.

The seven-tool worker protocol needs one ordinary startup and MCP reconnection
after review. Thereafter unchanged worker/protocol bytes continue to accept
reviewed backend and candidate updates without another worker restart. This
H0 unit does not perform that startup or any device action.
