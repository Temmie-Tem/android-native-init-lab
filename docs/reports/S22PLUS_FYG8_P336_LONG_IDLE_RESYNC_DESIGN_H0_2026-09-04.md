# S22+ FYG8 P3.36 long-idle resynchronization design

Date: 2026-09-04 KST

Target: `SM-S906N / g0q / S906NKSS7FYG8`

Status: `H0_DESIGN_ONLY`

## Decision

P3.36 is a narrow successor to the consumed P3.35 resident-session run. P3.35
proved three authenticated native-PID1 sessions and nine fixed BusyBox command
results, then exposed one later-action framing failure after a long idle. P3.36
changes only the host's later-session synchronization and failure evidence.

It does not add a shell, command, PTY, file transfer, persistent installation,
reboot, Download-mode request, unattended execution or partition payload.

## Failure boundary

The P3.35 later action stopped at `open-diagnostic-read`. Its fixed host order
places this after banner, OPEN and stage zero but before AUTH or EXEC, so the
failed action executed no fixed command. The device listener writes banner and
stage zero before waiting for OPEN and repeats after a no-peer timeout. The old
host action waited for one apparent preamble before sending OPEN, allowing an
older buffered preamble to be mistaken for the currently waiting attempt.

The queued-preamble explanation is strong but remains a hypothesis because the
P3.35 exception path retained only the stage digest, not partial stream bytes.

## Minimal P3.36 change

For a later action only:

1. durably record one action intent;
2. reopen and revalidate the exact current-boot lease, endpoint and udev guard;
3. send exactly one OPEN before consuming buffered candidate preambles;
4. accept only a finite byte-bounded series of exact P3.36 banner plus stage-zero
   pairs until exact OPEN_PARSED arrives;
5. continue the unchanged RNG, challenge, AUTH, authenticated boot-ID, fixed
   three-command tuple and clean close; and
6. retain partial TX/RX and audit stage on every post-intent exit before the
   one-shot action result is published.

There is no protocol retry and no second OPEN. A partial, foreign, malformed,
out-of-order or oversized prefix stops and selects rollback.

## Qualification set

The H0 acceptance set is intentionally small:

- immediate clean preamble;
- zero, one and many buffered exact preambles;
- a prefix crossing multiple read boundaries;
- partial, foreign, reordered and over-bound negative prefixes;
- failure before AUTH proving zero EXEC;
- partial TX/RX publication on every injected stage cut; and
- unchanged P3.35 regression behavior.

The P3.36 action runner and activation identity must be included in the fresh
prepare/approval closure. The runner cannot be authored during the live lease.
P3.36 uses a fresh run identity and distinct boot-only AP; P3.35 remains
consumed and never replayable.

## Device sequence

After independent H0 review, the already requested attended D1 may perform one
fresh normal-boot baseline rotation. A new raw-first D0 must then prove the
P3.36 baseline and prepare one new F1 approval. F1 remains attended, rollback
remains exact Magisk boot-only, and any uncertainty goes directly to rollback.

This document grants no D0, D1, F1, device, recovery, replay or live authority.
