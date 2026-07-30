# S22+ FYG8 P2.88 pair-attributable restart F1 closed

Date: 2026-07-30 KST

Tier: F1

Status: `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`

Transaction: `CLOSED`

Recovery required: false

## Result

One exact P2.88 boot-only candidate and the exact Magisk boot-only rollback
were transferred once each. The operator observed a normal candidate boot
without a boot loop. The exact CDC-ACM observer timed out, and the retained
record did not advance into any new P2.88 pair-indexed position.

The two post-rollback retained reads are byte-identical. They contain one exact
P2.88 run record with two CRC-valid slots:

```text
generation 87: stage=0x8e item=0 outcome=progress detail=0
generation 88: stage=0x8f item=0 outcome=progress detail=0xc18
active: generation 88
classification: E2_PROGRESS_OBSERVED
```

There is no generation 89 write, terminal success, terminal failure, UNSAT
record, fallback record, foreign record, partial record, or integrity issue.
The formal result is therefore no-proof rather than candidate failure or
success.

## Bound identities

- P2.88 run ID: `20bb4d70842fe7ae1a6bd0aec261d722`;
- ready bundle SHA256:
  `6ca4898feac8a862d42713898c5417198e769d88c0e072c83019029436e241ed`;
- approval binding SHA256:
  `eb74178fc6c21adb77dc17da0a04ffd3bec975b3814c9f763a4d0ac42f9efec5`;
- candidate AP SHA256:
  `14acdb0820329ab931b7b4b568778a9442c7f85662d4a7f502393c3e91ff6f95`;
- rollback AP SHA256:
  `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`;
- live result SHA256:
  `aad16a9d572c5cbfd84d319f123e1100392ada70cc208b4400ed112e62a80f7d`;
- retained-read SHA256:
  `34f5df7414b0c1f992372abe1c68e3d026da92d30e8a636e12ad3403998a4a34`.

The production `validate_live_result()` path reopened the prepared binding,
journal, transfer receipts, observer evidence, live state, final health, and
timeline without discrepancy.

## What the retained result proves

The P2.88 generation-88 record retains the strengthened P2.86 meaning. Exact
source order withholds it until normalized NONE readback, synchronous child
suspend, zero-return PHY power helper, exact child `suspended`, and exact
parent `runtime_status=suspended` have passed.

It does not prove the first P2.88 generation-89 publication, restart-helper
dispatch, restart-helper return, subsequent readback, trace capture, configfs
bind, final sampling, ACM enumeration, or terminal E3 success.

Removing the two early classification-only trace snapshots therefore did not
produce a surviving first successor coordinate. The next H0 must localize the
exact generation-88-to-89 producer corridor without assuming that absence of
generation 89 means the helper itself ran.

## Candidate observer

The candidate observer closed as `endpoint-timeout`. Its exact match includes
the prepared S22+ physical topology, VID, PID, synthetic USB serial,
`cdc_acm`, and interface `00`.

An attached A90 exposed the same `04e8:6861` VID/PID and the same driver and
interface, but differed in physical topology and serial. A live pre-execution
scan found zero exact candidate endpoints and zero same-topology
candidate-like endpoints. The A90 was not an accepted P2.88 endpoint.

The timeout is consistent with the retained record stopping before the first
new restart coordinate, but it does not identify the blocking primitive.

## Recovery deviation

The initial execution stopped while recording the physical rollback Download
endpoint because USB membership changed during a measured snapshot. Durable
state was already `OBSERVED`, so recovery reopened the journal without any
candidate replay.

The first rollback-only recovery transferred the exact rollback once and
durably recorded `ROLLBACK_FLASHED`. It then stopped when the completed
transfer removed the Download USBFS node during another measured inventory
snapshot. The persisted diagnostic class is
`inventory-membership-changed`.

A final recovery reopened `ROLLBACK_FLASHED` and performed no transfer. It
completed Android return, final health, retained reads, and transaction close.
Thus:

- candidate transfer count: one;
- rollback transfer count: one;
- candidate replay: none;
- rollback retransmission: none;
- final Android/Magisk health: pass; and
- recovery required after close: false.

This is the same post-transfer USBFS membership-race hazard class observed in
the closed P2.86 transaction. Durable transfer receipts prevented a completed
transition from being repeated.

## Final health

Final evidence proves exact FYG8 Android boot completion, stopped boot
animation, Magisk root, expected kernel, boot and supporting-partition
identities, verified-boot state, Download endpoint absence, and the canonical
eight Process-v2 events in order.

The approval binding is consumed. No S22+ F1 authority remains, and P2.88 must
not be replayed.

## Next H0

1. Audit the exact production path from accepted generation 88 through the
   first generated generation-89 publication call.
2. Prove whether the call is reached, whether the client derives the expected
   pair, and how a publication error reaches the evidence-park invariant.
3. Reconcile generation 87 `0x8e/detail=0` being accepted while its P2.88
   semantic rendering still labels detail zero `invalid`.
4. Keep candidate observer timeout as downstream corroboration, not a root
   cause.
5. Do not design or build a successor until this corridor is closed H0.
