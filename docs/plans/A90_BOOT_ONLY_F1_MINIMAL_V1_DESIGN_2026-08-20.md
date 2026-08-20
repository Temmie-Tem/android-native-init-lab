# A90 boot-only F1 minimal v1

Date: 2026-08-20
Target: operator-owned Samsung Galaxy A90 5G only
Tier: H0 design and host implementation
Live state: activation code present, pending fresh review and run inputs; no
D0, D1, F1, candidate, or approval authority

## Outcome

The reusable A90 kernel-experiment path is deliberately reduced to the
operator's actual transaction:

1. prove that the one attached target is the expected healthy A90;
2. prove the candidate and rollback `boot` images are the exact declared
   regular files;
3. durably record candidate intent and send the candidate once;
4. observe the bounded result;
5. if candidate health is not proved, durably record rollback intent and send
   the rollback once;
6. record the final target health.

The state machine is
`workspace/public/src/scripts/server-distro/a90_boot_only_f1_minimal_v1.py`.
Its CLI derives the fixed run/log paths from one canonical manifest, exposes
only `prepare`, approved `execute`, and read-only `audit`, and constructs the
small fixed adapter below. Activation itself still requires a fresh closure
review plus the candidate review/manifest and attended approval.
Each prepare/execute invocation reserves a new immutable
`<runId>-<phase>-<ordinal>-logs` directory. Pre-effect failure or a lost host
process preserves prior logs but does not make a correct later invocation
collide with them.
Prepare does not create its journal directory until candidate/rollback and
fresh target preflight pass. Active-guard contention or ordinary pre-effect
candidate-guard rejection removes only that still-empty directory; logs remain.
The adapter is loaded from the exact sibling source path through `importlib`
after aliasing the already-running minimal module; activation does not depend
on ambient `sys.path`. A per-load sentinel plus exact module path and class
identity reject stale or foreign `sys.modules` aliases. Log-directory
reservation is one atomic `mkdir`, and an ordinal collision is normalized and
retried without overwriting either log.

## What remains load-bearing

- A90 only, `boot` only, attended F1 only.
- One exact manifest selects one expected resident, candidate, and bounded
  timeout pair. The owner itself fixes the sole rollback to V2321 by absolute
  path, size, SHA-256, version, and build; a manifest cannot replace it. It
  cannot express a command or another partition.
- Candidate and rollback are opened with `O_NOFOLLOW`, must be direct regular
  single-link files owned by the current user and not group/world writable,
  and are checked by size and SHA-256 before use and after the helper returns.
  A pre-open `lstat` rejects FIFO/device/symlink inputs; the subsequent open is
  nonblocking and must resolve to the same inode before any hash read. Every
  later checkpoint rejects size drift and the 128 MiB cap before rehashing.
- Fresh preflight must prove the expected healthy resident, physical recovery,
  the same boot and target identity prepared for approval, and that other
  targets were untouched. The adapter hashes a bounded complete `lsusb`
  inventory and requires exactly one Native A90 `04e8:6861`; other Samsung
  endpoints may remain present but are never selected. The fixed A90 serial
  symlink/realpath is checked separately. Recovery ADB binds the complete
  pre-existing non-recovery endpoint set, requires it to remain unchanged,
  and selects only one newly arrived recovery endpoint caused by the exact
  A90 Native recovery command. The private qualification additionally binds
  the SHA-256 of that A90 recovery serial; the raw serial is never tracked.
  This adds no standing ADB owner: ADB remains confined to recovery transfer.
- After the exact boot-prefix readback and immediately before the sole TWRP System-reboot request, the helper revalidates TWRP `3.7.0_12-0` and the fixed
  root-owned mode-`0755` `/system/bin/rebootsystem.sh` at size `89`, SHA-256
  `3c3058563bbe775505fb5c0be8b94ae4a5e44787b5971ca17fd49e599ae7dd07`.
  The reviewed A90-only common-contract exception covers only that hook's
  exact 256-byte `misc` BCB clear. There is no caller-selected raw command,
  path, offset, length, payload, or retry.
- Approval is derived from the canonical manifest digest, target evidence, and
  current boot ID. It is not reusable for another manifest, device, or boot.
- The manifest embeds one candidate-specific qualification. It binds the exact
  candidate/rollback pair, one direct regular independent-review JSON,
  explicit recovery and hazard decisions, and the fresh enable/latch paths.
  The owner opens and rehashes that review before PREPARED and immediately
  before approval/effect. It also parses an exact schema requiring `PASS_GO`,
  the current ten-file execution closure, A90/candidate/rollback identities,
  matching recovery/hazard objects, no material findings, and zero contacts.
  The parser consumes the same bytes it hashes, and execute repeats validation
  after fresh Native preflight immediately before approval and candidate
  intent publication. It rejects non-regular/symlink/shared-writable review
  paths by `lstat` before opening; only then does it open nonblocking,
  revalidate the same inode, and perform the bounded read.
- Physical recovery is never a caller boolean. The adapter accepts only the
  validated `A90_ATTENDED_PHYSICAL_RECOVERY_V1` receipt for the fixed Native to
  stable-ADB-baseline/single-new-recovery-arrival/readback method. The private
  manifest binds the A90 recovery serial SHA-256, and the recovery-evidence
  digest is present in every snapshot and terminal.
- Fresh preflight and candidate health both use fixed read-only `stat` commands
  to prove the manifest-bound enable/latch paths absent. Rollback health does
  not misclassify a recovered V2321 solely because a candidate marker exists.
  Every Native response is paired in the adapter receipt with the exact command
  argument vector sent by that subprocess, so a generic or wrong-path ENOENT
  cannot prove either marker absent. The manifest and review both require one
  common generation stem, `enablePath` ending exactly in `.enable`, and
  `latchPath` ending exactly in `.done`.
- Candidate intent precedes its only launch. Rollback intent precedes its only
  launch. A candidate is never replayed after intent.
- All runs live under one fixed mode-0700 private A90 run root. After successful
  preflight, PREPARED first creates and fsyncs one permanent
  `candidate-<sha256>.guard` with `O_EXCL`; changing run ID or directory cannot
  prepare the same candidate again. A separate capability-wide
  `active-run.guard` serializes different candidate hashes and is released only
  after an exact healthy terminal (`PASS_A90_RESIDENT_INSTALLED` or healthy
  V2321 rollback) is durably published. `RECOVERY_REQUIRED`, uncertainty, and
  crashes leave it blocking. Approval also binds the run ID explicitly.
  PREPARED acquires the active guard before consuming the candidate guard; an
  ordinary pre-effect candidate-guard rejection releases only that newly
  acquired active reservation, so another active run cannot burn this candidate.
- Every record uses create-exclusive publication, file fsync, and directory
  fsync in a new mode-0700 run directory. Manifest and journal readers reject
  special/oversized paths before open, then bind one nonblocking descriptor,
  exact inode/size, bounded bytes, and absence of trailing growth. Journal
  presence comes from directory-entry names, not dereferencing `exists()`, so
  dangling allowlisted symlinks are malformed rather than silently absent.
- PASS requires candidate helper completion and quiescence plus fresh exact
  candidate health. Transfer success alone is not PASS.
- A rollback terminal is `NO_PROOF_ROLLED_BACK`, not experiment proof.

## The two journal paths

Only these paths and their prefixes are valid:

```text
PREPARED -> APPROVED -> CANDIDATE_INTENT -> CANDIDATE_LAUNCHED
 -> CANDIDATE_RESULT -> TERMINAL

PREPARED -> APPROVED -> CANDIDATE_INTENT -> CANDIDATE_LAUNCHED
 -> CANDIDATE_RESULT -> ROLLBACK_INTENT -> ROLLBACK_LAUNCHED
 -> ROLLBACK_RESULT -> TERMINAL
```

An unknown file, missing middle record, wrong event kind, mixed manifest
digest, or second execute is rejected.

## Crash rule

The minimal lane prefers a bounded manual stop over a general-purpose resume
engine:

| durable prefix | only allowed interpretation |
| --- | --- |
| `PREPARED` only | no device effect occurred |
| candidate intent or launch without terminal | candidate is consumed; never resend it; rollback-only assessment |
| rollback intent without rollback launch | the same exact rollback may be launched once by a separately reviewed adapter |
| rollback launch without result | park; do not replay rollback |
| terminal | complete |

The future backend must not raise after it has dispatched an effect. It must
return a bounded `EffectResult`, including an uncertain result. A host process
loss after launch is handled only by the table above.

## Backend boundary

The small H0 adapter is
`workspace/public/src/scripts/server-distro/a90_boot_only_f1_adapter_v1.py`.
It uses only the existing A90 mechanisms:

- target and resident observation use the existing Native serial protocol;
- candidate and rollback transfer use the existing reviewed
  `native_init_flash.py` path;
- ADB remains recovery-scoped and is not owned or started by this runner;
- the adapter accepts no caller command, partition, device selector, retry
  count, or arbitrary path;
- the adapter returns exact target, effect, and final-health receipts to the
  state machine.

For the recovery transition, the adapter always selects the helper's new
fail-closed mode: every pre-existing non-recovery ADB endpoint is bound by
exact serial/state before the Native reboot request and must remain unchanged;
exactly one new recovery endpoint may arrive, and its serial SHA-256 must match
the private A90 qualification. It never accepts a caller-selected serial.
In that mode the Native `recovery` command and TWRP `reboot` command are each
sent at most once: post-send transport loss, busy state, or missing disconnect
is uncertainty and never an internal resend. Historical helper callers retain
their prior retry behavior.
The same minimal mode uses strict ADB inventory: command success, empty stderr,
the exact header, and every nonblank endpoint row must parse without duplicates.
Malformed output is never a stable baseline, a unique arrival, or proof that
TWRP disconnected after its one reboot request. Completion requires the exact
pre-existing ADB baseline to be restored.
The default helper behavior for historical callers is unchanged.

The adapter and the state machine together require one fresh independent full
execution-closure review before activation. Tests are review evidence, not
runtime dependencies.

## Deliberately removed

The retired owner made the experiment depend on a generated sealed source
package, FD loader, four-module contract/runtime/observer tree, and the entire
host Python installation: 7,313 files, about 168 MiB, and 282 dynamic
libraries. That did not better answer target/file/one-shot/final-health and
made ordinary host updates invalidate the capability.

This replacement therefore removes:

- candidate-specific review constants and self-referential review receipts;
- the generated source package and memfd execution loader;
- host Python tree and shared-library qualification;
- tests, reports, and historical H24 journals from runtime identity;
- a new ADB owner and generic multi-device orchestration;
- a general crash reconciler, retry scheduler, or arbitrary command layer.

The previous owner design and its hardening portfolio remain historical
evidence. They grant no authority and are not execution dependencies.

## Open gates

1. Prove the adapter's exact Native serial and recovery transfer inputs, helper
   quiescence, and result receipts.
2. Produce the H27 candidate-specific canonical manifest and its exact
   recovery/hazard qualification inputs; the schema and runtime binding are
   present, but no H27 run data or approval exists yet.
3. Freeze and independently review the resulting small execution closure.
4. Only afterward follow the A90 target contract for attended F1 approval and
   execution.

The two live-enable constants are now true so the exact activated bytes can be
reviewed. That code state alone grants no run: the candidate review/manifest,
fresh preflight-derived approval, attendance, and all contract gates remain
mandatory.
