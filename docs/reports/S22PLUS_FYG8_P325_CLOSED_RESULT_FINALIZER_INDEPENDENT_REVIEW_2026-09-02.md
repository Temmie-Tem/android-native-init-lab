# S22+ FYG8 P3.25 closed-result finalizer independent review

Date: 2026-09-02 KST

Target: `SM-S906N` / `g0q` / `S906NKSS7FYG8`

Verdict: `PASS_P325_CLOSED_RESULT_FINALIZER_INDEPENDENT_REVIEW_HOST_ONLY`

Secondary state: `CURRENT_TREE_REAUDIT_FAIL_CLOSED_P326_SOURCE_DRIFT`

## Scope

This is a host-only, read-only review of
`workspace/public/src/scripts/revalidation/s22plus_fyg8_p325_closed_result_finalizer.py`
at the scope applied to the P3.24 finalizer. It does not re-derive the P3.25
scientific result, does not approve any live capability, and creates no D0, D1,
F1, recovery, replay, or device authority. P3.25 remains consumed and never
replayable.

The review exists because P3.24's equivalent review found a real defect: the
audit-only path used the common repairing `Journal.reopen` and therefore
rewrote identical journal-head bytes while changing inode and timestamps. With
public visual evidence now being attached to this campaign, leaving P3.25
without the same check was an avoidable asymmetry.

## Finding 1 — the P3.24 repair is preserved

`_read_only_journal()` constructs `core.Journal(path, binding)` directly and
calls `.records()`. It never routes through `reopen`, so the repairing path is
not reachable from it.

`_validate_result()` replaces `core.Journal.reopen` with a read-only classmethod
for the duration of `live.validate_live_result(...)` and restores the original
in a `finally` block, so the frozen live-result validation cannot reach the
repairing path either. `live._state` is stubbed and restored the same way.

`reconstruct()` reads the transaction journal through `_read_only_journal()` and
checks `state() == "CLOSED"`, 19 records, terminal sequence 18, and the exact
terminal record SHA-256 before proceeding.

## Finding 2 — the audit-only path publishes and validates nothing

In `finalize(audit_only=True)` with the result already present, control flow is:
`reconstruct()`, then `_stable_bytes(RESULT_PATH, ...)` compared against the
reconstructed payload, then return. `_publish()` is not called and
`_validate_result()` is not called. The audit path is read-only by construction,
which is a stronger position than P3.24's, where the read-only journal view was
what made the audit safe.

The module contains no ADB, USB, Odin, backend, `subprocess`, reboot, or
Download primitive. The returned record carries `device_contact`,
`adb_invoked`, `usb_revalidated`, `odin_invoked`, `candidate_transfer`,
`rollback_transfer` and `live_authorized` all false.

The publication path, which this review did not exercise because the result is
already published, opens a temporary file, `os.fchmod`s it to `0o400`, writes,
fsyncs, places it atomically, and unlinks the temporary on failure.

## Finding 3 — current-tree re-audit stops fail-closed on P3.26 source drift

A forced `--audit-only` run on the current tree stopped at
`FAIL_CLOSED / live_source identity differs` before any file was opened for
writing.

`EXACT_FILES` pins the shared runners at the identities they had when P3.25
closed:

| pinned file | P3.25 pin | at `0706b93c30` | current tree |
|---|---|---|---|
| `device_action_f1_live_v2.py` | 266,773 / `e9504fa1…` | 266,773 / `e9504fa1…` | 276,379 / `8301f090…` |
| `device_action_f1_v2.py` | 96,984 / `e01b5856…` | 96,984 / `e01b5856…` | 100,820 / `9b499dcb…` |

The pins match the P3.25 close snapshot exactly. The drift is entirely from the
P3.26 work, which added P3.26 branches to those shared runners. The fail-closed
stop is the intended behaviour: the finalizer refuses to audit a frozen run
against changed verifier sources rather than auditing silently against different
code.

## Finding 4 — the failed run mutated nothing

Full metadata was captured before and after the forced audit for all 22 retained
P3.25 evidence objects: the 20 files under `transaction/`, `live-state.json`,
and `live-result.json`. Every object was identical afterwards in inode, size,
mtime, ctime, mode, link count, and content digest. `live-result.json` remains
33,677 bytes, mode `0400`, single-link.

## Consequence

P3.25's closed live result is unchanged. Candidate transfer, the exact 49-byte
ACM arrival, rollback, and final rooted FYG8 health remain proved by the F1
`CAMPAIGN_CLOSED` row and are not affected by this review.

What is now unavailable is narrower: P3.25 is **not re-auditable in place from
the current tree** without reconstructing the exact close-time source
environment. This is not evidence loss and not a finalizer error. The exact
close-time sources are preserved in Git at `0706b93c30`, and the run evidence is
preserved under `workspace/private/`, but those two preservation domains cannot
be combined from a current checkout because the private evidence is not carried
into a historical worktree.

Restoring in-place re-auditability is deliberately **not** treated as a
prerequisite for the current publication. It is a provenance and reproducibility
convenience, and forcing it now would add machinery to close a gap that costs
nothing today.

## Successor note

From the campaign after P3.26, a close should additionally retain one
reproducibility receipt binding the campaign close to its exact verifier
commit/source identities, the private evidence bundle identity, and the re-audit
recipe. P3.25 is not retrofitted into that scheme.
