# V2450 — Audio ACDB M1 Diagnostic Observer Live Rerun

Date: 2026-06-15
Run: V2450
Scope: rollbackable Android-good `/dev/msm_audio_cal` diagnostic observer using a temporary Magisk service module
Rollback target: V2321 `boot_linux_v2321_usb_clean_identity_rodata.img`

## Safety Boundary

- Used the checked Android handoff / checked V2321 rollback path only.
- No native calibration ioctl was issued.
- No native speaker/mixer/PCM write was issued.
- No Wi-Fi scan/connect/DHCP/route/ping action was issued.
- Magisk was used only as an Android-side measurement capsule, matching the Wi-Fi-style handoff pattern; it is not a native-init runtime dependency.
- Temporary module/APK cleanup ran before rollback.

## Code Changes

- Added `native_audio_acdb_m1_diag_observer_live_handoff_v2450.py`.
- Added focused V2450 tests for:
  - exact approval refusal before device action,
  - V2449 helper/module selection,
  - helper-completion wait command,
  - diagnostic JSONL summary classifications,
  - raw-payload-free public summary hashes.
- Fixed the V2449 service helper duration cap from `180` to `120`, matching the helper parser's accepted `--duration-sec` maximum.

## Validation

Host validation:

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_m1_diag_observer_planner_v2449.py workspace/public/src/scripts/revalidation/native_audio_acdb_m1_diag_observer_live_handoff_v2450.py tests/test_native_audio_acdb_m1_diag_observer_planner_v2449.py tests/test_native_audio_acdb_m1_diag_observer_live_handoff_v2450.py`
- `PYTHONPATH=tests python3 -m unittest tests.test_native_audio_acdb_m1_diag_observer_planner_v2449 tests.test_native_audio_acdb_m1_diag_observer_live_handoff_v2450`
- `PYTHONPATH=tests python3 -m unittest discover tests`
- `python3 workspace/public/src/scripts/revalidation/native_audio_acdb_m1_diag_observer_live_handoff_v2450.py --dry-run --materialize-module-template`
- `git diff --check`

Pre-live safety:

- V2321 rollback image SHA matched `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- V2237 fallback image SHA matched `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`.
- `boot_linux_v48.img` existed.
- Resident V2321 reported `selftest fail=0` before the live rerun.

## Live Attempt 1

Private run directory:

- `workspace/private/runs/audio/v2450-acdb-m1-diag-observer-20260615-160630`

Result:

- Decision: `v2450-acdb-m1-diag-observer-no-syscall-stops-before-rollback-rollback-pass`
- Android flash/stage/module activation/playback/cleanup/rollback completed.
- Final rollback to V2321 passed.
- Payload captured: no.

Cause:

- The helper exited with rc `2` before tracing.
- Helper logs contained only usage output.
- Root cause: service passed `--duration-sec 180`, but the V2449 helper accepts at most `120`.
- Fix applied before live attempt 2: cap service helper duration at `120`.

## Live Attempt 2

Private run directory:

- `workspace/private/runs/audio/v2450-acdb-m1-diag-observer-20260615-161442`

Result:

- Decision: `v2450-acdb-m1-diag-observer-partial-helper-still-running-before-rollback-rollback-pass`
- Android flash/stage/module activation/playback/cleanup/rollback completed.
- Final rollback to V2321 passed; post-run native selftest was `fail=0`.
- Payload captured: no.

Diagnostic counters:

- Helper starts: `13`
- JSONL files: `13`
- Target pids observed: `799, 919, 3622, 4362, 4588, 5168, 6708, 6947, 7257, 7262, 8622, 8678, 8860`
- `syscall_stop_count`: `257929`
- `syscall_entry_count`: `129020`
- `ioctl_any_entry_count`: `2619`
- `ioctl_fd_match_count`: `0`
- `ioctl_fd_miss_count`: `2619`
- `ioctl_unmatched`: `128`
- Missing terminal `stop` JSONL files: `5`
- Payload hashes: none
- Raw payload in public summary: no

Key observations:

- The helper now traces successfully and sees many syscalls/ioctls.
- All sampled ioctl fd targets were `/dev/hwbinder` or `/dev/binder`, not `/dev/msm_audio_cal`.
- Pulled fd snapshots did not show `/dev/msm_audio_cal` in the observed process fd tables.
- The Android activity launch occurred, but this run did not show the previous ACDB/AppType logcat edge.
- The temporary Magisk service starts at Android boot. In this run, post-module ADB reacquire took about `207s`, while the service capture window was `180s` and individual helpers were capped to `120s`. This means the service can finish or age out before the host can start the AudioTrack stimulus.

## Interpretation

V2450 did not refute the ACDB payload-capture route. It refuted the current M1 timing shape:

- A boot-time Magisk service module is useful for early Android-good observation.
- For host-triggered playback after a long Android/Magisk reboot settle, service-only capture is not sufficient unless the helper can be started or restarted near the stimulus window.
- The correct Magisk direction remains a temporary Android measurement capsule, but the capsule needs a host-coordinated late observer in addition to any boot service hook.

## Next Frontier

V2451 should not attempt native ACDB replay. The next bounded unit should implement a hybrid M1 strategy:

1. Keep the temporary Magisk module as the Android-good measurement capsule.
2. After post-module ADB/root settle and before AudioTrack playback, start a late diagnostic observer from the already-staged module helper.
3. Keep the boot service optional as an early-edge observer, but do not rely on it for the host-triggered playback edge.
4. Require helper terminal `stop` records before collection; classify missing stops as partial.
5. Preserve the same boundaries: no native calibration ioctl, no native speaker write, cleanup before V2321 rollback.

Until a late observer captures decoded request headers, payload hashes, mem-handle policy, and cleanup ordering, native ACDB replay remains blocked.
