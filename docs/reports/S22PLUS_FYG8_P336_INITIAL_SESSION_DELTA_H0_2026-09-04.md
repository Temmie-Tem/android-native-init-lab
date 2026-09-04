# S22+ FYG8 P3.36 initial-session observation analysis

Date: 2026-09-04 KST

Target: `SM-S906N / g0q / S906NKSS7FYG8`

Status: `H0_ANALYSIS_ONLY`

## Corrections to the first revision of this report

The first revision, committed in `a7e02986f4`, drew two conclusions that
review found contrary to the retained evidence. Both are withdrawn.

1. **Withdrawn: the causal attribution to the P3.36 OPEN ordering.** The first
   revision blamed the `exchange_late_action` change that sends OPEN before any
   read. That function was not executed by this run. The F1 initial observation
   runs `exchange_retained` through `_P336ObserverSession`, which is the proved
   P3.35 session shape compiled against the P3.36 runtime and identity;
   `exchange_late_action` is reachable only from the P3.36 long-idle action
   runner, which was never invoked. No conclusion about the failure may rest on
   code that did not run.
2. **Withdrawn: the claim that the candidate emits its banner once per boot,
   and the consequent claim that multiple preambles are unreachable.** The
   retained P3.35 capture contains the exact 49-byte banner three times, at
   offsets 0, 661 and 1322 - one per session. The first revision's frame
   splitter matched on the `S328` magic only and silently absorbed each
   49-byte banner into the length of the preceding frame. Every conclusion
   built on banner-once, including the proposed qualification hazard class, is
   withdrawn.

What the first revision got right is retained below: the raw sizes and timings,
the observed stage boundary, the evidence-retention gap, and the P3.36
`NO_PROOF` terminal with healthy rollback. No operational code was changed by
either revision.

## Corrections to the second revision of this report

The second revision described the retention gap as retention having been
"scoped to a layer the failure never reached". Replay of the real initial path
shows that is the wrong mechanism. The retention was present at the right
layer and did compute; publication of the receipt aborted before it reached
disk. Section 5 is rewritten accordingly, and the recommended next step
narrows, because the host-side defect was already repaired in tree by
`b2cc9b8992` fifty-four minutes after the run.

## Scope

Host-only analysis of retained evidence from two consumed run directories and
tracked sources. No device contact, no endpoint opened, no ADB, USB, Odin,
fastboot or transfer operation. Grants no authority, changes no success
criterion, qualifies no runner.

- `workspace/private/runs/device-action-f1-live-v2/p335-ready1-prepared-20260904-2/`
- `workspace/private/runs/device-action-f1-live-v2/p336-ready1-prepared-20260904-2/`

## Method

Both retained candidate RX streams were decoded with the repository's own wire
definitions: header `<4sBBHII` (magic `S328`, version, frame type, payload
length, sequence, CRC) and the diagnostic payload struct, with constants read
from `s22plus_fyg8_p336_long_idle_runtime.py`. The decoder walks the stream by
declared frame length and recognises the exact banner inline, so a banner
between two frames is counted rather than absorbed. All byte counts are
measured from the retained files.

## 1. Measured streams

P3.35 retained 1,983 bytes; P3.36 retained 73 bytes.

| | P3.35 | P3.36 |
|---|---|---|
| exact 49-byte banners | 3 | 1 |
| `DIAG` stage 0 (console enter) | 3 | 1 |
| `DIAG` stage 1 (`OPEN_PARSED`) | 3 | 0 |
| `DIAG` stage 2 | 3 | 0 |
| `CHALLENGE` / `READY` / `BOOT_ID` | 3 each | 0 |
| `DATA` / `EXIT` | 9 / 9 | 0 |
| `DONE` | 3 | 0 |
| complete sessions | 3 | 0 |
| observer elapsed | 2,988 ms | 30,183 ms |
| observer exit | rc 0, not timed out | rc 0, not timed out |

Each P3.35 session is one banner followed by stages 0, 1, 2, then the
authenticated exchange and three command results, then `DONE`. The banner is
emitted per session, not once per boot.

## 2. The observed boundary

The P3.36 candidate reached console entry and emitted `DIAG` stage 0. Stage 1
(`OPEN_PARSED`) was not observed. The retained capture holds exactly those 73
bytes for the observer's entire 30,183 ms elapsed time, after which it exited
without error. Per-byte arrival times were not retained, so where stage 0 falls
within that window, and therefore how long the candidate was silent after it,
are both unknown.

This is the full extent of what the retained bytes establish.

## 3. What executed

The F1 initial observation used `_P336ObserverSession`, whose own docstring
records the arrangement: "P3.35 session shape with the exact P3.36 initial wire
codec ... The inherited session orchestration then calls this P336-bound
`exchange_retained`, never the imported P335 module."

The P3.36 long-idle action runner was not invoked: its pinned evidence
directory `p336-long-idle-action-evidence` was never created, and the run
proceeded candidate transfer -> observer -> guard release -> rollback. The
`exchange_late_action` resynchronization path therefore did not run in this
campaign and is not implicated by any retained evidence.

## 4. What cannot be decided from retained evidence

The observation "stage 0 received, stage 1 not observed" does not distinguish
between at least these:

- the host OPEN was never written to the descriptor;
- OPEN was written but not delivered to the candidate listener;
- OPEN was delivered and rejected during validation; or
- OPEN was accepted and the candidate failed before emitting stage 1.

Separating them requires the initial observer's OPEN TX bytes and its audit
stage at exit. Neither was published for this run, for the reason established
in section 5.

Host TX alone narrows the first branch away from the other three but does not
split them. Upstream Linux `u_serial` queues host OUT data until the gadget TTY
side reads it, which weakens - but does not eliminate - the plain "the listener
had not read yet, so OPEN was simply dropped" reading of branch two. That is
upstream behaviour; no evidence here establishes that the Samsung 5.10 gadget
serial implementation on this target is identical.

No claim is made here about candidate-side listener internals, endpoint
buffering, or the cause of the P3.36 D1 rotation stop earlier the same day.

## 5. Why the retained evidence was never published

The retained final result carries `partial_sessions`, `preauth_diagnostics` and
`rng_eagain_retries` as `null`, and the terminal classification is
`interrupted-before-receipt` - the same terminal as P3.29. The reason is not
that the host had nothing to record.

The observer child exited cleanly. Its capture record reports
`returncode: 0`, `timed_out: false`, `producer_error_type: null` and
`elapsed_msec: 30183`, with a 73-byte stdout. What is absent from the run
directory is `candidate-observer.json`: the receipt file itself was never
created, and its absence is exactly what the live runner converts into
`interrupted-before-receipt`.

The receipt was not written because building it raised. At the time of the run,
`_P336ObserverSession.observe()` repinned the inherited proof unconditionally:

    proof = _p336_repin_proof(value.get("proof", {}))

A failed initial session carries no proof, so this repinned `{}`, and
`_p336_repin_proof({})` raises `F1LiveError("P3.36 initial proof namespace
differs")` - which the receipt-validation path catches and reports as
`interrupted-before-receipt`. The full partial receipt had already been
computed one frame below and was discarded with the exception.

`b2cc9b8992`, committed at 18:09:09 KST, fifty-four minutes after the observer
capture at 17:15:42 KST, changed that line to repin only a non-empty proof.
The host-side defect is therefore already repaired in tree; it was repaired
without the mechanism above being stated, and this report states it.

Replay over a socketpair whose device side emits exactly the candidate's 73
bytes and then falls silent confirms both halves. The real `exchange_retained`
retains a 32-byte OPEN frame as TX, the exact 73-byte RX (SHA-256 identical to
`candidate-observer.raw`), one stage-zero diagnostic, and
`failure_stage == "open-diagnostic-read"`; the current `observe()` publishes
those as `session_tx_hex`, `tx`, `rx`, `diagnostics` and `partial_sessions`
rather than raising. This is pinned by
`tests/test_s22plus_fyg8_p336_retained_stream_replay.py`.

## 6. Unaffected safety layers

The candidate and the exact Magisk rollback each transferred once, final rooted
FYG8 health passed, the journal closed at 19 records, and `recovery_required`
is false. The loss in this run is information yield, not device safety. P3.36
is consumed and never replayable.

## Recommended next step

The host-side change first recommended here is already in tree. What remains is
narrow:

1. Done, and required: pin the real initial path, so the loss cannot recur
   silently. `tests/test_s22plus_fyg8_p336_retained_stream_replay.py` now drives
   `exchange_retained` and the real receipt projection against the candidate's
   exact bytes, and asserts the OPEN TX, the RX digest, the stage-zero
   diagnostic, the failure stage, and that a proofless session still publishes.
2. Recommended, device side, one value: record the outcome of the listener's
   first `read_frame` as a diagnostic. Host TX separates only branch one of
   section 4; this separates the remaining three. It is one ordinal, not a
   retry, not a new frame type and not a new handshake.

No protocol change, retry loop, additional device gate, or new qualification
gate is justified by this evidence. With the above, the next candidate can be
prepared under the ordinary process.

## Non-authority

This document is analysis of retained evidence. It activates nothing, qualifies
no runner, and grants no D0, D1 or F1 authority.
