# V3436 S22+ Ramoops Android Positive-Control Design

## Verdict

`HOST_DESIGN_PASS_NO_LIVE`.

V3436 defines the first meaningful live discriminator for the V3435 ramoops
console/dmesg DTBO. It does not create a live helper, activate an `AGENTS.md`
exception, contact the device, flash, reboot, or trigger a panic.

The final product target remains native/Debian without Android userspace.
Android is used only as a known-good positive-control substrate to prove the
retained observer before returning to direct native PID1.

Machine-readable contract:

```text
docs/plans/s22plus-v3436-ramoops-positive-control-contract.json
```

## Why Android Comes First

M13/M18/M22 combined an unproven native `/init` path with a pmsg-only ramoops
layout. Their empty console/dmesg results could not distinguish candidate
non-entry from a broken observer. V3435 created real console and dmesg zones;
V3436 now tests those zones with the known-booting Magisk Android baseline.

Only after the observer survives a controlled panic may it be used to localize
a direct-PID1 failure.

## Separate Policy Gates

A future live session requires two independently scoped `AGENTS.md` exceptions
and two independent acknowledgement tokens:

1. **DTBO maintenance exception:** exactly one V3435 candidate DTBO flash and
   exactly one pinned stock-DTBO rollback.
2. **Intentional-panic exception:** exactly one run-bound marker sequence and
   exactly one `sysrq-trigger-c` panic after the backend proof passes.

Neither exception exists or is active in V3436. DTBO authorization alone cannot
authorize panic, and panic authorization cannot authorize partition writes.

Pinned identities:

```text
candidate AP.tar.md5
  622ac0259eb61a7c9ef71eff44d4ea8bb3edbc6a90c3f2b237be7fdf88cb0264

candidate raw DTBO
  3c4d38a9d4833bab648cd36c3c0c78a2bfed35ca80dc4532b5e877cbaa8fa281

stock rollback AP.tar.md5
  6f397421bee84f4ea0c80a8519be0f6f6af84119794970e8a1faaa05f261caaa

stock raw DTBO
  97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c

known Magisk boot raw
  2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
```

Both APs contain exactly `dtbo.img.lz4`.

## Preflight Gates

### Stock Baseline

- exactly one Android ADB target;
- exact model/device/build identity;
- `boot_completed=1`, Magisk root, and four bounded stability samples;
- exact Magisk boot and stock DTBO readback hashes;
- live ramoops status is `disabled`.

### Patched Backend

After the candidate transfer and patched Android return, require all of:

- exact candidate DTBO readback;
- live ramoops status `okay`;
- region `0x200000`, pmsg `0x100000`, console `0x80000`, record `0x40000`;
- `/sys/module/ramoops/parameters` agrees with the live DT;
- pstore/ramoops backend registration is visible in dmesg/sysfs;
- `/sys/fs/pstore` is mounted and `/dev/pmsg0` exists;
- the fresh run ID is absent from baseline pstore files and the current ring.

Any failure before panic restores stock DTBO and stops. It must never continue
to panic in order to diagnose a failed backend preflight.

## Run-Bound Marker

Protocol `S22RPC1` uses a fresh 128-bit run ID and three CRC32-protected frames:

| Sequence | Phase | Sink |
|---:|---|---|
| 1 | `PREPANIC_KMSG` | `/dev/kmsg`, emergency console priority |
| 2 | `PREPANIC_PMSG` | `/dev/pmsg0` |
| 3 | `TRIGGER_KMSG` | `/dev/kmsg` immediately before panic |

Each frame binds the run ID, phase/sequence, exact candidate raw DTBO SHA256,
and V3436 contract SHA256
`f9ff86aa346023f8a168c98cd04bee57e1d69f913c9b4592f40ecfdc9133fec5`.

The kmsg frames must be visible in the current ring before the panic trigger.
Pmsg write completion is recorded separately; pmsg-only retention is not enough
to prove the new console/dmesg observer.

## State Machine

```text
STOCK_BASELINE
  -> CANDIDATE_TRANSFER
  -> PATCHED_BOOT_WAIT
  -> PATCHED_PREFLIGHT
  -> BACKEND_PROVEN
  -> MARKERS_WRITTEN
  -> PANIC_TRIGGERED
  -> RECOVERY_WAIT
  -> PATCHED_ANDROID_RETURNED
  -> EVIDENCE_COLLECTED
  -> ROLLBACK_TRANSFER
  -> ROLLBACK_BOOT_WAIT
  -> STOCK_RESTORED
  -> CLASSIFIED
```

The load-bearing rule is:

```text
panic -> patched Android return -> evidence collection -> stock DTBO rollback
```

Never restore stock DTBO before reading pstore: the stock overlay disables the
ramoops node. If Android does not return after panic, require attended recovery
to patched Android and preserve the evidence opportunity. If recovery is
impossible and exactly one Odin endpoint exists, the operator may explicitly
choose stock rollback for device recovery, but the result is
`NO_PROOF_EVIDENCE_ABANDONED_FOR_RECOVERY`.

Evidence collection is attempted at most twice. Every pstore file is read twice
to EOF, compared, hashed, and flushed to host disk before rollback begins.

## Classification

- `PASS_RAMOOPS_CONSOLE_DMESG_RETENTION`: a valid current-run
  `PREPANIC_KMSG` or `TRIGGER_KMSG` frame is recovered from
  `console-ramoops*` or `dmesg-ramoops*` after reset.
- `PARTIAL_PMSG_ONLY_NO_CONSOLE_DMESG_PROOF`: only the pmsg frame survives.
  This does not reopen direct PID1.
- `NO_PROOF_NO_CURRENT_RUN_FRAME`: no current-run frame and no integrity error.
- `FAIL_STALE_OR_COLLISION`: the run ID existed before marker emission.
- `FAIL_MALFORMED_OR_IDENTITY`: malformed frame, bad CRC, or wrong DTBO/contract
  binding.

Only PASS reopens a minimal module-free direct-PID1 witness. A clean negative
after proven backend registration retires ramoops and moves observability to
EUD/UART.

## Timeline Contract

The future helper must write only this schema:

```json
{"events":[{"name":"candidate_flash_start","timestamp_utc":"..."}]}
```

Required events include candidate flash start/done, candidate boot ready,
live-session start/end, backend proof, marker/panic/recovery/collection phases,
and rollback flash start/done plus rollback boot ready. Every event and every
call result is flushed immediately. Ad-hoc `phases_elapsed_sec`, nested steps,
or alternate timeline objects are forbidden.

## Next Unit

V3437 may implement the resumable host helper and inert policy drafts with
offline-check, dry-run, live-session, resume-after-manual-recovery, and explicit
Android/Download rollback modes. It must remain live-inert until both policy
exceptions receive separate operator approval.
