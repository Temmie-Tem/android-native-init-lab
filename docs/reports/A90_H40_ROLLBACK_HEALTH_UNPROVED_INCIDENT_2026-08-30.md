# A90 H40 Rollback Health Unproved Incident

Date: 2026-08-30
Scope: exact A90 H40 run `a90-h40-f1-20260830-01`
Classification: `RECOVERY_REQUIRED / ROLLBACK_HEALTH_UNPROVED`

## Durable evidence

- Manifest SHA-256: `a6c101fb2dfa0ad85bba1b73d1ebf9fcf973d46aaaf1e0f11981aba8fcf61ceb`.
- Candidate SHA-256: `68e12101e151f9515f2cf519f2749a8c1218e6c79a49aa4c9fcadd96b0728db0`.
- Candidate result records exact boot write/readback and confirmed System return.
- Failed-boot evidence is `NO_PROOF_OBSERVER / NO_RECOVERY_ENDPOINT`; it proves
  neither H40 runtime success nor device-attributable failure.
- Rollback SHA-256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- Rollback evidence records exact boot write/readback and confirmed System
  return, followed by host-side final-health failure
  `invalid minimum read budget: 0.25`.
- The terminal record has no health snapshot and closes as
  `RECOVERY_REQUIRED` with reason `ROLLBACK_HEALTH_UNPROVED`.
- The active-run guard and exact H40 candidate guard remain present.

Private raw evidence remains under
`workspace/private/runs/a90-boot-only-f1-minimal-v1/`; it is not tracked.

## Interpretation

The exact V2321 rollback transition is recorded, but a transfer result and
System return are not final resident health. The observer stopped on a host
validation error before it could prove the returned version, boot identity,
self-test, status, and stable exact-target inventory. Current resident identity
and health therefore remain unproved.

H40 boot, playback, cleanup, rollback health, and final health are not promoted.
The candidate and rollback are both one-shot consumed and must never replay.

## Recovery boundary

This report creates no live authority. The current target contract contains no
H40-specific continuation. Any future connected observation or recovery must
be independently reviewed, bind the exact retained journal and guards, permit
no new candidate or rollback transfer, and publish final health before releasing
the active guard. Until then, the exact A90 remains parked at
`RECOVERY_REQUIRED / ROLLBACK_HEALTH_UNPROVED`.
