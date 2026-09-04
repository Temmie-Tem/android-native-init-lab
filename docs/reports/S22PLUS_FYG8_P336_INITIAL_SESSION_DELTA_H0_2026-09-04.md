# S22+ FYG8 P3.36 initial-session delta and qualification-gap analysis

Date: 2026-09-04 KST

Target: `SM-S906N / g0q / S906NKSS7FYG8`

Status: `H0_ANALYSIS_ONLY`

## Scope

This report answers the follow-up named at the end of
`S22PLUS_FYG8_P336_F1_LONG_IDLE_NO_PROOF_2026-09-04.md`: compare the narrow
P3.35/P3.36 initial-session delta before any further candidate is spent.

It is host-only. It reads retained evidence from two consumed run directories
and tracked sources, and replays retained bytes through the tracked P3.36
observer over a local socketpair. It contacted no device, opened no endpoint,
and issued no ADB, USB, Odin, fastboot or transfer operation. It grants no
authority, changes no success criterion, and qualifies no runner.

## Method

Both retained candidate RX streams were decoded with the repository's own wire
definitions: header `<4sBBHII` (magic `S328`, version, frame type, payload
length, sequence, CRC) and the diagnostic payload decoder, with frame-type and
diagnostic-stage constants read from
`s22plus_fyg8_p336_long_idle_runtime.py`. All byte counts below are measured
from the retained files, not restated from a result document.

Sources of evidence:

- `workspace/private/runs/device-action-f1-live-v2/p335-ready1-prepared-20260904-2/`
- `workspace/private/runs/device-action-f1-live-v2/p336-ready1-prepared-20260904-2/`

## 1. Measured protocol, both runs

P3.35 retained 1,983 bytes; P3.36 retained 73 bytes. Both open with one exact
49-byte banner. Decoded frame sequence after the banner:

| | P3.35 (PASS) | P3.36 (NO_PROOF) |
|---|---|---|
| banner | 1 | 1 |
| `DIAG` stage 0 (console enter) | yes | yes |
| `DIAG` stage 1 (`OPEN_PARSED`) | yes | **absent** |
| `DIAG` stage 2 | yes | absent |
| `CHALLENGE` / `READY` / `BOOT_ID` | yes | absent |
| `DATA`/`EXIT` command pairs | 3 per session | absent |
| `DONE` | yes | absent |
| complete sessions | 3 | 0 |
| observer elapsed | 2,988 ms | 30,183 ms |
| observer exit | rc 0, not timed out | rc 0, not timed out |

The three P3.35 sessions repeat this whole cycle inside one boot. The banner is
not repeated between them.

## 2. The candidate never parsed the host OPEN

`DIAGNOSTIC_STAGE_OPEN_PARSED` is 1. The candidate emitted stage 0 and never
emitted stage 1, while in P3.35 stage 1 follows stage 0 directly.

The device's own diagnostic vocabulary therefore reports that OPEN was not
parsed. The P3.36 observer then blocked in its next read until its 30-second
deadline and exited without error, which is consistent with the candidate
sending nothing further rather than sending something rejected.

Confidence: high; read from retained bytes and repository constants.

## 3. The delta that produced it

P3.36 changed the initial wire order. In `exchange_late_action`:

```python
# This is intentionally the first wire action.  It establishes the
# boundary before consuming any bytes retained during long idle.
audit.current_stage = "open-write-before-resync"
_CODEC._send(descriptor, runtime.FRAME_OPEN, 0, runtime.P336_RUN_ID, ...)
_consume_preambles_until_open_parsed(descriptor, deadline, audit, writer)
```

P3.35 read the candidate preamble first and sent OPEN afterwards, so OPEN was
written only after the candidate had demonstrably reached its console path.
P3.36 writes OPEN immediately after opening the descriptor, before any evidence
that the candidate-side listener is reading.

This is the same hazard class as P3.28: a host action ordered ahead of proven
device readiness. P3.28 probed udev before udev processing completed; P3.36
writes OPEN before the listener is known to be draining the endpoint.

Confidence: high for the code delta and its ordering; the causal attribution is
the best explanation consistent with all retained evidence and with the replay
in section 4, but see section 7.

## 4. Replay of retained bytes through the tracked P3.36 observer

The retained P3.35 stage frames were replayed into
`_consume_preambles_until_open_parsed` over a socketpair. Because the P3.35
banner carries the P3.35 run identity, which the P3.36 observer correctly
rejects, the exact P3.36 banner was substituted and the retained stage frames
used unmodified.

| replayed input | result |
|---|---|
| banner + stage 0 only (what P3.36 actually received) | `TimeoutError`, blocked at `resync-prefix` |
| banner + stage 0 + stage 1 (real device progression) | passes, `pairs=1`, `open_parsed_seen=True` |
| banner + stages 0, 1, 2 | passes, `pairs=1` |
| banner + stage 0 repeated twice (fixture's shape) | passes, `pairs=2` |

Two conclusions follow.

First, the P3.36 resync loop parses the real device progression correctly. The
observer is not at fault for failing to advance: it received stage 0 and
nothing else. This removes host parsing from the candidate causes and leaves
section 3.

Second, the truncated stage-0 case reproduces the live failure exactly -
including the blocked stage label - on the host, with no device. This case was
constructible from P3.35's retained stream before the P3.36 candidate was
spent.

Confidence: high; these are measured outcomes of running tracked code.

## 5. The resynchronization premise is refuted by already-retained evidence

The P3.36 design states that the candidate listener writes banner and stage
zero and "repeats after a no-peer timeout", and builds a bounded resync loop
around consuming repeated banner/stage-0 pairs, with `MAX_PREAMBLE_PAIRS = 8`.

The retained evidence contradicts the premise:

- the candidate-side banner is a single write in the `p260` boot-stage
  sequence, not a loop;
- P3.35's retained stream contains exactly one banner across three complete
  sessions, with no banner between sessions; and
- the stage frames are a monotonic progression 0 -> 1 -> 2, not a repeated
  stage-0 preamble.

Because a second banner cannot occur within one boot, the loop can consume at
most one pair against real firmware. Section 4 shows the loop still behaves
correctly in that single-pair case, so this is not a live defect; the multi-pair
path and the `MAX_PREAMBLE_PAIRS = 8` bound are simply unreachable.

The consequence is narrower than a fault but not trivial: even a P3.36 run that
had completed would not have exercised the buffered-preamble resynchronization
it was built to test, because the device cannot produce that input. The
refuting bytes were on disk, in P3.35's own retained stream, before P3.36 was
designed.

Confidence: high.

## 6. Hazard class: a qualification fixture weaker than the live channel

The P3.36 host qualification passed, including
`test_zero_one_many_buffered_preambles_and_immediate_clean_stream` at counts
0, 1 and 4. It passed because the fixture manufactures the input that section 5
shows the device cannot emit:

```python
def _preamble(self) -> bytes:
    pair = runtime.DEVICE_BANNER + observer.encode_frame(...CONSOLE_ENTER...)
    return pair * self.preamble_count
```

The fixture transport is `socket.socketpair()`, and the fixture server sends its
preambles before it reads OPEN. A socketpair is lossless, symmetric and
buffered, so a host write issued before the peer reads is retained and
delivered.

The live transport is a USB CDC-ACM gadget where a host write issued before the
candidate listener drains the endpoint is not guaranteed to be delivered. The
fixture therefore cannot express the failure mode that the section 3 delta
introduces, and no number of passing cases in it constrains that delta. The
same socketpair was sufficient to reproduce the failure once the input was
taken from retained device bytes rather than synthesized, as section 4 shows;
the gap is in the inputs and the ordering the fixture permits, not the
transport alone.

Proposed hazard class: **qualification inputs synthesized rather than replayed,
over a transport that cannot lose a pre-readiness write**. Scope: any unit whose
delta changes wire ordering, open/read/write sequencing, or timing against a
device endpoint. Retirement evidence: a qualification case that replays a
retained live stream, plus one that drops a write issued before the peer reads.
Review trigger: any future unit that changes initial-session ordering.

Confidence: high for the fixture's properties; the hazard class is a proposal
for review, not an activated gate.

## 7. Retention was installed one layer below the failure

The P3.36 design promised to "retain partial TX/RX and audit stage on every
post-intent exit". The failure occurred in the observer, before any action
intent, so the action runner was never invoked: the pinned evidence directory
`p336-long-idle-action-evidence` was never created, and the run proceeded
candidate transfer -> observer -> guard release -> rollback.

Consequently `partial_sessions`, `preauth_diagnostics` and
`rng_eagain_retries` are all `null` in the retained final result, and the
terminal classification is `interrupted-before-receipt` - by the definition
carried in `GOAL.md`, the projection used when partial exchange state was not
serialized. That is the same terminal, for the same reason, as P3.29.

The unit built to retain failure evidence produced a failure with no retained
evidence, because the retention was scoped to a layer the failure never
reached.

Confidence: high.

## 8. What remains unproved

Whether the OPEN frame was written to the descriptor at all is not decidable
from retained evidence. The host TX bytes and the observer audit stage would
separate "OPEN never written" from "OPEN written and lost before the listener
drained the endpoint". Both are exactly the artifacts section 7 shows were not
retained.

No claim is made here about candidate-side listener internals, endpoint
buffering behaviour, or the cause of the P3.36 D1 rotation stop earlier the
same day.

## 9. Recurrence and cost

Across the last twelve S22+ F1 runs, three consumed a candidate while
terminating upstream of the question that unit existed to answer: P3.28 before
the tty open, P3.29 before the challenge, P3.36 before the action. In each case
the preceding unit's repair was installed at the layer where the previous
failure occurred, and the next failure appeared one layer earlier.

Unit cost over the same span is rising: commits per unit 3, 4, 3, 7, 5, 8, 14
for P3.30 through P3.36, and `_p3NN_bundle` branch sites in the F1 live runner
25, 26, 27, 35, 37, 26, 30, 35, 36, 37, 38, 45, 48 for P3.24 through P3.36.

The permanent safety layers were unaffected throughout: candidate and rollback
transferred once each, final rooted health passed, and `recovery_required` was
false. The loss in these runs is information yield, not device safety.

Confidence: measured counts; the interpretation is offered for review.

## Recommended next H0, before any further F1

1. **Promote the section 4 replay into a tracked qualification case.** It
   reproduces the live failure host-side and pins the real stage progression as
   the expected input. Host-only, no device contact.
2. **Add a fixture case that drops a write issued before the peer reads**, so
   that an initial-session ordering change is expressible as a failure, per
   section 6.
3. **Move retention from post-intent to post-open.** The observer must
   serialize audit stage and partial TX/RX on every exit path, so a
   pre-session failure is still a durable receipt. Commit `b2cc9b8992` moves in
   this direction for the proof namespace; the TX/audit path is not yet
   covered. Item 3 is what makes section 8 decidable on the next run.
4. **Withdraw the buffered-preamble resync premise** from the successor design,
   per section 5, and state the successor's question as the ordering hazard in
   section 3.

A protocol redesign, retry loop, new device gate or another F1 is not justified
before items 1-3 exist.

## Non-authority

This document is analysis of retained evidence. It activates nothing, qualifies
no runner, and grants no D0, D1 or F1 authority. P3.36 remains consumed and
never replayable.
