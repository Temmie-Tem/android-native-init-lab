# S22+ ordinary route attach cue and original-A recovery

This H0 branch implements items 2–4 of the
[ordinary cue agenda](../plans/S22PLUS_MAINLINE_ORDINARY_CUE_AGENDA_2026-11-22.md).
An SCM task can use the ordinary evidence route with a dedicated review and
target adoption. The authenticated response is sealed before the observer
closes cue issuance. Rederivation checks the closure against this operation
and original window, with the closure timestamp at or after the sealed
response. Legacy SCM tasks retain their original review selection.

- The numbered absence census, the positive endpoint selection and cue
  issuance take the same operation-local lock. A positive census therefore
  becomes visible before a later cue check can select an older absence.
  Ordinary SCM and the existing UFS-link path share the observer helper.
- Before a new original-A dispatch, stopped-owner recovery closes further
  cue issuance under that lock and checks the existing reply. The approved
  terminal does the same before recording a continuation intent. A real
  completion or cancellation can settle a cue after the observation window.
  The fence ends cue issuance for this operation once original-A recovery is
  considered. The reply requirement is satisfied by the operator's recorded
  completion or cancellation, and the fence has no scope beyond the original
  owner.
  An existing A transfer intent continues through the existing raw-completion
  and health-only path.
- H0 close repair rederives the exact normal A and `android-final` when normal
  A and final health exist but the observation closure is unavailable. The
  resulting terminal describes the independently validated Android outcome.
  It does not synthesize a `recovery-health` result or replay any I/O.
- The ordinary and Download base readers require integer timestamps before
  comparing them. They convert the DT parser's `AuditError` into a validation
  failure with its original cause. Existing owner, intent and final-health
  checks still decide whether recovery is allowed.

The host regression suite passed 261 tests covering SCM routing and loopback
observation, late resolution, interleaved USB census publication, no-replay
recovery, H0 terminal repair, legacy Download and UFS socket flows, and the
approved terminal. A separate approved-terminal regression confirmed that
an unresolved cue blocks dispatch before intent publication, and that a
recorded cancellation permits the same original recovery. Python compilation
and the repository boundary check and its 12 tests passed. The SCM loopback
used synthetic evidence and the ordinary reader.

Independent review returned `PASS_GO` for this H0 change. The reviewer reran
142 cue, SCM, owner and terminal tests and found no open production issue.
The review covers the branch implementation and host regression evidence.

## SCM adoption and approved-terminal pre-application

The follow-up on `7a999cd1c6` adds the [SCM policy adoption](../operations/S22PLUS_MAINLINE_SCM_USB_V1.md)
and its dedicated source review for the ordinary `mainline-evidence` step.
The policy uses the existing attended physical attach procedure under the
S22+ target contract. The qualified SCM package and decoder were checked
offline against the retained task. Its operation was already consumed and
closed healthy. A future SCM run needs its own reviewed qualification, task
and finite attended approval. The current reader rederived the original
authenticated SCM result from its sealed capture with an exact match to the
retained result.

During pre-application testing, the existing publisher/close race exposed
a busy-lock failure when trying to save the operator's actual resolution.
Resolution now waits for the existing lock for up to one second. It still
publishes once, and a lock timeout leaves the resolution file absent. The
local wait can run after expiry without altering the observation or grant.
The held-lock success and timeout fixtures passed, as did 30 repetitions of
the original race test and 263 focused host regressions. The UFS capability
suite added 11 passing tests and six opt-in private-artifact skips. The
repository boundary checker and its 12 tests passed.

The v55 source refresh is a versioned v56 receipt. It changes nine pins in
the same 55-source list and retains both worker pins. The isolated branch
selects v56 using the canonical deployment paths. The main checkout still
validates its existing v55 selector and pins. Historical review and dispatch
receipts retain their bytes.

The independent review returned `PASS_GO` on the exact SCM and v56 source
sets for staged H0 adoption. The SCM task reader accepted the new scope in
offline normal and recovery validation, and the cue caller refused the old
review's scope. The v56 receipt matched every canonical source and selector
pin. In an isolated copy with local receipt paths, the real worker
initializer and status handler accepted v56 with zero device authority.
They refused v55 on the changed bytes, an old expected review, and an
altered source. The production socket and device endpoints were outside
this validation. A simulated merge with main `76e138439f` was clean,
and its tree reproduced both reviews, stable worker pins and selector hash.

The shared-source change also affects other task capabilities independently
of the gateway. The currently matching loader timing-v2 review would gain
ten source mismatches after cutover. When checked, the deployed checkout
had one `loader-android` owner tied to that review and no terminal record.
Its original-A recovery source check passed against the deployed checkout
and refused the proposed branch, which changes eight of its required
recovery pins. The existing owner later closed `ANDROID_CLOSED_HEALTHY`
on v55, and its F1 owner record was retired. The ten source mismatches still
apply to future timing-v2 tasks after a cutover.

The prepared ML053 V13 capability
already has six mismatches against the main checkout and has twelve on this
branch. The two older UDC reviews already have stale pins. A shared live
cutover must account for affected capabilities that remain in use, including
any original owner that still requires recovery. This branch refreshes the
SCM and gateway reviews. MAX77705 needs its own future review and adoption.

## Timing-v2 and ML053 compatibility review

The successor loader review replaces the ten mismatched pins in the same
89-source list. The selector is in the shared task reader so the loader
profile retains the exact bytes named by the timing qualification harness.
Both retained LOGM arms passed the actual timing image validation, package
check and new review source join in H0. The original timing-v2 review and
both closed task bindings were preserved.

The staged SCM and gateway reviews each refresh the one shared task-reader
pin on top of `35046aa8ed`. Both stable gateway worker pins remain identical.
Independent review returned `PASS_GO` for those two closures, the loader
successor and the staged ML053 V13 capability. The latter replaces 12 of
84 pins and retains all fixed fields and 467 evidence receipts. The real
qualification path recompiled the observer byte-for-byte, verified the
same AP, key and runtime, and passed the normal and recovery task readers
in isolation. The retained ML053 artifact was absent from both candidate
consumption indexes. This is H0 evidence and does not renew the old task.

The read-only operating inventory found 67 original dispatches with
verified healthy closure and no F1 owner. For supported vendor-native
tasks, the root-evidence, journal-recovery and Debian-autoboot reviews were
already stale in the deployed checkout. The staged cue changes added no
new mismatch paths for those reviews and the supported prepared vendor
bundles were closed. The two older UDC closures remain stale, with ML049
undispatched. The host suite covered loader, owner, SCM, gateway, UFS and
dialog paths, with 212 passing tests and six opt-in private-artifact cases
skipped. The repository boundary check and its 12 tests passed.

During verification `ec9980d397` installed a different v56 review on the
operating checkout for loader timing-v3. The running worker confirmed
that review. A merge simulation found conflicts in the immutable v56
receipt and its current selector. This branch retains the pre-transition
compatibility result for the earlier timing-v2 baseline. The operating
receipt and selector were left intact. A combined deployment needs a new
review that preserves timing-v3 and binds the shared cue sources together.
The timing-v3 change also updates `s22plus_native_target_io_v3.py`. The V13
retirement decision below governs the retained ML053 capability and candidate.

## Agenda item 5 cue dialog review

The optional helper was reviewed alongside the common caller. Both ordinary
SCM and UFS use the `mainline-evidence` step name. The helper's time origin
is its journal detection time on `CLOCK_MONOTONIC`. It can therefore
miss W+22 and keep the dialog open beyond the intended cutoff, even
though the fixed caller checks the sealed window under its operation lock.
A host fixture with detection 20 seconds after the true opening placed
the proposed dialog deadline at W+132. The helper also accepts historical
step starts and a success substring in failed caller output. Another
fixture showed that a nonzero result mentioning the success string
still opened the dialog.

An actual affirmative or cancel click can supply the operator's accepted
statement. Zenity exit 1 also means window dismissal, so the current
helper can record a cancellation the operator did not state.
[GNOME Zenity exit codes](https://raw.githubusercontent.com/GNOME/zenity/master/help/C/usage.page)

The helper remains on hold. Its separate review must use the current
operation and sealed BOOTTIME window, prove exact successful cue receipt
matching, stop on uncertain caller output, and distinguish both explicit
buttons from dismissal, timeout and display failure. The fixed caller's
typed resolution remains available for the reviewed gateway and ML053
paths.

## Integration hold and atomic adoption

The independent review of `35dc99a788` found nine stale terminal v56 pins
and ten stale loader timing-v3 pins on that tree. The timing-v3 cue receipt
refused both normal and recovery validation while its verdict was pending.
The terminal selector now binds the pending v57 receipt. The loader task
reader selects timing-v3 cue, and fresh ordinary SCM selects v2. Their
validators refuse pending verdicts before dispatch or recovery admission.

The terminal v57, timing-v3 cue and SCM ordinary-cue v2 closures now bind
150, 156 and 112 sources respectively. A host test traces real imports in a
fresh interpreter and checks source imports in selected lazy entries and
bound build files. It verifies all listed hashes and exercises the pending
and synthetic approved record sets as a unit. Loader recovery also checks
its eagerly imported Android storage helper. Both retained timing-v3 LOGM
arms passed full artifact and source validation with the synthetic review
fixture. A null retained request path now raises `ValueError` at the
observation boundary. Host fixtures reach the original-A decision for a
stopped owner and reuse recorded normal final health during H0 close repair.
The final host run outside the sandbox passed 311 tests with zero failures
and six skips for opt-in private UFS artifacts. The repository boundary
checker and its 12 tests passed.

The cue parent's staged v56 `PASS_GO` receipt is preserved byte-for-byte as
[`s22plus_approved_terminal_persistent_v56_cue_superseded.json`](../../workspace/public/src/device-action/bindings/s22plus_approved_terminal_persistent_v56_cue_superseded.json).
It matches the v56 review blob in `a5ece6a6cb`, SHA-256
`5bf62aa60cfe3116ca1caac818743c23c8c3ed326d392e2a5e29dc2b3628ab37`.
The published main v56 and loader timing-v3 receipts remain at their
original paths.

**Adoption commit `Adopt S22+ ordinary cue and timing-v3 review set`.**
The branch must wait for this single commit before integration into
`main`. The reviewer creates it as one squash commit on the then-current
`main` tip, so the pending tree never enters main's history. The commit
includes the integrated sources and the following four binding files under
`workspace/public/src/device-action/bindings/`.

- `s22plus_approved_terminal_persistent_v57_review.json`,
  `s22plus_loader_android_timing_v3_cue_review.json` and
  `s22plus_mainline_scm_ordinary_cue_v2_review.json` all carry the independent
  `PASS_GO` verdict and exact reviewer attribution for the final source
  bytes. Any bound source change on the final base must be checked against
  the review before adoption.
- `s22plus_approved_terminal_persistent_current.json` binds the canonical
  v57 path and the SHA-256 and size of the final approved v57 receipt. The
  same commit includes the loader timing-v3 cue and SCM v2 selections in
  the task reader and profile. Verify the gateway and both task selections
  with their final bytes, including loader recovery mode.

Before cutover, finish every used task bound to the original timing-v3
review with the original reviewed `s22plus_mainline_task_v1.py close`
command. Require a matching task-level `closed.json` even for direct-CLI
runs without a gateway dispatch. A healthy operation-level `terminal.json`
can retire its F1 owner before this task close. Keep the original review
usable through publication of the task closure. A preparation with no
effect does not require a healthy return receipt. A charged operation with
no effect requires its matching durable `unused.json`.

Before applying the adoption commit to the operating checkout, hold its
existing terminal admission lock and target session lease. Confirm all
issued dispatches are closed and no original-A or final-health work remains.
Require all mainline RAM tasks, including V13, to be quiescent. The checker
names open grants, operations without a joined task close or a proved
unused closure, and staged gateway approvals that the original dispatcher
has yet to consume. Resolve those records on their original reviewed
checkout before switching. Finite expired grants by themselves carry no
current authority. Their operation and approval records still apply.
Under those locks, run the read-only
[`s22plus_ordinary_cue_cutover_h0.py`](../../workspace/public/src/scripts/analysis/s22plus_ordinary_cue_cutover_h0.py)
from the isolated worktree with `--operating-root` set to the old checkout
and `--adoption-commit` set to the exact reviewed squash commit. It checks
the original timing-v3 pins and the joined closures from private operation
records, including direct-CLI runs. It also requires the adoption commit to
be the direct single-parent child of the operating HEAD. It copies the
proposed Git blobs to a disposable directory and runs that tree's production
gateway and task validators there. It checks the full gateway closure, the
timing-v3 selection in normal and recovery modes, and the ordinary SCM
selection. The canonical gateway receipt paths are relocated only in the
scratch copy after verifying the original selector pin.

Before switching, the checker compares every successor-pinned path's
operating bytes with the old HEAD, including sources unchanged by the
squash. It also checks the affected index entries and requires successor-only
paths to be absent from the operating checkout. An edit on a newly pinned
source can survive the squash, so an uncommitted difference holds cutover.
The check is scoped to this one adoption. Keep the locks through the
switch. If an owner or an uncertain dispatch remains, defer adoption and
keep the original checkout through verified
closure. Prepare fresh tasks with the adopted receipts. The adoption commit
has no hash yet because it depends on the independent verdict.

### V13 retirement at cutover

Cutover retires the V13 capabilities bound to pre-cutover sources, including
ML053. The shared cue interlock and recovery corrections apply to UFS and
change its reviewed source closure. Keep the original capability, candidate
qualification, task, approvals, grants, reviews and artifacts as evidence.
Before any later V13 run, require a fresh capability and independent review
for the adopted sources, a fresh candidate qualification and task, and a
fresh pre-approval audit and D0 on that task. The existing attended approval
and recovery conditions apply to the new run.

The lifecycle fixtures held cutover on an open V13 grant and an unclosed
operation, then passed after the matching task close. A separate fixture held
on a staged mainline approval and on its unresolved dispatch. The socket-free
suite passed 262 tests with zero failures and six opt-in UFS artifact skips.

The ordinary and Download observers now share receipt-path validation.
Joined, socket-free fixtures exercise both stopped-owner recovery and H0
repair for ordinary and UFS observations. With the old receipt reads,
all four regressions reproduce the null-path `TypeError`. With the fix,
the owner reaches its existing original-A decision without replay.
The socket-free rerun passed 258 tests with zero failures and six opt-in
UFS artifact skips. Socket-dependent fixtures were excluded from that run.

The cutover checker regressions accepted a complete synthetic approved
set and rejected a missing selector schema, an incomplete gateway closure,
a loader recovery refusal and an uncommitted edit to the unchanged
`s22plus_debian_handoff_profile_v1.py` source. The final socket-free rerun
passed 260 tests with zero failures and six opt-in UFS artifact skips.
