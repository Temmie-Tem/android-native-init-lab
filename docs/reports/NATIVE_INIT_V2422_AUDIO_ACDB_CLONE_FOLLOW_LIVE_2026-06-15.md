# NATIVE_INIT V2422 — Android ACDB clone-follow capture live result

## Scope

- Unit: AUD-5E / N3-CAP clone-following Android-good `/dev/msm_audio_cal` payload observation.
- Device action: checked Android boot handoff, Magisk-root transient observer, Android framework `AudioTrack` speaker playback, private artifact pull, cleanup, checked rollback to V2321.
- Safety boundary: no native calibration ioctl, no native speaker write, no persistent Magisk module, no raw payload bytes in this public report.

## Implementation delta

V2422 adds the exact-gated live runner for the V2421 clone-following observer:

- `workspace/public/src/scripts/revalidation/native_audio_acdb_clone_follow_live_handoff_v2422.py`
- `tests/test_native_audio_acdb_clone_follow_live_handoff_v2422.py`

The V2421 planner was also fixed so the live plan actually installs the Android `AudioTrack` stimulus APK and makes root-owned private artifacts readable before `adb pull`.

## Validation before live

- `python3 -m py_compile` on touched V2421/V2422 scripts and tests: pass.
- Focused V2421 tests: pass.
- Focused V2422 tests: pass.
- Full `python3 -m unittest discover -s tests -v`: 1140 tests passed.
- `git diff --check`: pass.
- Rollback/fallback preflight: V2321, V2237, and V48 boot images present; V2321 SHA matched the pinned rollback SHA.
- V2422 materialized dry-run: `ok=true`, `future_live_ready=true`, no blockers, command-safety pass.

## Live result

Private run directory:

- `workspace/private/runs/audio/v2422-acdb-clone-follow-capture-20260615-111037`

Live decision:

- `v2422-acdb-clone-follow-capture-clone-follow-helper-started-no-msm-audio-cal-ioctl-before-rollback-rollback-pass`

Recovery envelope:

- Android flash through the checked helper: pass.
- Android post-handoff and Magisk-root settle: pass.
- Helper/APK staging and APK launch: pass.
- Private artifact pull and cleanup: pass.
- Checked rollback to V2321: pass.
- Final V2321 health: `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`, `selftest fail=0`.

Observer summary:

| Field | Value |
| --- | --- |
| helper starts | 2 |
| tracee-add events | 2 |
| clone events | 0 |
| ioctl entries | 0 |
| ioctl exits | 0 |
| raw payload in public summary | false |

Observed target processes:

- `android.hardware.audio.service`: PID `795`
- `audioserver`: PID `933`

Helper JSONL summaries show one traced TID per process:

- `msm-audio-cal-clone-p795.jsonl`: `tracee-add tid=795`, no clone events, no ioctl events.
- `msm-audio-cal-clone-p933.jsonl`: `tracee-add tid=933`, no clone events, no ioctl events.

## Crucial negative result

This is **not** evidence that Android skipped ACDB. The stock Android-good ACDB path fired during the capture window.

Logcat evidence from the private run shows the ACDB edge happened in the audio HAL worker TID `4158`:

- `start_output_stream` for deep-buffer playback on speaker.
- `select_devices` changed output to `speaker`, `acdb 15`.
- `send_app_type_cfg_for_device PLAYBACK app_type 69941, acdb_dev_id 15, sample_rate 48000`.
- `ACDB -> send_audio_cal, acdb_id = 15, path = 0, app id = 0x11135`.
- `AUDIO_SET_AUDPROC_CAL cal_type[11] acdb_id[15] app_type[69941]`.
- `AUDIO_SET_AFE_CAL cal_type[16] acdb_id[15]`.

The HAL process had `/dev/msm_audio_cal` open:

- `proc-795-fd.txt`: fd `13 -> /dev/msm_audio_cal`.

The initial task snapshots did not contain worker TID `4158`:

- PID `795` initial task count: 12.
- PID `933` initial task count: 18.
- `4158` absent from `proc-795-tasks-initial.txt`.

Therefore the V2421/V2422 observer attached only to process-main TIDs (`795`, `933`). `PTRACE_O_TRACECLONE` only reports clone events created by traced TIDs. A new HAL worker created by another already-existing untraced thread, or by a path outside the traced main TID, is not caught.

## Magisk module direction

The Wi-Fi-style Magisk direction remains useful, but the result does **not** justify jumping straight to a persistent or temporary boot module yet.

Current tiering:

- **M0 remains first:** transient Magisk-root observer staged under `/data/local/tmp`, cleaned before rollback.
- **Next M0 fix:** attach all existing TIDs in the target process before playback, and enable clone-following on every traced TID. This addresses the measured miss directly.
- **M1 temporary Magisk module:** justified only if hybrid attach-all-existing-TIDs + clone-following M0 still misses a logcat-proven ACDB edge because the observer must be active before the audio HAL process or its worker pool exists.
- **If M1 is used:** package the same hybrid observer at Android boot time. Do not package the older polling-only watcher, and do not make Magisk a native-init playback dependency.

This matches the Wi-Fi precedent: use Android/Magisk to observe the stock-good producer path, then port only reviewed facts into native init.

## Classification

V2422 closes the single-main-TID clone-following route as insufficient.

The blocker is now observer coverage, not Android/Magisk root, APK playback, `/dev/msm_audio_cal` reachability, or absence of ACDB activity.

## Next unit

V2423 should be host-only first:

1. Implement a hybrid thread-set observer that attaches every existing TID under `/proc/<tgid>/task/*` for each target process.
2. Set `PTRACE_O_TRACECLONE` on every attached TID.
3. Keep fd resolution against the owning TGID (`/proc/<tgid>/fd`), not each TID.
4. Preserve the same raw-payload rules: private JSONL only, public command numbers/lengths/decoded headers/hashes only.
5. Keep the exact Android handoff/rollback boundary unchanged for a later V2424 live run.

Escalate to an M1 temporary Magisk boot-module observer only if that hybrid M0 route still misses a confirmed ACDB edge.
