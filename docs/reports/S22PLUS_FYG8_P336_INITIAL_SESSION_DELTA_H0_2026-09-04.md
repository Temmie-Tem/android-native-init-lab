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
(`OPEN_PARSED`) was not observed, and nothing further was received during the
remaining ~30 seconds, after which the observer exited without error.

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
stage at exit. Neither exists for this run, per section 5.

No claim is made here about candidate-side listener internals, endpoint
buffering, or the cause of the P3.36 D1 rotation stop earlier the same day.

## 5. The evidence-retention gap

The P3.36 design promised to retain partial TX/RX and audit stage on every
post-intent exit. The failure occurred in the initial observer, before any
action intent, so nothing in that promise applied.

`partial_sessions`, `preauth_diagnostics` and `rng_eagain_retries` are all
`null` in the retained final result, and the terminal classification is
`interrupted-before-receipt` - by the definition carried in `GOAL.md`, the
projection used when partial exchange state was not serialized. That is the
same terminal, for the same reason, as P3.29.

The retention was scoped to a layer the failure never reached. This is the one
defect this analysis establishes, and it is the reason section 4 is
undecidable.

## 6. Unaffected safety layers

The candidate and the exact Magisk rollback each transferred once, final rooted
FYG8 health passed, the journal closed at 19 records, and `recovery_required`
is false. The loss in this run is information yield, not device safety. P3.36
is consumed and never replayable.

## Recommended next step

One change, in the initial observer only: retain the OPEN TX bytes and the
audit stage on every exit path, so that a pre-session failure is still a
durable receipt and section 4 becomes decidable on the next candidate.

No protocol change, retry loop, additional device gate, or new qualification
gate is justified by this evidence.

## Non-authority

This document is analysis of retained evidence. It activates nothing, qualifies
no runner, and grants no D0, D1 or F1 authority.
