# S22+ FYG8 R4W1-E E1 Process v2 typed evidence host pass

Date: 2026-07-22 KST
Target: `SM-S906N/g0q/S906NKSS7FYG8`
Tier: H0 only

## Verdict

`P2_10_HOST_GO`

Process v2 can now validate the exact P2.9 E1 offline contract and classify the
R4W1-E retained A/B checkpoint without a candidate-specific runner. No device
was contacted, D0 was not run, Odin was not invoked, no partition was written,
and no F1 authority was created.

## Change

The reusable evidence module adds one allowlisted acceptance kind:
`retained_checkpoint_after_rollback`. It pins the P2.9 run manifest and static
checker result, recomputes the canonical run ID, and binds that identity to the
exact boot-only AP already qualified in P2.9. The evidence helper and checkpoint
decoder are part of the approval-bound execution closure.

The existing `retained_marker_after_rollback` path retains its original schema
and classification behavior. There is no change to Download discovery, Odin
transport, the durable state machine, rollback, or final-health logic.

## Acceptance

A live observation can pass only when the post-rollback observer contains:

- exactly one complete R4W1-E carrier entry and no duplicate or partial family;
- the P2.9 manifest-derived run ID;
- E1 terminal stage `63` with success outcome;
- two valid A/B slots with adjacent generations; and
- a saturated, self-consistent boot identity across both slots.

Progress, explicit failure, stale run ID, one-slot CRC fallback, corrupt
committed slots, truncated regions, or family ambiguity cannot pass. The
connected D0 path must separately prove the family absent before approval.

## Validation

The focused execution-closure suite passes 62 tests. It covers the old marker
path, exact terminal success, progress and failure, changed run ID, duplicate
and partial families, corrupt latest-slot fallback, one-valid-slot rejection,
offline artifact binding, draft refusal, ready-manifest data-only promotion,
and the existing Process v2 core/live regressions.

The broader Process v2, D0, Odin/USBFS, and R4W1-E P2.7-P2.10 integrated
suite passes 175 tests. Python byte-compilation, offline live-adapter
validation, plan rendering, and `git diff --check` also pass.

Independent H0 review first found only four stale immutable bundle test hashes
after the helper closure changed. The hashes were recomputed from the finalized
bytes, the same 62 tests passed, and follow-up review returned
`P2_10_HOST_GO`.

## Limits

- This result does not prove E1 boot or runtime behavior on the device.
- It does not prove retained checkpoint publication or final Android health.
- It does not authorize F1.
- The next action is one connected read-only D0 preparation using the exact
  ready manifest, followed by a stop at the fresh approval token.
