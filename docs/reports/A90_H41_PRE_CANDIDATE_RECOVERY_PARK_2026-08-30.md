# A90 H41 Pre-Candidate Recovery Park

- Date: `2026-08-30`
- Run: `a90-h41-f1-20260830-01`
- Classification: `RECOVERY_REQUIRED / RECOVERY_NOT_PROVED`
- Candidate runtime: `unproved`

## Durable boundary

- Preparation proved exact healthy V2321, the H41 fresh paths absent, exact
  rollback/recovery inputs, and sole-A90 isolation.
- One attended approval was consumed.
- One Native Recovery request was sent after durable
  `11-recovery-transition-intent.json`.
- No Recovery endpoint was proved before the bounded wait ended.
- The journal closed this invocation with
  `13-recovery-transition-parked.json`.
- Candidate guard publication, candidate intent, candidate helper launch,
  candidate bytes, and rollback bytes are all absent or zero.

## Interpretation

H41 was not written and did not boot. Its Bad Apple behavior remains unproved.
The Recovery request and original run approval are consumed and never replay.
The active guard remains because current V2321 health has not yet been freshly
proved after the transition attempt. The H41 candidate guard is absent.

## Recovery

Run-01 used the fixed read-only park closer and returned to exact healthy
V2321. Run-02 repeated the pre-candidate park, but the exact A90 later appeared
as sole bound TWRP after a cable reconnect. A separately reviewed run-02
continuation may inherit that late Recovery without resending the consumed
request, write H41 once, open an explicitly unproved manual demo window, and
write exact V2321 rollback once. It retains no other authority. Until that
review and fresh approval, no H41 write is authorized.
