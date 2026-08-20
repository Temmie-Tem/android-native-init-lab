# A90 H28 TWRP System-return uncertainty incident — 2026-08-21

## Disposition

`H28 RECOVERY_REQUIRED / ROLLBACK_HEALTH_UNPROVED`.

The H28 candidate and exact V2321 rollback were each written and read back
exactly once. Neither image may be replayed. H28 kernel boot acceptance is
**unproved**, not refuted, because no candidate Native observation was reached.
The final boot-partition readback proves exact V2321 bytes, but V2321 health is
also unproved because the sole TWRP System-return request remained uncertain.

## Exact transaction

The fresh attended run was `a90-h28-f1-20260821-01`. Its connected preflight
proved exact healthy V2321, physical recovery availability, absent H28
enable/latch state, and no command to the other Samsung endpoint. The approved
owner then published candidate intent and launched H28 once.

The candidate helper proved:

- local and remote H28 SHA-256
  `aea34a96464affd2f7e6c30d237e2175940eef511e69c1452c9deab4833a521b`;
- one `58,372,096`-byte boot write; and
- exact boot-prefix readback matching H28.

Immediately before its only System-return request, the helper revalidated the
bound TWRP version and exact fixed reboot hook. That request returned an
uncertain outcome, so the helper did not resend it. The owner recorded a
quiescent incomplete candidate result and proceeded directly to its one exact
rollback attempt without candidate health inference.

The rollback helper reused the already-bound A90 recovery endpoint and proved:

- local and remote V2321 SHA-256
  `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`;
- one `60,882,944`-byte boot write; and
- exact boot-prefix readback matching V2321.

Its sole TWRP System-return request was also uncertain and was not resent. The
owner recorded a quiescent incomplete rollback result and closed
`RECOVERY_REQUIRED / ROLLBACK_HEALTH_UNPROVED`. Candidate and rollback transfer
counts are `1/1`; both replay flags are false by the durable journal.

## Current boundary

Canonical terminal record `40-terminal.json` is SHA-256
`400a6fe75ea54a738777092f828dede4d7b801bd3fbd8db29baddf26878c4f01`.
The exact H28 candidate guard and capability-wide active guard remain present.
Post-terminal USB inventory showed no A90 Native `04e8:6861` endpoint and two
generic Samsung `04e8:6860` endpoints. The owner did not issue another ADB,
TWRP, reboot, candidate, or rollback command and did not attribute either
generic endpoint after the terminal.

This is a TWRP return/observation incident, not evidence that the rebuilt
kernel boot-looped. The next action is not another F1. A separately reviewed
incident recovery must preserve both consumed image attempts, bind the exact
journal and current recovery identity, and either observe an already completed
V2321 return or authorize one bounded operator physical recovery continuation.
It must then prove fresh V2321 health before releasing only the active guard;
the H28 candidate guard remains consumed.
