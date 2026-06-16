# NATIVE_INIT V2593 — ACDB corrected-arg-order live result

Date: 2026-06-16

## Scope

Rollbackable Android handoff using the V2592 live runner and V2591 private artifacts. The run used
fake audio-calibration ioctl interception and the corrected `send_audio_cal_v5` call shape. No native
ACDB replay `SET`, native speaker write, mixer write, or raw payload publication was performed.
Raw logs and any pulled binaries remain private under the run directory.

## Decision

- decision: `v2592-send-audio-cal-v5-no-per-device-records-rollback-pass`
- functional result: `no-per-device-records`
- safety result: rollback to V2321 completed; direct post-run native health check shows
  `version=0.9.285 (v2321-usb-clean-identity-rodata)` and `selftest fail=0`
- run directory: `workspace/private/runs/audio/v2592-acdb-perdevice-rx-capmask-argorder-20260616-155220`

## Key Evidence

- V2591 artifacts were selected and staged:
  - helper SHA: `5cc7b9c6f2bacdb7c4789bb9f9f62ec2f2ec7488e9124e97b0364b3644af023d`
  - preload SHA: `e8e5273a76ebd409ecb84aa660372aded1b3559ee7ee3eaaba72fcad72693d93`
- `acdbtap` produced only the control marker:
  - `phase=armed`
  - `cmd=0x00000000`
  - `out_len=0`
  - real `acdb_ioctl` call rows: `0`
- preinit hook events reached the send boundary but never returned:
  - `entered_common_topology_hook`
  - `skip_real_common_topology`
  - `patched_initialized_flag_addr`
  - `patch_initialized_flag_return=0`
  - `before_send_audio_cal_v5`
  - no `send_audio_cal_v5_return`
- helper did not SIGSEGV; the runner timed out while the helper was still in/under
  `send_audio_cal_v5`.
- `ioctl` interposition remained active and fake-allocated successfully:
  - `ioctl_trace_event_count=53`
  - `AUDIO_ALLOCATE_CALIBRATION` fake-success count: `25`
  - observed fake-allocate cal types include `11`, `12`, `15`, and `16`
  - `AUDIO_SET_CALIBRATION` count: `0`
- ACDB initialization itself was healthy:
  - `.acdb`/`.qwsp` files loaded from `/vendor/etc/audconf/KTC/...`
  - `ACDB_CMD_INITIALIZE_V2` logged
  - `ACPH INIT`, `RTAC INIT`, `MCS, FTS INIT`, and `ADIE RTAC INIT` logged
  - no `/dev/msm_audio_cal` AVC/ioctl denial explaining the stop

## Interpretation

The V2590/V2591 corrected stack-argument order is not sufficient to reach the first armed
per-device ACDB GET. The run still stops after the `before_send_audio_cal_v5` marker and before any
real `acdb_ioctl` row, despite `arg2=1`, corrected `(arg5,arg6,arg7)=(0,48000,1)`, healthy init,
and active fake allocation.

This does not disprove the underlying per-device GET path, but it closes one easy hypothesis:
repeating the `send_audio_cal_v5` route with only argument-order variations is now low-information.
The next meaningful unit should either instrument the local setup path inside `send_audio_cal_v5`
before the first `0x1122e` dispatcher query, or derive/call the lower-level pure-read GET request
geometry directly. Native replay remains blocked until operator-verified per-device bytes exist.

## Validation

- V2592 dry-run before live reported `live_ready=True` and no live blockers.
- Live command:
  `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_perdevice_rx_capmask_argorder_live_handoff_v2592.py --run-live --exact-gate "AUD-ACDB-V2592-perdevice-rx-capmask-argorder go: one-shot send_audio_cal_v5 arg2=1 corrected-stack-order per-device capture on Android, fake allocate preload, no SET replay, no speaker write, rollback to V2321"`
- Direct post-run health:
  - `python3 workspace/public/src/scripts/revalidation/a90ctl.py version`
  - `python3 workspace/public/src/scripts/revalidation/a90ctl.py status`
  - `python3 workspace/public/src/scripts/revalidation/a90ctl.py selftest verbose`
- `git diff --check` for the public V2592/V2593 changes.
