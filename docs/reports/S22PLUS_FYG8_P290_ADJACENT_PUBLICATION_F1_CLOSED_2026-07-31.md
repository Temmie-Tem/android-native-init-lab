# S22+ FYG8 P2.90 adjacent-publication F1 closed

Date: 2026-07-31 KST

Tier: F1

Status: `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`

Transaction: `CLOSED`

Recovery required: false

## Result

One exact P2.90 boot-only candidate and the exact Magisk boot-only rollback
were transferred once each. The operator observed a normal candidate boot
without a boot loop. The exact CDC-ACM observer closed as
`endpoint-timeout`.

The two post-rollback retained reads are byte-identical. They contain one exact
P2.90 run record with two CRC-valid slots:

```text
generation 87: stage=0x8e item=0 outcome=progress detail=0
generation 88: stage=0x8f item=0 outcome=progress detail=0xc18
active: generation 88
classification: E2_PROGRESS_OBSERVED
```

There is no generation 89 mutation, terminal success, terminal failure, UNSAT
record, fallback record, foreign record, partial record, or integrity issue.
The formal result is no-proof rather than candidate failure or success.

## Bound identities

- P2.90 run ID: `2ec2bbaeed33025c92a0831c5e82dd3b`;
- ready bundle SHA256:
  `978328a8c6cf54cc8f80f9f4764122ed12fddb51ad9d4f04821bec1be26b423f`;
- approval binding SHA256:
  `2263c3c77d3c2b6147330c107b15b3c8279fad25fa16261d63bb020c2ba8ecf5`;
- candidate AP SHA256:
  `4fb859bc980370ffd68704e31cfaaf3e06e908424cba996df9a39662302787b7`;
- rollback AP SHA256:
  `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`;
- live result SHA256:
  `02eb20d95ea8f150b707efb8eaa71c2477fe7b4cc8948310c8f4e7ff69e35481`;
- retained-read SHA256:
  `bc148c63ad339dd808c17909f733a9fee1451f9150043118787b05d9533619b3`.

The production `validate_live_result()` path reopened the prepared binding,
journal, transfer receipts, observer evidence, live state, final health, and
timeline without discrepancy.

## New attribution

P2.90 placed generation 89 at `(stage=0x8f,item=1)` immediately after the
accepted generation-88 publisher returns. There is no gate revalidation,
tracefs read, unrelated syscall, suspend return, restart entry, or helper
dispatch between the two publications.

The exact P2.90 retained image nevertheless matches the predecessor boundary:
generation 88 committed while generation 89 did not reach the target slot's
first persistent CRC clear. This rejects the P2.88 explanation that the first
new coordinate was merely too far beyond the unresolved corridor.

The result strongly localizes the stop to the generation-88 publication
return boundary. In the P2.90 contract's one-channel model, the remaining
class is a non-return after the generation-88 durable commit, before the
adjacent generation-89 publication can begin. A returned primary error would
have entered the checked fallback route, while a generation-89 attempt would
have invalidated or replaced the still-valid generation-87 target slot.

This does not identify the exact kernel instruction. It does establish that
restart-helper dispatch, restart entry, and deadline construction were not
reached.

## Candidate observer

The exact candidate observer closed as `endpoint-timeout` after its bounded
300-second window. An attached A90 had a different physical topology and USB
serial and was not accepted as the P2.90 endpoint.

The timeout corroborates the retained record stopping before generation 89,
but it is not the root-cause classifier.

## Recovery deviation

After observation closed, the first rollback endpoint inventory met the known
USB mode-transition membership race and stopped before any rollback transfer.
Durable state was already `OBSERVED`; candidate transfer count was exactly one.

The S22+ then appeared at the prepared physical topology as the exact Samsung
Download endpoint. Rollback-only recovery reopened the existing journal,
transferred the exact rollback once, and completed final health. It did not
replay the candidate or retransmit the rollback.

Thus:

- candidate transfer count: one;
- rollback transfer count: one;
- candidate replay: none;
- rollback retransmission: none;
- final Android/Magisk health: pass; and
- recovery required after close: false.

## Final health and authority

Final evidence proves exact FYG8 Android boot completion, stopped boot
animation, Magisk root, expected kernel, boot and supporting-partition
identities, verified-boot state, Download endpoint absence, and the canonical
eight Process-v2 events in order.

The approval binding is consumed. No S22+ F1 authority remains, and P2.90 must
not be replayed.

## Next H0

1. Audit the exact post-commit tail of the generation-88 retained writer and
   its procfs/VFS return path.
2. Distinguish a non-return inside the checkpoint write from a non-return in
   the immediate userspace publication tail without using the same retained
   channel as its own sole witness.
3. Keep the CDC-ACM timeout as downstream corroboration only.
4. Do not build or request another F1 until the generation-88 publication
   return boundary has a host-derived successor hypothesis.
