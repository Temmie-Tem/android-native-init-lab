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
type/sequence/exact-length/run-ID validation. This report first stated that
the retained evidence cannot choose between those two sites. That statement is
withdrawn; see "Correction: branch 1 is already decided by the retained host
TX" below.

No OPEN_PARSED diagnostic, challenge, HMAC, fixed BusyBox command, clean
close, logical resident proof or general shell was observed. Candidate success
and causal-result flags remain false.

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

## Correction: branch 1 is already decided by the retained host TX

Added 2026-09-05, host-only, after the campaign closed. This corrects two
statements above. It changes no device evidence, no verdict and no artifact
identity. P3.38 remains `CLOSED`, consumed and never replayable.

The P3.38 observer receipt retained the host OPEN transmission, which the
P3.36 no-proof publication path had previously dropped. It is 32 bytes:

```
53 33 32 38 | 01 | 01 | 10 00 | 00 00 00 00 | b2 fd b3 2d | <16-byte run ID>
"S328"        ver  OPEN  len=16  seq=0         CRC           run ID
```

`encode_frame(FRAME_OPEN, 0, P338_RUN_ID)` on the tracked codec inherited by
the P3.38 observer reproduces those 32 bytes exactly, CRC included. Checking
them against both sites that emit ordinal 1:

- base frame grammar: magic `S328`, version 1 and length 16 within
  `P328_MAX_PAYLOAD` all pass;
- parsed OPEN semantics: type `P328_FRAME_OPEN`, sequence 0, length equal to
  `sizeof(p328_run_id_bytes)` and a payload equal to `p328_run_id_bytes` all
  pass.

The last of these is decided by the candidate's own output rather than by the
host's expectation. The retained stream opens with the fresh banner
`S22PLUS-FYG8-E3:<run ID>`, whose run ID is the hex of the same
`k_run_id[16]` the OPEN payload carries, and the P3.38 artifact identity
module independently requires that run ID to be present in the flashed image
and the predecessor run ID to be absent.

`p328_read_exact` returns 0 only when the requested size was fully read; a
short read continues to loop, end of stream returns `-EIO` and expiry returns
`-ETIMEDOUT`. There is therefore no path on which a partially filled header
buffer reaches the grammar check as a success.

Neither site can fire on the host's intact OPEN bytes, yet ordinal 1 was
recorded. The 16 bytes the candidate consumed as a frame header were therefore
not the header the host transmitted. This is host-side derivation from
retained bytes, not a new device observation: the retained TX is what the host
submitted to the endpoint, and it is not evidence of what the wire delivered.
That gap is the finding rather than a defect in it.

The surviving hypothesis is the one the P3.36 design named: data ahead of the
host OPEN in the candidate's read stream, or a read that begins off the frame
boundary.

## Proportional next step

The next candidate should preserve the successful path and all timeouts and
add no retry. It should not spend a candidate splitting branch 1 into header
grammar versus parsed OPEN semantics; the section above already decides that
split in favour of header grammar, and a candidate spent on it would return
information the retained evidence holds.

The useful unknown is what the candidate actually read. The smallest step is
to retain the rejected bytes themselves: carry the 16-byte header that failed
the grammar check, or a bounded prefix of it, in the existing branch
diagnostic. That answers what preceded or displaced the OPEN directly. It adds
no retry, no second OPEN, no new frame type and no approval gate; only the
diagnostic payload width changes.

This addendum grants no D0, D1, F1, device, recovery, replay or live
authority.
