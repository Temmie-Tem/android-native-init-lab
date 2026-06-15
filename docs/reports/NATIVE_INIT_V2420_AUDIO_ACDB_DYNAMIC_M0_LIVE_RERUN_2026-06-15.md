# V2420 — dynamic M0 ACDB payload capture live rerun

Scope: exact-gated rollbackable Android-good `/dev/msm_audio_cal` payload capture after V2419 added dynamic task polling to the M0 observer.

Device action: checked Android boot handoff, Magisk-root transient observer, Android framework `AudioTrack` speaker playback, private artifact pull, cleanup, checked rollback to V2321. No native calibration ioctl, native speaker write, persistent Magisk install, or native replay ran.

## Decision

`v2420-acdb-dynamic-m0-capture-no-msm-audio-cal-ioctl-observed-before-rollback-rollback-pass`

V2420 proved that the dynamic task watcher works, but it still did not capture `/dev/msm_audio_cal` ioctl entries. The important delta is that the relevant Android audio HAL worker TID was discovered and attached only at the end of the capture window, after the logcat-proven speaker ACDB edge had already occurred. This is no longer the V2416/V2418 static-task-snapshot miss; it is a thread-birth / first-ioctl race.

## Live result

- Android handoff: passed through the checked flash helper.
- Android post-handoff settle and Magisk root: passed.
- Playback stimulus: Android `AudioTrack` ran and produced the speaker calibration edge.
- Artifact pull: passed; private artifacts remain under `workspace/private/runs/audio/v2420-acdb-dynamic-m0-capture-20260615-103647/`.
- Cleanup: passed.
- Rollback: checked V2321 rollback passed; final native `selftest fail=0`.
- Current resident image after rollback: `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`.

## Evidence summary

| Evidence | V2420 result |
| --- | --- |
| `payload_capture_summary.classification` | `no-msm-audio-cal-ioctl-observed` |
| helper starts | `29` |
| ioctl entries / exits | `0` / `0` |
| audio HAL target pid | `804` |
| audioserver target pid | `921` |
| `/dev/msm_audio_cal` | present and open in audio HAL fd table |
| late relevant worker TID | `4761`, comm `writer` |
| dynamic attach for TID `4761` | `A90_V2415_HELPER_START pid=804 tid=4761 remaining=1` |
| TID `4761` JSONL | `start` then `stop`, `captured_entries=0`, `timed_out=false` |

Logcat confirms the stock Android speaker path did run the ACDB/App Type edge on audio HAL TID `4761`:

```text
A90_AUDIO_STIMULUS_BEGIN duration_ms=2000 sample_rate=48000 amplitude=0.05 speaker_hint=true
send_app_type_cfg_for_device PLAYBACK app_type 69941, acdb_dev_id 15, sample_rate 48000
ACDB -> send_audio_cal, acdb_id = 15, path = 0, app id = 0x11135, sample rate = 48000
ACDB -> AUDIO_SET_AUDPROC_CAL cal_type[11] acdb_id[15] app_type[69941]
ACDB -> AUDIO_SET_AFE_CAL cal_type[16] acdb_id[15]
```

A prior capture/VI-feedback calibration edge also appeared on the same TID with `acdb_id=102`, `path=1`, `app id=0x11132`, and `cal_type[17]`. That may matter later for native replay design, but V2420 still does not have raw ioctl request bytes.

## Magisk module direction

The Wi-Fi-style Magisk pattern remains valid, but only as an Android-good measurement/packaging layer. It is not a native-init runtime dependency.

V2420 changes the escalation logic:

- Moving the same polling observer into a temporary Magisk boot module is not enough by itself. The dynamic poller did see the relevant TID, but only with `remaining=1`, after the ACDB logcat edge.
- The next observer must follow thread creation rather than merely poll after creation. The primary next design is a clone-following observer: attach to the audio HAL process before playback and use `PTRACE_O_TRACECLONE` / strace-`-f` style clone following so a new worker TID is stopped at birth before its first ioctl.
- M1 is justified only if clone-following M0 still cannot attach early enough after Android handoff, or if the observer must be active before the audio HAL process itself starts. In that case the M1 module should package the clone-following observer from Android boot, not the current polling-only script.
- M2 vendor wrapper/probe stays deferred unless both clone-following M0 and M1 fail to expose one identified payload edge.

This keeps the useful Wi-Fi precedent: Android/Magisk observes the stock-good producer path, then native init consumes only reviewed facts: ioctl command sequence, decoded headers, lengths, payload hashes, and cleanup policy.

## Classification

`dynamic-m0-caught-thread-but-missed-first-ioctl`

The static snapshot issue is closed. The current blocker is that the ACDB worker thread can be born and complete its first calibration ioctl sequence before a poll-based observer attaches.

## Validation

```text
python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_payload_capture_dynamic_live_handoff_v2420.py tests/test_native_audio_acdb_payload_capture_dynamic_live_handoff_v2420.py
python3 -m unittest discover -s tests -p 'test_native_audio_acdb_payload_capture_dynamic_live_handoff_v2420.py' -v
python3 workspace/public/src/scripts/revalidation/native_audio_acdb_payload_capture_dynamic_live_handoff_v2420.py --dry-run
python3 -m unittest discover -s tests -v
git diff --check
python3 workspace/public/src/scripts/revalidation/a90ctl.py version
python3 workspace/public/src/scripts/revalidation/a90ctl.py status
```

Results:

- Focused V2420 tests: 3/3 pass.
- Full unittest suite: 1129/1129 pass.
- `git diff --check`: pass.
- Device post-rollback status: V2321 resident, `selftest fail=0`.

## Next step

V2421 should be host-only first: design and implement a clone-following payload observer around `PTRACE_O_TRACECLONE` or equivalent strace-`-f` semantics, then dry-run/static-test it before any fresh Android handoff. Do not start by installing a Magisk module that only relocates the same polling observer earlier; that would not address the measured race.
