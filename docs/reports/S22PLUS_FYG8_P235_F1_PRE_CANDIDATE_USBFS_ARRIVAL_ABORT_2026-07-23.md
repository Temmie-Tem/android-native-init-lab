# S22+ FYG8 P2.35 F1 pre-candidate USBFS arrival abort

Date: 2026-07-23 KST
Tier: F1 stopped before candidate transfer, followed by one bounded D1 reboot
Status: `FAIL_F1_V2_PRE_CANDIDATE_DOWNLOAD_RETURNED_HEALTHY`
F1 authority: consumed; none active

## Result

The exact prepared approval binding was accepted and execution-time D0 passed.
The adapter requested Android Download mode and durably reached `APPROVED`.
Endpoint polling then persisted 11 empty Odin snapshots and stopped with
`OdinTransitionError` before `DOWNLOAD_IDENTIFIED` or
`candidate_flash_start`. The structured result is:

```text
verdict=FAIL_F1_V2_PRE_CANDIDATE_DOWNLOAD
state=ABORTED
candidate_classification=not-attempted
candidate_completed=false
rollback_completed=false
recovery_required=false
```

No AP path was passed to Odin and no partition transfer occurred. The exact
approval and transaction are consumed and cannot be reused.

Immediately after the abort, the target was present as one Samsung Download
endpoint and `odin4 -l` returned one usbfs path. The operator then explicitly
authorized a bounded no-payload return. `odin4 --reboot` completed without an
AP argument. A separate connected read-only D0 run passed Android boot, stopped
boot animation, FYG8 kernel identity, Magisk root, supporting-partition
identity, Odin-endpoint absence, and a clean retained baseline with zero P2.34
marker families.

## Root Cause

The durable adapter recorded only the normalized exception type, so the exact
inner exception message is not available. The source path and timing isolate a
matching execution gap: the measured USBFS observer treated a node that arrived
between its baseline inventory and the Odin/after-inventory sample as a fatal
membership change. This is an expected edge of endpoint-arrival polling, not
evidence that the candidate or rollback transfer failed.

The first attempted fix covered only the legacy identity callback and was not
sufficient for the measured observer used by F1. Review also rejected an early
version that could retry before scanning compound ambiguity. The final change
classifies a retryable arrival only when all baseline USBFS nodes retain their
immutable identity and exactly one node was added. The transition core converts
that typed condition to a bounded retry only when Odin output is empty or names
exactly that added node. Multiple endpoints, an existing live endpoint plus an
arrival, replacement, removal, unrelated membership changes, terminal absence,
and ticket revalidation remain fatal.

## Validation

- Python compilation passed for both changed modules and focused tests.
- Transition, measured USBFS, F1 adapter, evidence, and manifest tests:
  152 passed.
- Independent `gpt-5.6-sol` high-reasoning review of the final measured closure:
  `GO`, no findings.
- `git diff --check` passed.

## Next Gate

The prior manifest and prepared binding name the old execution closure and are
not reusable. A later candidate attempt requires a fresh host closure, a new
connected D0 preparation from the clean healthy state, and a fresh exact
approval. This report grants no live authority.
