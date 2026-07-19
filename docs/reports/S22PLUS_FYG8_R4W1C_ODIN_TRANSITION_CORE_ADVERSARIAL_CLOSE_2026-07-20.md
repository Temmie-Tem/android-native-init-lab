# S22+ FYG8 R4W1-C Odin Transition Core Adversarial Close

Date: 2026-07-20 KST

## Verdict

`PASS_R4W1C_ODIN_TRANSITION_CORE_ADVERSARIAL_CLOSE_HOST_ONLY`

The target-neutral Odin endpoint evidence core is ready to commit and reuse by
a future, separately reviewed target helper. Five independent read-only review
rounds were completed. The first four returned `NO-GO`; the fifth returned
`GO`. Every blocking finding has a direct implementation change and regression
test.

This is an evidence-only core. It contains no transfer API, target pin,
confirmation prompt, consumed-state policy, or live authorization. No device was
contacted and no image, USB state, partition, or policy was changed.

## Final Sources

```text
workspace/public/src/scripts/revalidation/s22plus_odin_transition_core.py
  size    52557
  SHA256  ab418aac5ce4c854f433e2132bd9536a610991384ec82c50dc0ba063f1888a9b

tests/test_s22plus_odin_transition_core.py
  size    63492
  SHA256  560a6cefd2b4a6fcbe63be27fa06073a4c57eba0a95e9f7e7f2c81792f9ac376
```

## Review Closure

Review 1 rejected weak generation binding, misleading immutability claims,
missing writer exclusion, loose bounds, and permissive endpoint parsing.

Review 2 rejected per-call rather than whole-transaction locking, a
publish-before-seal crash gap, incomplete reverse reconciliation, stdout/stderr
token synthesis, imprecise deadlines, child cleanup gaps, and tests that did not
exercise the claimed branches.

Review 3 rejected non-finite time inputs and lost remaining budgets, incomplete
directory durability around visible orphans, externally forgeable or expired
leases, public ungated mutation, incomplete receipt/index bounds, and a weak
child cleanup assertion. It also identified the remaining USB attribution race.

Review 4 rejected post-only USB identity checks, receipt publication before
serialization of the actual derived index record, a lease inherited across
`fork()`, finite deadline overflow, and the `FileExistsError` parent-directory
fsync gap.

Review 5 verified all five Review-4 fixes and returned `GO`. Its only LOW note
was missing direct coverage for a node newly appearing during `odin4 -l`. That
coverage was added before this close report.

## Final Contract

- A bounded pre-run `/dev/bus/usb` identity inventory is captured before the
  actual `odin4 -l` process runs.
- Every reported path is post-statted. Appearance, disappearance, or identity
  replacement during enumeration fails closed before a snapshot receipt.
- Stale output absent both before and after remains absence evidence, not a live
  endpoint.
- Exactly one stable live path can yield a generation ticket; ambiguity fails.
- Tickets bind path, node identity, generation, receipt path, and receipt SHA.
- A ticket is evidence only and never authorizes an Odin transfer.
- A nonblocking `flock` and registered PID/thread-bound lease cover the complete
  caller transaction. Forged, expired, cross-thread, nested, and fork-inherited
  leases are rejected.
- Receipt bytes and the actual derived index record are serialized and bounded
  before publication.
- Receipts use exclusive create, mode `0400`, file fsync, hard-link publication,
  and directory fsync on trusted host storage.
- One visible receipt orphan from the link/fsync or receipt/index crash window
  is re-fsynced, semantically revalidated, and indexed before progress.
- Snapshot count, receipt size, record size, segment size/count, and aggregate
  index size are bounded before mutation.
- Wall-clock inputs, clock results, and calculated deadlines must all be finite;
  enumeration receives only the remaining budget.
- The child enumeration process has bounded stdout/stderr capture and is killed,
  waited, and pipe-closed on timeout, overflow, or setup failure.

## Validation

```text
focused Odin transition core          61 passed
retired R4W1-B regression suite       94 passed, 3 skipped
reusable boot-only live core          12 passed
total                                167 passed, 3 skipped
py_compile                            PASS
ResourceWarning-as-error              PASS
git diff --check                      PASS
line length >100 scan                 clean
```

The three skips require build-host-only FYG8 kernel inputs and are unrelated to
this host core.

## Residual Boundary

The host run directory owner is trusted. Mode `0400`, hashes, and fsync provide
exclusive-create and crash-recovery evidence; they do not defend against a
malicious owner who deliberately chmods or rewrites files.

No host core can make a previously observed USB node an authorization token for
a later process open. A future helper must hold the transaction lease, perform
fresh same-generation revalidation immediately before a separately authorized
transfer, and pass the revalidated path only to that transfer call. Artifact and
policy gates remain outside this module.

## Next

Proceed host-only to a new M31B-derived R4W1-C watchdog carrier. The carrier must
load only the live-proven five-module closure, fail closed on every load error,
verify all five module names in `/proc/modules`, retain the exact R4W1-B kernel
witness contract, and park without USB/configfs, Android handoff, persistent
mounts, block writes, or reboot. A separate static checker must precede any
connected or live policy work.
