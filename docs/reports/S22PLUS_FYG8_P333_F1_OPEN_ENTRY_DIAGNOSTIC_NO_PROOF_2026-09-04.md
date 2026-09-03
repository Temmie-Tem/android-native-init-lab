# S22+ FYG8 P3.33 F1 OPEN-entry diagnostic result

Date: 2026-09-04 KST

Target: `SM-S906N / g0q / S906NKSS7FYG8`

Tier: attended F1, boot-only candidate with mandatory rollback

Formal result: `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`

Outcome: `p333_authenticated_logical_resident_open_entry_diagnostic_unproved_rollback_verified`

## Outcome

P3.33 answered its narrow question positively. The retained 73-byte candidate
RX is the exact 49-byte P3.33 native-PID1 banner followed by one independently
decoded, CRC-valid 24-byte `S328` diagnostic frame with stage `0`, code `0`,
sequence `0`. The stage is emitted immediately before the out-of-line
`p328_framed_console()` call, so the device reached that call boundary and the
diagnostic traversed the candidate CDC-ACM channel to the host.

The host then wrote the exact 32-byte OPEN frame, but no `OPEN_PARSED` frame
arrived. Session 1 stopped at `open-diagnostic-read`; sessions
attempted/successful/reconnected are `1/0/0`. This rules out "the publisher
never called the console" as the P3.31/P3.32 explanation and narrows the next
investigation to the first `p328_read_frame()` / OPEN-validation path.

It does not prove that the device received or parsed the host OPEN bytes. It
also proves no challenge, HMAC, BusyBox command, clean close, second session,
resident loop, interactive shell, persistence, or USB/Max77705 causality. The
formal campaign result therefore remains `NO_PROOF_OBSERVER` rather than a
session PASS.

## Exact retained evidence

- candidate AP: 28,631,081 bytes, SHA-256
  `1a6036b688ae92c94f459aee66e06a817e767aa615c6a7a9cb2a22b7d13487b3`;
- exact Magisk rollback AP: 23,367,721 bytes, SHA-256
  `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`;
- candidate observer: 6,801 bytes, SHA-256
  `8485312a0b5e6ce118da3393faac2ff533deabddda2a5835abf62e59119cf378`;
- candidate raw RX: 73 bytes, SHA-256
  `18bc55ba6a6b0abc6c8a2d714e33bd407e35300e4d68355931e92e26c53a7eba`;
- host OPEN TX: 32 bytes, SHA-256
  `549e387c39a4091d32b07df210b6bb430aac5fceff2af00dc3346f4ec0d73e1b`;
- candidate and rollback transfer classifications:
  `odin_transfer_completed`, attempt 1 only;
- journal: 19 records, terminal state `CLOSED`, terminal record SHA-256
  `e76974f885bf6158d7d05f376fffa1e9e742d44139579c31d071a6167d5f8704`;
- final rooted FYG8 health: verified, Download absent,
  `recovery_required=false`.

P3.33 is consumed and never replayable.

## Post-closure publication

All device effects, rollback, final health, and journal closure completed
before the live command reported `durable record exceeds its bound`. Adding
the required arrival projection would grow the state from 31,285 bytes to
32,855 bytes, 87 bytes above the ordinary 32 KiB intermediate-record bound.
No device recovery was required.

The independently reviewed exact-run finalizer in commit `74cc071092` kept the
common 32 KiB bound unchanged. It reconstructed the pinned CLOSED journal,
both attempt-1 transfer receipts, exact observer/raw bytes and current verifier
sources, then published only:

- final state: mode `0400`, one link, 32,855 bytes, SHA-256
  `232aeecc7339da3c2ae15120dd21de592ea2497b6a1e9388dfb8497312ba1506`;
- canonical result: mode `0400`, one link, 36,652 bytes, SHA-256
  `207c36a1506997fe81e45e16997c3769fd838bf5e5f6de1ed8853c861388a7ed`.

Post-publication audit reproduced both identities and reported zero device,
ADB, USB revalidation, Odin, candidate, rollback, or live action.

## Next boundary

The proportional successor should preserve the proved banner and stage-0
path, then retain the first device-side `p328_read_frame()` return code outside
the tty response path. No protocol rewrite, broad retry, reconnect, resident
installation, or repeated candidate is justified by this result.
