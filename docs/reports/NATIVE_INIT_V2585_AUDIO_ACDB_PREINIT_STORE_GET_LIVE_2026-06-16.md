# NATIVE_INIT V2585 — ACDB pre-init store-get live result

Date: 2026-06-16

## Scope

One rollbackable Android handoff using the V2584 runner and V2583 pre-init store-get probe.
No native calibration `SET`, speaker write, direct `/dev/msm_audio_cal` replay, or raw ACDB
payload publication was performed. Raw artifacts remain private under the run directory.

## Decision

- decision: `v2584-preinit-storeget-case-returns-no-nonzero-rollback-pass`
- ok: `False`
- run_dir: `workspace/private/runs/audio/v2584-acdb-preinit-store-get-20260616-150447`
- rollback_target: `v2321-usb-clean-identity-rodata`
- final_native_version: `0.9.285 (v2321-usb-clean-identity-rodata)`
- final_selftest: `fail=0`

## Result Summary

The pre-init hook entered the common-topology interception point and ran the planned store-get
metadata cases before the known init-tail crash path. The hook itself is therefore live, but the
five candidate store-get argument shapes did not return a usable payload:

| Case | Selector | Instance | Return | Out Len | Non-zero |
| --- | ---: | ---: | ---: | ---: | --- |
| `store_selector_37` | 37 | 0 | -19 | 0 | no |
| `store_selector_0_no_instance` | 0 | 0 | -19 | 0 | no |
| `store_selector_0_instance` | 0 | 1 | -19 | 0 | no |
| `store_selector_1_no_instance` | 1 | 0 | -20 | 0 | no |
| `store_selector_1_instance` | 1 | 1 | -19 | 0 | no |

The ACDB loader log confirms database load and init progression through `ACDB_CMD_INITIALIZE_V2`,
ACPH/RTAC/MCS/ADIE RTAC init, and `Reading meta_info` before the five store-get errors. The ioctl
trace also confirms fake-success `AUDIO_ALLOCATE_CALIBRATION` records across the init allocation
set, including cal types through `39`, with no real `AUDIO_SET_CALIBRATION` boundary crossing.

## Interpretation

- V2585 is a safe negative for the V2580/V2583 `acdb_loader_store_get_audio_cal()` argument
  guesses; it does not invalidate the already captured real topology payload path.
- The failure mode is informative: the candidate store selectors are reaching loader code but are
  not valid for the desired per-device/calibration data in this binary state.
- Repeating the same five store-get shapes is low value unless new RE identifies the actual
  selector/argument geometry.

## Safety / Rollback

- Android boot, staging, execution, artifact pull, cleanup, and V2321 rollback completed.
- Post-run native bridge responded with `version` showing V2321.
- `selftest verbose` reported `pass=11 warn=1 fail=0`.
- Raw device artifacts and vendor libraries remain under `workspace/private/`; no raw payload bytes
  or private binaries are committed.

## Next

Do not keep iterating blind `store_get` selector guesses. The next meaningful unit should either:

1. implement the operator-specified armed `acdb_ioctl` dump path if the current code is missing that
   exact after-init arming behavior, or
2. move to a source/RE-backed lower-level GET argument decode before another live capture.

## Validation

- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_preinit_store_get_live_handoff_v2584.py --run-live --exact-gate 'AUD-ACDB-V2584-preinit-store-get go: one-shot preinit store_get metadata capture on Android, fake allocate preload, no SET replay, no speaker write, rollback to V2321'`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/a90ctl.py version`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/a90ctl.py selftest verbose`
