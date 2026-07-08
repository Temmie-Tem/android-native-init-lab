# S22+ — M28 Re-Opened Observability; the Fix Is Collection Timing, Not More Markers (M29 Operator Steer, 2026-07-08)

Operator (Claude) host-only steer, refining the loop's own M28-S24
retained-log postmortem. No device action. Agrees with the loop's core finding
(the captured `last_kmsg` is the Android rollback boot, not the `S24` candidate)
but corrects the M29 direction: the cheapest, highest-value next move is a
**collection-timing** change, not a candidate re-architecture with more markers.

## What M28 actually changed (the good news)

Adding `sec_debug.ko` + `minidump.ko` as dependency-complete suppliers
**re-opened Samsung's retained-log channel**: the M28 run captured a full
**2,097,136-byte** `last_kmsg` for the first time in this saga (earlier M-runs
saw empty/vestigial pstore). The retention mechanism is alive. This is the
observability the whole M18→M27 saga chased and could not get.

## Why the captured log is still the wrong boot (collection timing)

`/proc/last_kmsg` holds only the **immediately previous** boot. The M28-S24
rollback timeline had **two** Android boots after the candidate reset:

```text
S24_candidate_boot_ready   14:33:15   (candidate resets ~here)
S24_rollback_flash ...     14:33:15   Magisk boot rollback
S24_rollback_boot_ready    14:34:01   ← FIRST Android boot; here last_kmsg == S24 log
dtbo_rollback_flash ...    14:34:13   stock DTBO rollback
dtbo_rollback_boot_ready   14:34:59   ← SECOND Android boot; last_kmsg now == boot A
live_session_end           14:34:59   ← helper read last_kmsg HERE
```

The helper read `last_kmsg` only at the very end, after **both** rollback boots.
By then the S24 candidate's kernel log had been overwritten by the first Android
rollback boot. Host confirmation of the blob's provenance:

```text
Android signatures (really_probe/modprobe/vendor modules) : 1320
native-init / A90 / 43-module signatures                  :    3 (incidental)
```

So the blob is unambiguously an Android boot, not the native-init candidate.
This is exactly the "recovery chain clears the context" wall — but now it is a
**fixable collection-order bug**, because the channel itself works.

## M29 = capture at the FIRST post-candidate boot (cheap, host-side helper change)

Before re-architecting the candidate with durable markers, change **when** the
helper collects:

1. At `S24_rollback_boot_ready` (the FIRST Android boot after the candidate
   reset), **immediately** read and pull, before the stock-DTBO rollback:
   - `/proc/last_kmsg` (now == the candidate's kernel log), and
   - Samsung `sec_qc_user_reset` surfaces `/proc/reset_summary`,
     `/proc/reset_klog`, `/proc/reset_history`, `/proc/reset_tzlog`. `sec_debug`
     is now loaded **in the candidate**, so a watchdog bite may populate per-core
     last-PC / faulting-module context here.
2. Only after that early capture, proceed with the stock-DTBO rollback.

This is a helper collection-order change on the existing dependency-complete
candidate — **no new candidate flash policy, no marker re-architecture**. Keep
the M28 S24/F43 dependency-complete artifacts and the DTBO high-speed cap /
QMP-exclusion as-is.

## Decision gate M29

- **First-boot `last_kmsg`/`reset_summary` shows the S24 fault** (a faulting PC,
  the module/driver active at bite, or the last native-init line) ⇒ the
  observability wall is finally down; localize the exact biting step and fix its
  missing supply/clock — no marker work needed.
- **First-boot capture is still empty** ⇒ then, and only then, the loop's marker
  hypotheses matter (init never ran / `/dev/kmsg` not retained / faulted before
  first line). Add a durable candidate-owned marker path as M30, having ruled out
  the cheap timing fix first.

## Relationship to the loop's postmortem

The loop's postmortem is correct that S24's failure was not captured and lists
four hypotheses (init didn't run / output not retained / faulted pre-first-line /
buffer overwritten by rollback). The evidence points hardest at **#4 (overwritten
by later rollback)** because a full 2 MB Android log WAS retained — retention is
not broken, the read is one boot too late. M29 tests #4 directly and cheaply
before spending a candidate redesign on #1–#3.

## Discipline

Host-only helper change + one attended live gate under a fresh SHA-pinned
boot+DTBO exception (same scope as M28). No forbidden partitions, no PMIC/power
writes, redacted logs (strip serials — the M25–M28 reports were just re-redacted;
keep raw adb serials out of committed reports). Device stays recoverable to the
Magisk baseline.
