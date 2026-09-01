# Shared closed-result publisher

Date: 2026-09-02 KST

Scope: host-only. No device, ADB, USB, Odin, transfer, rollback, replay or live
authority is created, and no consumed run is republished or altered.

## Why

Four consecutive S22+ runs closed healthy on the device and then stopped in the
ordinary host publisher because their canonical `live-result.json` exceeded the
shared 32 KiB record bound:

| run | canonical result | over the bound by |
|---|---|---|
| P3.23 | 34,937 B | 2,553 B |
| P3.24 | 38,558 B | 6,174 B |
| P3.25 | 33,677 B | 909 B |
| P3.26 | 33,879 B | 1,111 B |

None of these blocked an experiment. Each was resolved after the fact by writing
a run-specific finalizer, and each of those cost a script, focused tests, an
independent review, a ledger row and a report. Four copies now exist, totalling
roughly 1,900 lines that are largely the same procedure.

The copies also drifted, and that is the part that matters. P3.24's review found
that auditing through the common repairing `Journal.reopen` rewrote identical
journal-head bytes and moved the retained evidence's inode and timestamps. The
repair reached P3.24, P3.25 and P3.26. It did not reach P3.23, which still
carries the defect, because P3.23 is a separate file that nobody had reason to
revisit. That was found only because the P3.25 finalizer review happened to look.

## What this is not

It is **not** a wider record bound. `MAX_RECORD` stays at 32 KiB and the live
path is unchanged. Widening it would widen every live and intermediate record,
which would dissolve the meaning of the bounded-record model.

What changes is that the bound becomes lifecycle-scoped. A canonical result
reconstructed from an already-`CLOSED` run may be published under a separate
`MAX_CLOSED_RESULT` of 64 KiB, and only then.

```
live / journal / intermediate records
              max 32 KiB
                   |
                   v
            CAMPAIGN_CLOSED
                   |
                   v
      canonical closed result
              max 64 KiB
        host-only publication
```

## Invariants and where they are enforced

| invariant | enforcement |
|---|---|
| the live bound is untouched | `MAX_RECORD` unchanged; the loaded runtime is checked to still report 32 KiB |
| the 64 KiB path is unreachable from the live path | one-way dependency: the publisher imports the runtime, and a test asserts no runtime source names the publisher |
| nothing before `CLOSED` | `reconstruct` checks journal state, record count, terminal sequence and terminal digest before deriving anything |
| the path cannot become the default | a payload that would have fit inside 32 KiB is refused outright |
| the journal is never repaired | `read_only_journal` constructs and reads without `reopen`; `_read_only_journals` replaces `Journal.reopen` for the duration of frozen result validation and restores it in a `finally` |
| exact run and source identity | every pinned input is checked by size and digest, before and after reconstruction |
| drift stops the run | any pinned-identity mismatch raises before any write |
| no reinterpretation | the result is assembled from stored state, the stored projection and the stored terminal classification; expectations are compared, never computed |
| atomic, exclusive, 0400 | `O_EXCL | O_NOFOLLOW`, `fchmod 0400`, fsync, link into place, directory fsync, then read back and compare |
| `audit_only` publishes nothing | the publish call is not on that branch, and a test compares inode, size, mtime and mode across an audit |
| no device path | the module imports no process or socket module and calls no process entry point |

## Equivalence

The generalisation is only correct if it produces what the run-specific
finalizer produced. Reconstructed from the exact P3.26 closed run, the shared
publisher emits 33,879 bytes with SHA-256
`a78a9c50c8242506e6f531cc3d48f5fcadbe19410b1da8a7fc5215847aef91b5` — byte
identical to the P3.26 finalizer's own output and to the result P3.26 published.
The `value` mappings are equal as well.

P3.25 cannot be compared on the current tree. Its finalizer pins the shared
runners at the identities they had when P3.25 closed, and P3.26 changed them, so
it stops fail-closed. That is the limitation already recorded for P3.25 and is
not a new one.

## Scope of adoption

This applies from P3.27 onward. P3.23 through P3.26 are historical evidence and
are not republished, and their finalizers are not rewritten against this module;
doing so would alter the tooling of consumed runs and would need its own review.

P3.23's finalizer keeps its unrepaired defect but no longer runs: its CLI entry
now refuses with `REFUSED_RETIRED_FINALIZER` rather than mutating P3.23's
retained evidence. The guard is on the entry point, not the module, so the file
stays readable and its tests still load it.

## Successor note

From the campaign after P3.26, a close should also retain one reproducibility
receipt binding the campaign close to its exact verifier commit and source
identities, the private evidence bundle identity, and the re-audit recipe. That
is what would have let P3.25 stay re-auditable after P3.26 moved the shared
runners. P3.25 is not retrofitted into that scheme.
