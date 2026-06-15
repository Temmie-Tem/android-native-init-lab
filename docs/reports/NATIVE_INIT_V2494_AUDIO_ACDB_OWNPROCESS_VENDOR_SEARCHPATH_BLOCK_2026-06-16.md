# NATIVE_INIT V2494 — audio ACDB own-process vendor search-path blocker

Date: 2026-06-16

## Decision

`v2494-ownprocess-vendor-searchpath-block`

V2494 reran the own-process ACDB GET handoff with the V2493 `RTLD_NOW`-only
helper. The V2492 invalid-flag blocker is resolved: bionic no longer rejects the
`dlopen()` flags. The next live blocker is now the vendor library search path:

```json
{"event":"error","stage":"dlopen-libaudcal","code":-1,"detail":"dlopen failed: library \"libaudcal.so\" not found"}
```

This is not a file-presence problem. The setup step confirmed both vendor libs
exist on the device:

```text
-rw-r--r-- 1 root root  92500 /vendor/lib/libacdbloader.so
-rw-r--r-- 1 root root 162124 /vendor/lib/libaudcal.so
```

The current helper calls `dlopen("libaudcal.so", RTLD_NOW)` by soname while being
executed from `/data/local/tmp` under `su`. Despite the runner exporting
`LD_LIBRARY_PATH=/vendor/lib:/system/lib:/system_ext/lib:/product/lib`, bionic did
not resolve `libaudcal.so` by soname from that context. The next smallest fix is
to use absolute vendor paths first:

```c
dlopen("/vendor/lib/libaudcal.so", RTLD_NOW);
dlopen("/vendor/lib/libacdbloader.so", RTLD_NOW);
```

If absolute paths are accepted, the next blocker will classify dependency or
namespace behavior more accurately. If absolute paths are still blocked, the
own-process path has a real linker namespace/loadability wall and should move to
one of the operator-listed namespace/location workarounds.

## Live run

Private run directory:

- `workspace/private/runs/audio/v2490-acdb-ownprocess-get-20260616-014321`

The runner name/build tag still says V2490 because the live harness is reused;
the helper artifact was the V2493 rebuild:

- helper SHA256: `de19a7ed44a51946d64479c7422fab50a3b4c018f7cb873c1d31e20f7ed81ba0`

High-level result:

- Android flash through checked helper: pass
- Android boot/root settle: pass
- helper push/chmod: pass
- helper execution: completed and wrote error event
- artifact pull: pass
- `/data/local/tmp/a90-acdb-ownget` cleanup: pass
- rollback to V2321: pass
- final native version: `0.9.285 (v2321-usb-clean-identity-rodata)`
- final native selftest: `fail=0`

Captured private event set:

- `error_count=1`
- `row_count=0`
- `raw_file_count=0`
- `target_4916_count=0`
- stage: `dlopen-libaudcal`
- detail: `dlopen failed: library "libaudcal.so" not found`

No ACDB GET calls ran, and no raw ACDB payload bytes were captured.

## Boundary

The run did not use in-HAL injection, Magisk modules, HAL restart, playback,
native speaker route writes, or `/dev/msm_audio_cal` calibration SET ioctls.

This result is distinct from V2492 and does not justify retrying the same soname
load path. It should be followed by an absolute-path helper build before any
broader linker namespace strategy.

## Validation

Post-run native checks:

```bash
python3 workspace/public/src/scripts/revalidation/a90ctl.py version
python3 workspace/public/src/scripts/revalidation/a90ctl.py selftest verbose
```

Result: V2321 resident, selftest `pass=11 warn=1 fail=0`.
