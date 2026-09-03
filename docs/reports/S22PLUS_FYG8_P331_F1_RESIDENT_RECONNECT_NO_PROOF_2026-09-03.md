# S22+ FYG8 P3.31 resident-reconnect F1 no-proof

Date: 2026-09-03 KST

Target: `SM-S906N / g0q / S906NKSS7FYG8`

Tier: attended F1

Formal verdict: `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`

Outcome: `p331_authenticated_resident_heartbeat_unproved_rollback_verified`

## Outcome

P3.31 is closed and consumed. The exact boot-only candidate and exact Magisk
rollback each transferred once, the journal closed at 19 records, and final
rooted FYG8 health passed with `recovery_required=false`. There is no attempt
2, and P3.31 must never be replayed.

The candidate booted without a reported boot loop. The exact 49-byte P3.31
native-PID1 banner reached the raw-first observer, and the host emitted one
32-byte OPEN frame. This preserves the already established native-PID1
CDC-ACM device-to-host path and records host write progress for this run.

The first session timed out at `open-diagnostic-read`. No `OPEN_PARSED` or
`RNG` diagnostic, challenge, HMAC authentication, heartbeat result, clean
session close, or reconnect was observed. The declared two-session resident
precursor is therefore unproved; normal boot does not change that result.

## Exact closure

- candidate AP: 28,631,081 bytes, SHA-256
  `729b33c3bad602e1d5863fa8cfa6a4bdf22f194a74d378f7417879897bf4d08d`;
- exact Magisk rollback AP: 23,367,721 bytes, SHA-256
  `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`;
- candidate transfer result: 2,079 bytes, SHA-256
  `9cbef6d3084a8ee03d8ff863090000fabd273873403621d117389b5c0efa488d`;
- rollback transfer result: 2,030 bytes, SHA-256
  `55d957f43f08a3a837627409870757e2972ad30e77d716f53ef75caf1994abd5`;
- final live state: 12,605 bytes, SHA-256
  `e17a3e03a0132d910ec8921a7a93c4d1d5ad56bec1e0ea15bd63c7081715d1a5`;
- final live result: 15,182 bytes, SHA-256
  `172952c9ef7f0efb08dc516dd15a2b2565044c1d2911b82f3625d984e989acdf`.

The final state records `candidate_completed=true`,
`rollback_completed=true`, and `final_verified=true`. Final health verifies
boot completion, stopped boot animation, root, the expected boot and
supporting-partition identities, and absent Download mode.

## Candidate observation

- raw device-to-host bytes: 49 bytes, SHA-256
  `99eab40ec9d0d1d61164a89b0746ca56fee317b50dc40afb04c000709661425a`;
- host-to-device bytes: 32 bytes, SHA-256
  `ab8a5c732b2eca5a077435553c49057e0fb5a399cf701e8166f0cc0292a21797`;
- candidate observer receipt: 6,733 bytes, SHA-256
  `9af34b3d821314c70d97b754137f788e7a20fc15cf285911eea7b099c9221094`;
- observer classification: `authenticated-session-error`;
- partial session: index 0, `TimeoutError`, stage
  `open-diagnostic-read`;
- sessions attempted/successful/reconnected: `1/0/0`.

The raw bytes equal the exact P3.31 banner. The retained OPEN frame contains
the fresh P3.31 run identity, but a completed host write alone cannot prove
that the device parsed it. P3.30 remains the latest proof of a complete
OPEN/diagnostic/challenge/HMAC/command exchange.

## Host-only result publication repair

The device run was already safely CLOSED when ordinary result publication
fell through from the P3.31 supplemental-observer branch into an inherited
P3.28 validator. An independently reviewed run-specific finalizer reopened
only the exact retained inputs, required CLOSED/19, exact 1/1 transfers, no
attempt 2, final health and the no-proof state, and published the canonical
mode-0400 single-link result. Post-publication audit reproduced the exact
15,182-byte result while reporting zero device, ADB, Odin, candidate,
rollback, or live action.

This was a host reporting defect after recovery, not another device failure
and not a reason to replay P3.31.

## Proportional successor

The next candidate should stay at the first-session OPEN boundary. Keep the
proved P3.30 protocol, exact tty lane, bounded udev settle, rollback and final
health unchanged; compare the P3.31 outer resident loop with the P3.30
single-session entry and repair only the lifecycle step that prevents the
first `OPEN_PARSED` diagnostic. Do not add persistence, PTY, arbitrary
commands, broad retries, or another validation layer before that narrow
hypothesis is tested.
