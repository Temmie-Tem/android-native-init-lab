# NATIVE_INIT_V2458_AUDIO_ACDB_M1_HYBRID_LIVE_RESULT_2026-06-15

## Summary

V2458 executed the fresh AUD-5L live rerun using the V2457-hardened root
recheck logic. The recoverable envelope held:

- Android boot image was flashed only through the checked helper.
- Temporary Magisk module state stayed under `/data` and was cleaned.
- No native calibration ioctl, native mixer write, native PCM write, or native
  speaker playback was attempted.
- The run rolled back to V2321 and final native `selftest verbose` returned
  `fail=0`.

The run reached the intended Android-good measurement window. It staged the M1
temporary module, rebooted for Magisk `service.sh`, reacquired Android ADB,
verified Magisk `uid=0`, started the host-coordinated late observer, launched
bounded Android framework `AudioTrack` playback, collected private artifacts,
cleaned up, and rolled back.

No `/dev/msm_audio_cal` ioctl payload was captured.

## Inputs

- Runner:
  `workspace/public/src/scripts/revalidation/native_audio_acdb_m1_hybrid_late_observer_live_handoff_v2451.py`
- Private run directory:
  `workspace/private/runs/audio/v2458-acdb-m1-hybrid-late-observer-20260615-182052`
- V2321 rollback image:
  `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
  SHA256 `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private helper SHA256:
  `9520e9f297ba4cb52ce2730d8166876409162a70f64998b7c2ac16ca21f165f8`
- Private module zip SHA256:
  `6f90d81c4cb03ac62c7174754b4746bb4d329a40eb009131fe2e021ec2b4f7d4`

## Root-Gate Result

The V2457 root-output hardening worked and no retry was needed:

- initial post-handoff root check:
  - classification: `root-ready`
  - attempt: `1/4`
  - stdout length: `61`
  - stderr length: `0`
- post-module root check:
  - classification: `root-ready`
  - attempt: `1/8`
  - stdout length: `61`
  - stderr length: `0`

Both checks reported Magisk `uid=0` before the runner proceeded.

## Capture Result

- `decision=v2451-acdb-m1-hybrid-late-observer-hybrid-late-ioctl-any-but-fd-miss-before-rollback-rollback-pass`
- `ok=true`
- `rolled_back=true`
- overall classification: `hybrid-late-ioctl-any-but-fd-miss`
- overall syscall stops: `259429`
- overall ioctl-any entries: `3454`
- overall `/dev/msm_audio_cal` fd matches: `0`
- overall fd misses: `3454`
- late observer classification: `late-ioctl-any-but-fd-miss`
- late observer syscall stops: `13441`
- late observer ioctl-any entries: `492`
- late observer `/dev/msm_audio_cal` fd matches: `0`
- late observer fd misses: `492`
- late observer terminal stop files: complete (`missing_stop_files=[]`)
- payload hashes: `[]`
- `raw_payload_in_summary=false`

The late observer attached to the active audio HAL process and followed the
ACDB worker thread:

- logcat ACDB worker: process `12816`, thread `15644`
- helper task scan: process `12816`
- clone-follow evidence: child TID `15644` was added as a tracee
- helper stop counters for process `12816`:
  - `tracees=13`
  - `ioctl_any_entry_count=0`
  - `ioctl_fd_match_count=0`
  - `ioctl_fd_miss_count=0`

The late FD snapshot for process `12816` did show `/dev/msm_audio_cal` open
as fd `13`, alongside `/dev/snd/controlC0`, `/dev/diag`, and `/dev/msm_rtac`.
Despite that, the traced process and the cloned ACDB worker thread made no ioctl
syscalls during the observed window. The ioctl activity that was captured came
from the AudioFlinger-side process and targeted binder/hwbinder fds, not
`/dev/msm_audio_cal`.

## Android-Good Audio Edge

Android framework playback did run and the stock audio stack logged the expected
speaker ACDB edge:

- `A90_AUDIO_STIMULUS_BEGIN`
- `select_devices ... output device ... speaker, acdb 15`
- `send_app_type_cfg_for_device PLAYBACK app_type 69941, acdb_dev_id 15, sample_rate 48000`
- `ACDB -> send_audio_cal, acdb_id = 15, path = 0, app id = 0x11135`
- `AUDIO_SET_AUDPROC_CAL cal_type[11] acdb_id[15] app_type[69941]`
- `AUDIO_SET_AFE_CAL cal_type[16] acdb_id[15]`
- `A90_AUDIO_STIMULUS_END frames=96000`
- `A90_AUDIO_STIMULUS_FINISH rc=0`

## Interpretation

V2458 closes the previous root-output gap and also removes the main remaining
timing/thread-coverage objection to the M1 ptrace strategy:

- the late observer starts before playback;
- the target audio HAL process is traced;
- the ACDB worker TID is seen and attached via clone-follow;
- the process has `/dev/msm_audio_cal` open;
- Android logs the actual speaker ACDB/App Type edge;
- no `/dev/msm_audio_cal` ioctl syscall is observed from that traced process.

This is still not native ACDB replay input. It is a stronger negative for the
specific assumption that the speaker calibration payload can be recovered by
ptracing userspace `ioctl()` calls on `/dev/msm_audio_cal` during the playback
window.

## Next

Do not rerun M1 unchanged. The next meaningful unit is host-only mechanism
analysis of the stock `libacdbloader.so` / HAL path and the kernel
`msm_audio_cal` ABI to explain how the logged `AUDIO_SET_*` calibration reaches
the kernel when ptrace sees no `/dev/msm_audio_cal` ioctl syscall:

- check whether calibration uses `mmap`, shared memory, binder/vendor service,
  or another device path;
- inspect symbols/strings and syscall expectations around `allocate_cal_block:
  mmap`;
- determine whether the native path needs ACDB loader semantics rather than raw
  ioctl replay.

