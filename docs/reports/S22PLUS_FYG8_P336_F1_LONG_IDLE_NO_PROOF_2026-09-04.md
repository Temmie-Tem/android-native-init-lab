# S22+ FYG8 P3.36 F1 long-idle result

Date: 2026-09-04 KST

Target: `SM-S906N / g0q / S906NKSS7FYG8`

Tier: attended F1, boot-only candidate with mandatory rollback

Formal result: `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`

Outcome: `p336_authenticated_long_idle_resident_unproved_rollback_verified`

## What succeeded

The exact P3.36 candidate and exact Magisk rollback each transferred once,
with no attempt 2. The candidate left Download mode and produced a 73-byte
raw host capture: the exact 49-byte P3.36 native-PID1 banner followed by the
CRC-valid 24-byte stage-0/code-0 diagnostic emitted immediately before the
framed console path. The operator also observed a normal boot without a boot
loop.

This proves candidate boot, native-PID1 console entry, and candidate-to-host
USB bytes. It does not prove an authenticated session.

## What did not succeed

No canonical candidate receipt was published. The retained result is
`interrupted-before-receipt`, with HMAC, authenticated PID1 execution,
BusyBox commands, clean framed close, logical residency, retained-listener
proof, and later-action lease all false or absent. Therefore P3.36 did not
establish a resident session or standing shell.

The device-side stream stopped after stage 0; no `OPEN_PARSED`, RNG,
CHALLENGE, READY, boot-ID, command result, or DONE frame is retained. Whether
the host OPEN reached or was parsed by the candidate remains unknown.

The host observer then made this no-proof result harder to report: its P336
wrapper passed an empty partial proof to the strict successful-proof namespace
validator, which raised `P3.36 initial proof namespace differs` instead of
publishing a rejected receipt. This was a host reporting defect, not evidence
of an authenticated device session.

## Rollback and closure

Because the candidate transfer was already durable and the required observer
proof was absent, Process-v2 correctly forbade candidate replay and required
the preapproved rollback. Recovery resumed the same journal. The exact Magisk
rollback transferred once, and the S22+ returned to healthy rooted FYG8
Android with expected boot/supporting-partition identities and no Download
endpoint.

The ordinary recovery then stopped after all device work at
`P3.36 final stock projection is missing`. P336 had been omitted from the
post-rollback projection selector and fell through to its P328 predecessor
namespace. The independently reviewed host-only finalizer in commit
`772458644d` used only the retained evidence and appended the journal tail;
it invoked no ADB, USB, Odin, candidate, or rollback operation.

Final identities:

- candidate AP: 28,631,081 bytes, SHA-256
  `d19f978109100f3c87a5ca92dd2aaf0aaf8af0e228f0eebb6d7716c95008361b`;
- rollback AP: 23,367,721 bytes, SHA-256
  `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`;
- candidate raw: 73 bytes, SHA-256
  `19955936676751fff5e9d8643b0b5d4f8a89e27d94da57c80771ef5c1b39b5b6`;
- two byte-identical rollback reads: 2,097,136 bytes, SHA-256
  `c8f8c4fd67a354beee120fd473502d1d296f5aeb98410293d41f9d38114b7efe`;
- final state: 12,791 bytes, SHA-256
  `db4299b37142ee94d8b836c50a919c409acf7861034e011f5ca23f6624295318`;
- final result: 15,428 bytes, SHA-256
  `9941d5e29efcd9c4e5c2b8b71f13476fba3c1dff0b79df0c302b6a4a9344bc30`;
- journal: `CLOSED`, 19 records, terminal record SHA-256
  `d808e9952122e51e4e1454f6fb2d06dce98cdd633c5c02b644c54bbf3ce90e4d`;
- `recovery_required=false`.

P3.36 is consumed and never replayable.

## Proportional follow-up

Commit `b2cc9b8992` fixes only the observed host defects: an empty partial proof
now remains a rejected no-proof receipt, P336 proof/audit fields stay in the
P336 namespace during execution and recovery, and final stock evidence no
longer falls through to P328. It changes no success criterion, timeout,
approval, device authority, or replay rule.

The next candidate should first compare the narrow P3.35/P3.36 initial-session
delta and retain the host OPEN TX plus the first device read/parse return. A
protocol redesign, broader retry loop, new external-tamper gate, or another
F1 before that small H0 analysis is not justified.
