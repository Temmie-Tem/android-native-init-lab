# NATIVE_INIT V2604 — ACDB V2603 combined preload live result

Date: 2026-06-16

## Scope

Rollbackable Android-good handoff using the V2592 per-device runner with the V2603 combined ACDB preload. The combined preload includes the V2600 indirect-buffer `acdb_ioctl` tap, the V2531 fake audio-cal ioctl shim, and the V2572/V2591 preinit hook that arms capture and calls `send_audio_cal_v5` with `arg2=1` plus the corrected stack argument order.

The run stayed inside the measurement boundary: fake audio-cal allocation was enabled, no native replay was attempted, no real `AUDIO_SET_CALIBRATION` was passed through, no speaker write or mixer write was performed, raw captures stayed private, and checked rollback returned to V2321.

## Decision

- decision: `v2592-send-audio-cal-v5-no-per-device-records-rollback-pass`
- functional result: `no-per-device-records`
- private run: `workspace/private/runs/audio/v2592-acdb-perdevice-rx-capmask-argorder-20260616-174616`
- V2603 helper SHA256: `5cc7b9c6f2bacdb7c4789bb9f9f62ec2f2ec7488e9124e97b0364b3644af023d`
- V2603 combined preload SHA256: `eb979d3a732aaa27003d0547efdc8226bc052c2ea389accceec32474ed0e42bd`
- rollback: V2321 checked rollback completed (`rolled_back=True` in the engine result)
- counts toward the no-per-device-records retry budget: `true`

## Key Evidence

- `acdbtap` emitted only the explicit armed-control marker:
  - `phase=armed`
  - `cmd=0x00000000`
  - `out_len=0`
  - real `acdb_ioctl` call rows: `0`
  - raw capture files: `0`
  - target `4916` records: `0`
  - successful non-zero records: `0`
- The V2572/V2591 preinit hook executed and reached the per-device send boundary:
  - `entered_common_topology_hook`
  - `skip_real_common_topology`
  - `patched_initialized_flag_addr`
  - `patch_initialized_flag_return`
  - `before_send_audio_cal_v5`
  - no `send_audio_cal_v5_return`
- The helper did not SIGSEGV; the Android helper step timed out after `90.0s` while in or below `send_audio_cal_v5`.
- ACDB initialization was healthy before the send boundary:
  - `.acdb` and `.qwsp` files loaded from `/vendor/etc/audconf/KTC/...`
  - `ACDB_CMD_INITIALIZE_V2` logged
  - `ACPH INIT`, `RTAC INIT`, `MCS, FTS INIT`, and `ADIE RTAC INIT` logged
- The fake ioctl boundary held:
  - ioctl trace event count: `53`
  - fake `AUDIO_ALLOCATE_CALIBRATION` count: `25`
  - `AUDIO_DEALLOCATE_CALIBRATION` count: `0`
  - fake `AUDIO_SET_CALIBRATION` count: `0`
  - real `AUDIO_SET_CALIBRATION` passthrough count: `0`
- A broad AVC/audit filter matched unrelated log noise, but there was no `/dev/msm_audio_cal` open denial and no SELinux explanation for the stop.

## Interpretation

V2604 fixes the V2602 host-composition error. The V2603 combined preload did arm the capture path and did run the preinit hook; therefore the absence of rows is no longer explained by accidentally using a tap-only preload.

The remaining blocker is now inside the `send_audio_cal_v5` path before its first armed `acdb_ioctl` GET. The helper reaches `before_send_audio_cal_v5`, but no real `acdb_ioctl` row is observed afterward and the helper never returns before the timeout. This is consistent with a pre-GET wait, ACPH/RTAC/diag side path, internal mutex/state dependency, or a still-wrong call-state precondition before the per-device GET dispatcher is reached.

This closes another unchanged rerun of the `send_audio_cal_v5` route as low-information. The next meaningful unit should be host-only RE/instrumentation design for the pre-first-GET region inside `send_audio_cal_v5`, or direct construction of the lower-level pure-read per-device GET geometry. Do not rerun the same V2603 live route unchanged.

## Validation

- Re-read `GOAL.md`, `AGENTS.md`, `CLAUDE.md`, and the ACDB operator spec before reporting.
- Parsed `/tmp/v2604-live.json` and the private run metadata only.
- Confirmed the public report contains no raw ACDB payload bytes and no vendor binaries.
- `git diff --check`
