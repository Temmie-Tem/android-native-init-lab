# S22+ FYG8 P3.32 same-FD logical-session F1 no-proof

Date: 2026-09-04 KST

Target: `SM-S906N / g0q / S906NKSS7FYG8`

Tier: attended F1

Formal verdict: `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`

Outcome: `p332_authenticated_logical_resident_same_fd_unproved_rollback_verified`

## Outcome

P3.32 is closed, consumed, and never replayable. The exact boot-only candidate
and exact Magisk rollback each transferred once, no attempt 2 exists, the
journal closed at 19 records, and final rooted FYG8 health passed with
`recovery_required=false`. The operator reported a normal candidate boot with
no boot loop.

The raw-first observer retained the exact 49-byte P3.32 native-PID1 banner and
the host emitted one 32-byte OPEN frame. The first logical session then timed
out at `open-diagnostic-read`. No `OPEN_PARSED`/`RNG` diagnostic, challenge,
HMAC authentication, fixed command, clean close, or second logical session was
proved. Sessions attempted/successful/reconnected are `1/0/0`, so the declared
same-FD logical-resident capability remains unproved.

## Exact closure

- candidate AP: 28,631,081 bytes, SHA-256
  `e1309080879700445b88cef08eb3becb4e57e524f5467979857fc79ee36a9a9d`;
- exact Magisk rollback AP: 23,367,721 bytes, SHA-256
  `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`;
- candidate transfer result: 2,079 bytes, SHA-256
  `8ec7f5bd1e230f0840b3a2cc391fda6e267efbaf68d71fa466727bc2557c0888`;
- rollback transfer result: 2,030 bytes, SHA-256
  `7e5cc8dcf0147d174e1412fa0dd01fd38916f1f1bd74055b91942ab6924256b4`;
- final live state: 32,779 bytes, SHA-256
  `7bf83fb129addbaecd124f4ca527118013b4fbc4fc0110538968415bac16b198`;
- final live result: 36,558 bytes, SHA-256
  `3a76c74eba93999d568154710a57628d36390cbf552453ba5eba280c4439b112`.

The terminal journal record is sequence 18 with digest
`1f6db8d6d4e0bf22106366dc4cca3fcd0a265dfd534c3fdc27e23ce6335467b0`.
The state records `candidate_completed=true`, `rollback_completed=true`,
`final_verified=true`, and `p332_proof_class=NO_PROOF_OBSERVER`.

## Candidate observation

- raw device-to-host bytes: 49 bytes, SHA-256
  `ac1cd94304104e8494d6a27cd0b71192ecad420284056936c0ea71adc26c0f26`;
- host-to-device bytes: 32 bytes, SHA-256
  `cfe6ca09374375637d9a595b8f523b4344d56bd2ad36d93221dced18f833ba8e`;
- candidate observer receipt: 6,803 bytes, SHA-256
  `e4d5f56fe3c3d87cc5fe9c78e6ef2a1a2b756d418b343984a86aa641baf4c145`;
- observer classification: `authenticated-session-error`;
- partial session: index 0, `TimeoutError`, stage
  `open-diagnostic-read`.

P3.32 removed the P3.31 physical close/reopen and outer reconnect loop, yet the
same first-session boundary recurred. This is evidence that physical reconnect
was not the sole necessary cause of P3.31's failure. It does not identify the
remaining cause and does not prove host OPEN parsing on the device.

## Host-only result publication

The device run and recovery had already completed when the ordinary result
publisher stopped. Adding the required arrival-proof projection grew the
31,209-byte state to 32,779 bytes, eleven bytes above the shared 32 KiB
intermediate-record bound. The result itself was within its existing 64 KiB
terminal bound.

An independently reviewed exact-run finalizer kept the common 32 KiB bound and
all execution-critical sources unchanged. It accepted only the pinned pre-state,
the exact CLOSED/19 journal, exact 1/1 transfers, no attempt 2, final health and
the negative P3.32 projection. It published the exact mode-0400 single-link
state/result, and a post-publication audit reproduced both without changing the
state, result, or journal-head metadata. The finalizer performed zero device,
ADB, USB revalidation, Odin, candidate, rollback, or live action.

## Proportional successor

Keep the proved P3.30 authentication and fixed-command protocol, lane, guard,
rollback, and health path unchanged. The next candidate should isolate only the
first-session regression between P3.30 and the P3.31/P3.32 entry path, with one
small device-side diagnostic before or at OPEN parsing. Do not add persistence,
PTY, arbitrary commands, broad retries, or another general validation layer.
