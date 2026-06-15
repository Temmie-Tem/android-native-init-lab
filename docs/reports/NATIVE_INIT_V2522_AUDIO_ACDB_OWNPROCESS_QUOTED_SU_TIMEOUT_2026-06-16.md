# NATIVE_INIT_V2522_AUDIO_ACDB_OWNPROCESS_QUOTED_SU_TIMEOUT_2026-06-16

## Scope

- Unit: V2522 live rerun of the V2490 own-process ACDB path after V2520 quoted-`su` and V2521 staging-permission fixes.
- Goal: confirm whether `ownget-run-context.txt` now reports root/Magisk context and whether the own-process ACDB GET path progresses past the V2519 shell-domain denial.
- Boundary: measurement-only; no HAL injection, no Magisk module install, no HAL restart, no playback, no native speaker write, and no `/dev/msm_audio_cal` SET ioctl.

## Result

- Decision: `v2490-acdb-ownprocess-get-live-started-rollback-pass`
- Runner outcome: `ok=false`, `rolled_back=true`
- Error: `ownget-run-helper timed out after 60.0s`
- Private run: `workspace/private/runs/audio/v2490-acdb-ownprocess-get-20260616-044058`

## What Completed

- V2321 preflight passed before live execution.
- Android checked handoff completed.
- Android root precheck still worked: `adb shell su -c id` returned root/Magisk context.
- Setup now created the remote staging directory as `shell:shell`, preserving `adb push`.
- All dependency pushes succeeded.
- The quoted `su -c` command shape was used for setup, chmod, identity probe, logcat clear, helper run, and cleanup.
- Rollback to V2321 passed.
- Final serial verification after rollback:
  - `version`: `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`
  - `selftest verbose`: `fail=0`

## Evidence Kept

- Host-side step logs show staging and dependency push completed.
- `ownget-setup.stdout.txt` confirms `/data/local/tmp/a90-acdb-ownget` and `delta` were `shell:shell`.
- `ownget-chmod-helper.stdout.txt` confirms helper SHA matched and dependency files were present.
- No `ownget-device-artifacts/` directory was pulled because the helper timed out before the runner reached log capture, collect, and pull.

## Interpretation

- The behavior changed materially after the quoted-`su` fix:
  - V2519: helper returned quickly with `acdb_loader_init_v3=-19` under shell context.
  - V2522: helper did not return within `60s` once the quoted path was used.
- This strongly suggests the helper reached a different execution path, likely no longer the immediate shell-domain `/dev/msm_audio_cal` denial, but V2522 cannot prove root context or the exact hang site because remote artifacts were cleaned in the exception path before pull.
- The current runner has an observability gap: helper timeout skips logcat capture, context pull, and artifact pull, then cleanup removes the evidence.

## Next Unit

- V2523 should be host-only runner hardening:
  - on helper timeout or any helper-step exception, run best-effort logcat capture;
  - run best-effort collect/readability chmod;
  - pull `/data/local/tmp/a90-acdb-ownget` before cleanup;
  - classify the result as `helper-timeout-artifacts-preserved` or a more specific ACDB blocker if logs/events exist.
- Do not increase the helper timeout or rerun live until timeout evidence preservation is implemented.

