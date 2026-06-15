# NATIVE_INIT V2499 — audio ACDB own-process namespace loader live result

Date: 2026-06-16

## Decision

`v2499-namespace-api-symbol-missing-rollback-pass`

The V2498 own-process namespace-aware ACDB helper was executed once inside a
rollbackable Android handoff. The run did not reach namespace probing or ACDB GET
calls because `dlsym(libdl, "android_get_exported_namespace")` failed at runtime.
The device rolled back cleanly to V2321 and final native selftest remained
`fail=0`.

## Live Run

```text
private run dir: workspace/private/runs/audio/v2499-acdb-ownprocess-namespace-live-20260616-021122
helper sha256: 277915a34f4f0619f9c11abc681755ef2c609ed878dea665e47d6b920c66ac12
helper rc: 22
classification: namespace-api-symbol-missing
rolled_back: true
final version: A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)
final selftest: fail=0
```

Pulled private artifacts were preserved under the private run directory only. No
raw ACDB payload bytes were captured.

## Evidence

The helper emitted exactly one JSONL error event:

```json
{"event":"error","stage":"dlsym-android_get_exported_namespace","code":-2,"pid":3533,"tid":3533,"detail":"undefined symbol: android_get_exported_namespace"}
```

Summary from `result.json`:

```text
classification: namespace-api-symbol-missing
error_count: 1
row_count: 0
namespace_event_count: 0
raw_file_count: 0
target_4916_count: 0
operator_valuable: true
counts_toward_fails_twice: true
```

Rollback evidence:

```text
rollback-v2321: ok
rollback selftest: pass=11 warn=1 fail=0
post-run a90ctl selftest verbose: pass=11 warn=1 fail=0
```

## Boundary Check

The run stayed inside the approved measurement envelope:

- checked helper flashed only the boot partition
- Android boot was sealed to the private run directory with mode `0600`
- helper ran from `/data/local/tmp/a90-acdb-ownget` under `su`
- no in-HAL LD_PRELOAD or wrapper-exec path
- no Magisk module install
- no HAL restart
- no AudioTrack/playback
- no native speaker write
- no `/dev/msm_audio_cal` SET path
- remote temp directory was removed before rollback
- rollback to V2321 succeeded

## Parser Update

The live runner parser was aligned with the V2498 classification buckets before
this live run. The concrete mapping added in this unit:

- `dlsym-android_get_exported_namespace` / `dlsym-android_dlopen_ext` →
  `namespace-api-symbol-missing`
- `namespace-none-visible` → `namespace-none-visible`
- `namespace-visible-load-failed-libaudcal` → `namespace-visible-load-failed`
- `android_dlopen_ext-libacdbloader` → `libaudcal-loaded-libacdbloader-block`
- `acdb_loader_init_v3` → `init-v3-block`
- 4916-byte capture → `acdb-get-success-4916`
- non-4916 ordered out-buffer set → `acdb-get-full-outbuf-set-no-4916`

## Interpretation

V2499 proves that the public namespace API name is not dynamically visible through
`libdl.so` in this standalone Android helper context. This closes the direct
`android_get_exported_namespace` dlsym route for this helper as implemented. The
run did not test namespace visibility, vendor library loadability, ACDB init, or
the GET matrix.

The next meaningful unit is host-only: inspect the device-matched Android linker
and `libdl.so` symbol surface from private Android/vendor artifacts, then decide
whether the correct runtime symbol is a private loader entry such as a
`__loader_*` thunk, or whether a different safe own-process load strategy is
required. Do not retry V2499 unchanged.

## Validation Commands

```text
python3 -m py_compile   workspace/public/src/scripts/revalidation/native_audio_acdb_ownprocess_get_live_handoff_v2490.py   tests/test_native_audio_acdb_ownprocess_get_live_handoff_v2490.py

PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest   tests.test_native_audio_acdb_ownprocess_get_live_handoff_v2490 -v

python3 workspace/public/src/scripts/revalidation/native_audio_acdb_ownprocess_get_live_handoff_v2490.py --dry-run --from-native

python3 workspace/public/src/scripts/revalidation/native_audio_acdb_ownprocess_get_live_handoff_v2490.py   --run-live --from-native --out-dir workspace/private/runs/audio/v2499-acdb-ownprocess-namespace-live-20260616-021122   --android-timeout 300 --flash-timeout 480 --adb-command-timeout 120   --adb-pull-timeout 180 --helper-timeout 90

python3 workspace/public/src/scripts/revalidation/a90ctl.py selftest verbose
```
