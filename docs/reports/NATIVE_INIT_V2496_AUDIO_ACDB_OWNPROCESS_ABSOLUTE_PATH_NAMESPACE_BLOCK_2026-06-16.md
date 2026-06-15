# NATIVE_INIT V2496 — audio ACDB own-process absolute path namespace block

Date: 2026-06-16

## Decision

`v2496-ownprocess-absolute-path-namespace-block`

V2496 reran the checked Android handoff with the V2495 helper that calls bionic
`dlopen()` using absolute vendor paths. The previous V2494 soname search-path
hypothesis is now closed: absolute paths still fail at the first vendor load.

Captured event:

```json
{"event":"error","stage":"dlopen-libaudcal","code":-1,"detail":"dlopen failed: library \"/vendor/lib/libaudcal.so\" not found"}
```

The file exists in the same Android session:

```text
-rw-r--r-- 1 root root 162124 /vendor/lib/libaudcal.so
-rw-r--r-- 1 root root  92500 /vendor/lib/libacdbloader.so
```

Therefore the blocker is no longer simple path spelling or `LD_LIBRARY_PATH`; it
is the Android linker namespace/policy for a `/data/local/tmp` standalone 32-bit
helper under `su`. The own-process path is still not dead, but the next unit must
change the load mechanism or namespace context. Repeating soname or absolute-path
`dlopen()` from the same context is low-information churn.

## Live run

Private run directory:

- `workspace/private/runs/audio/v2490-acdb-ownprocess-get-20260616-015109`

The runner name/build tag still says V2490 because the live harness is reused;
the helper artifact was the V2495 rebuild:

- helper SHA256: `4d793aa6a91d3f5212896903b6cbf08f8a423e6f9ec85174a0b01bf4c403198c`

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
- detail: `dlopen failed: library "/vendor/lib/libaudcal.so" not found`

No ACDB GET calls ran, and no raw ACDB payload bytes were captured.

## Boundary

The run did not use in-HAL injection, Magisk modules, HAL restart, playback,
native speaker route writes, or `/dev/msm_audio_cal` calibration SET ioctls.

## Interpretation

V2492 and V2494 were fixable helper mistakes/unknowns:

1. V2492: invalid flag word `0x102` → fixed by `RTLD_NOW` only.
2. V2494: soname lookup cannot find `libaudcal.so` → tested absolute path.
3. V2496: absolute `/vendor/lib/libaudcal.so` still reports not found while the
   file exists → classify as linker namespace/policy wall for the current run
   context.

Next meaningful unit should be host-only design for one bounded namespace-aware
variant, not another same-context `dlopen()` retry. Candidate directions:

- use Android linker namespace APIs such as `android_dlopen_ext()` with an
  exported vendor/sphal namespace if available on this build;
- execute from a context that already has vendor library visibility;
- stage a minimal dependency-local copy only if the license/private-path policy
  and linker dependency chain are explicitly bounded under `workspace/private`.

The operator's own-process path remains safer than HAL injection, but it now
requires a namespace-aware loader step.

## Validation

Post-run native checks:

```bash
python3 workspace/public/src/scripts/revalidation/a90ctl.py version
python3 workspace/public/src/scripts/revalidation/a90ctl.py selftest verbose
```

Result: V2321 resident, selftest `pass=11 warn=1 fail=0`.
