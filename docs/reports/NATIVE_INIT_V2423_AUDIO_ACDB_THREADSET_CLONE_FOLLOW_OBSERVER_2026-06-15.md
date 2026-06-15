# NATIVE_INIT V2423 — ACDB hybrid thread-set clone-follow observer

## Scope

- Unit: AUD-5F host-only implementation after V2422.
- Goal: fix the measured observer-coverage gap by attaching every existing TID in each target audio process, then enabling clone-following on every traced TID.
- Device action: none. No Android boot, no native flash, no playback, no Magisk install, no calibration ioctl.
- Safety boundary: measurement-only observer; raw future JSONL payload bytes remain private-only.

## Why this unit exists

V2422 proved the single-main-TID clone-following model is insufficient:

- Android `AudioTrack` playback succeeded.
- The stock-good ACDB speaker edge fired in audio HAL worker TID `4158`.
- PID `795` had `/dev/msm_audio_cal` open.
- The V2421/V2422 helper attached only TIDs `795` and `933`.
- `PTRACE_O_TRACECLONE` saw zero clone events and captured zero ioctls.
- TID `4158` was absent from the initial task snapshot, meaning it was created during the capture window but not by a traced TID.

`PTRACE_O_TRACECLONE` only follows clones from traced threads. Therefore the next observer must trace the whole existing thread group, not only the process-main TID.

## Implementation

New source files:

- `workspace/public/src/android/acdb_payload_capture/a90_acdb_ioctl_capture_threadset_v2423.c`
- `workspace/public/src/scripts/revalidation/native_audio_acdb_threadset_clone_follow_planner_v2423.py`
- `tests/test_native_audio_acdb_threadset_clone_follow_planner_v2423.py`

The V2423 helper:

1. Accepts `--tgid <pid>` and defaults fd resolution to `/proc/<tgid>/fd`.
2. Enumerates `/proc/<tgid>/task` before playback.
3. Attaches each existing TID with `PTRACE_ATTACH`.
4. Performs up to three attach/rescan passes to reduce the pre-resume race.
5. Sets `PTRACE_O_TRACESYSGOOD | PTRACE_O_TRACECLONE` on every attached TID.
6. Resumes all tracees through syscall stops.
7. Keeps the existing fd-filtered `ioctl` logic: only syscalls whose fd resolves to `/dev/msm_audio_cal` get bounded request-buffer copies.
8. Writes private JSONL only.

The controller still starts one helper per process, but that helper now covers the process thread-set:

- `android.hardware.audio.service` → one `--tgid` helper.
- `audioserver` → one `--tgid` helper.
- Output shape: `msm-audio-cal-threadset-p<TGID>.jsonl`.

## Private build

Materialized dry-run built a private AArch64 static helper:

- Path: `workspace/private/builds/audio/v2423-acdb-threadset-clone-follow-helper/a90_acdb_ioctl_capture_threadset_v2423`
- SHA256: `804668b1c7350953bc3151b34cdbfa27d32f2802819c58fddc01a74f45268e1d`
- Mode: `0700`
- `file`: ARM aarch64, statically linked, stripped.

The build artifact is private and not committed.

## Dry-run result

`native_audio_acdb_threadset_clone_follow_planner_v2423.py --dry-run --materialize-capture-helper`:

- `decision`: `v2423-acdb-threadset-clone-follow-observer-dry-run`
- `ok`: true
- `future_live_ready`: true
- `future_live_blockers`: none
- `command_safety.ok`: true

Watcher contract:

```json
{
  "mode": "threadset-attach-plus-PTRACE_O_TRACECLONE",
  "trace_mode": "threadset-clone-following",
  "helper_args": ["--tgid <pid>", "--fd-pid <pid>"],
  "per_process_output": "msm-audio-cal-threadset-p<TGID>.jsonl"
}
```

Command-safety findings were empty. Forbidden tokens remain absent:

- persistent Magisk install;
- native calibration ioctls;
- `tinyplay` / `tinymix set`;
- raw partition writes / fastboot.

## Magisk module direction

M1 remains deferred.

The Wi-Fi-style Magisk pattern is still valid, but V2423 directly addresses the measured V2422 failure inside M0. The next live attempt should use this hybrid M0 observer first. A temporary Magisk boot module is justified only if V2424 still misses a logcat-proven ACDB edge because the observer must be active before the audio HAL process or worker pool exists.

If M1 is used later, it must package this same hybrid thread-set clone-following observer and only change delivery timing. It must not reintroduce the older polling-only watcher and must not become a native-init runtime dependency.

## Validation

- `aarch64-linux-gnu-gcc -O2 -static -s -Wall -Wextra`: pass.
- `file` confirms private helper is ARM aarch64 static.
- `python3 -m py_compile` on the V2423 planner and test: pass.
- Focused V2423 unit tests: 6 passed.

## Next unit

V2424 should be an exact-gated Android live rerun using the V2423 hybrid observer:

- checked Android handoff;
- Magisk-root transient helper only;
- `AudioTrack` speaker stimulus;
- private artifact pull;
- cleanup;
- checked rollback to V2321;
- no native calibration ioctl or native speaker write.

Interpretation:

- `ioctl_entries > 0` → decode private payload headers/hashes and design native replay boundary.
- `ioctl_entries = 0` while logcat still proves ACDB → classify as true boot-time/early-observer miss and design M1 temporary Magisk boot-module delivery as a separate exact-gated unit.
