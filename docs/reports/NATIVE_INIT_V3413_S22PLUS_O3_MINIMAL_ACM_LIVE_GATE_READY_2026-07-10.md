# V3413 S22+ O3 Minimal-ACM Live Gate Ready

## Verdict

`LIVE GATE READY; NOT YET CONSUMED`. The exact V3412 O3 artifact, Magisk
rollback AP, stock fallback AP, current rooted Android boot SHA, and single
transport passed the checked helper's offline and connected dry-run gates. No
reboot, flash, module insertion, sysfs/configfs write, or partition write
occurred in this preparation unit.

## Checked Helper

```text
workspace/public/src/scripts/revalidation/s22plus_o3_minimal_acm_live_gate.py
```

The helper requires two independent tokens:

```text
S22PLUS-O3-MINIMAL-ACM-LIVE-GATE
S22PLUS-O3-MINIMAL-ACM-ROLLBACK-FROM-DOWNLOAD
```

It pins candidate AP, boot, LZ4, init, daemon, kernel, plan TSV/header, known
Magisk base, Magisk rollback AP, and FYG8 stock fallback AP hashes. It refuses
multiple transports, wrong Android identity/boot SHA, a missing/consumed
exception, a non-single-member AP, or any manifest safety drift.

## Proof And Rollback Flow

1. Start continuous udev, kernel-journal, and available usbmon observers.
2. Enter Download from the verified rooted Android baseline.
3. Flash the exact boot-only O3 AP and require the original Odin endpoint to
   disconnect.
4. Accept only a CDC ACM tty carrying serial `S22O3ACM01`.
5. Run 128 CRC-framed echo requests, with host close/reopen at request 64.
6. Query `O3 STATUS` and require 59-module load accounting, EOF-complete
   registration, eight gates (`0xff`), exact mode/UDC readback, and zero
   protocol errors.
7. Ask the operator for manual Download-mode entry and wait at most 600 seconds.
8. Restore the pinned Magisk boot AP, using the stock boot AP only if that
   transfer fails while Download remains available.
9. Verify rooted Android, exact baseline boot SHA, stability, and collect
   pstore plus `/proc/last_kmsg`.

The standard `timeline.json` remains `events:[{name,timestamp_utc}]` and a
successful complete run requires the eight canonical flash/boot/session
phases. Every result is written before the helper exits.

## Validation

Nine O3 build/live-focused tests pass. They cover the real manifest, full
status bundle, active/consumed policy handling, independent tokens, canonical
timeline, attended rollback ordering, static binaries, source restrictions,
and a host PTY 128-frame run. The helper's artifact-only offline check passed,
then its connected read-only dry-run passed against the current device.

The active AGENTS exception is limited to this one exact O3 candidate and is
consumed as soon as `candidate_flash_start` is recorded.
