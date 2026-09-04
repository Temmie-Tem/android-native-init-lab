# S22+ FYG8 P3.38 F1 open-read branch result

Date: 2026-09-05 KST
Target: `SM-S906N / g0q / S906NKSS7FYG8`
Status: `CLOSED`, healthy, consumed, never replayable
Formal verdict: `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`

## Outcome

P3.38 completed exactly one candidate and one exact Magisk rollback transfer.
The final rooted FYG8 Android health check passed, Download was absent and
`recovery_required` is false. It did not establish an authenticated or
resident USB session.

- Candidate AP: `28631081B/2f6dc740`
- Rollback AP: `23367721B/d2373bf8`
- Candidate transfer receipt: `2079B/26009a11`
- Rollback transfer receipt: `2030B/24724e01`
- Journal: `CLOSED`, 19 records, terminal `285331bb`
- Final state: mode 0400/link 1, `17374B/06c6663f`
- Final result: mode 0400/link 1, `20258B/6525e96c`

There is no attempt 2. P3.38 is consumed and cannot be replayed.

## What the candidate proved

The retained candidate stream is `97B/78137243`. It contains the fresh
native-PID1 banner followed by two CRC-valid diagnostic frames:

1. stage 0, code 0: entry into the console path;
2. stage 3, branch ordinal 1: `header-validation`.

This is the intended new information. P3.37 exposed only an undifferentiated
`EPROTO`; P3.38 proves that the fixed header read itself completed and rules
out header-read errno, body-read errno and body CRC as the reported branch.

Branch 1 still covers two validation sites in the current runtime: base frame
magic/version/maximum-length validation, and the later parsed OPEN
type/sequence/exact-length/run-ID validation. The retained evidence cannot
choose between those two sites. No OPEN_PARSED diagnostic, challenge, HMAC,
fixed BusyBox command, clean close, logical resident proof or general shell
was observed. Candidate success and causal-result flags remain false.

## Recovery and final health

The initial process stopped after candidate observation while measuring the
physical rollback endpoint. It did not replay the candidate. Recovery reopened
the same durable journal, identified the attended Download endpoint, completed
the exact preapproved rollback once and verified Android boot completion,
stopped boot animation, root, boot/supporting partition identities and absent
Download. The two rollback raw reads are byte-identical
`2097136B/321b03b2`.

## Terminal publication incident

The journal reached `CLOSED` and final health was already durable, but the
ordinary publisher initially did not create `live-result.json`. The P3.38
arrival projection used integer keys for its four branch ordinals in memory;
canonical JSON reopened those same object keys as strings, so the final exact
Python-object equality check failed. This changed no evidence meaning and
caused no device or transfer failure.

Independent review returned `PASS_GO_P338_TERMINAL_REEMIT_H0`. The host-only
re-emission pinned the original runner, exact CLOSED journal, state, terminal,
both completed transfer receipts and final health; normalized only that map
through canonical JSON; validated the formal terminal; and atomically emitted
the missing mode-0400 result. It invoked no backend, ADB, USB revalidation,
Odin, journal transition or transfer. Commit `6dd202876b` applies the permanent
one-line JSON-visible map fix and adds a focused roundtrip regression test.

## Proportional next step

The next candidate should preserve the successful path and all timeouts, add
no retry, and split branch 1 into the smallest useful subreason: base frame
header grammar versus parsed OPEN semantic validation. Only if the semantic
site wins should a later diagnostic distinguish type, sequence, exact length
and run-ID. This avoids widening the protocol before the present evidence
requires it.
