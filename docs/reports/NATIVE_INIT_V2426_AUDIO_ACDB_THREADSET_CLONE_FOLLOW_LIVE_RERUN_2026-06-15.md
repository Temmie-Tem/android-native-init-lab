# NATIVE_INIT V2426 — ACDB thread-set clone-follow live rerun

## Scope

- Unit: exact-gated Android/Magisk M0 ACDB payload-capture rerun after V2425 ADB stage hardening.
- Device action: rollbackable Android handoff, then checked rollback to V2321.
- Native action: none.
- Native speaker write: none.
- Calibration ioctl issued by helper: none.
- Persistent Magisk module: none.

## Code delta

V2426 adds a thin live-runner wrapper around the V2424/V2425 runner so the rerun has its own run/build identity:

- `run_id=V2426`
- `build_tag=v2426-audio-acdb-threadset-clone-follow-live-rerun`
- V2425 `adb wait-for-device` staging waits inherited before stage indices `1`, `2`, and `3`

The shared V2424 runner was also made wrapper-safe by replacing hard-coded `v2424` decision prefixes with a `RUN_ID`-derived decision slug. The live result from this run still contains the legacy inherited decision prefix because it was produced before that cleanup; the run directory and `run_id` are V2426.

## Live result

Private evidence directory:

- `workspace/private/runs/audio/v2426-acdb-threadset-clone-follow-capture-20260615-115105/`

Safety envelope:

- Pre-live native baseline: V2321 `A90 Linux init 0.9.285`.
- Pre-live `selftest verbose`: `fail=0`.
- Android flash/handoff: pass.
- Post-handoff `adb wait-for-device`/boot/root settle: pass.
- Stage waits before observer/controller/APK push/install: pass.
- Playback stimulus: pass.
- Artifact pull and cleanup: pass.
- Rollback to V2321: pass.
- Final native `selftest verbose`: `fail=0`.

Observer summary:

- helper starts: `2` (`android.hardware.audio.service` / `audioserver` candidates)
- tracee-add events: `31`
- clone events: `1`
- captured `/dev/msm_audio_cal` ioctl entries: `0`
- captured ioctl exits: `0`
- helper errors: `0`
- raw payload bytes in public report: `0`

Private JSONL summaries:

- `msm-audio-cal-threadset-p796.jsonl`: `tracee_adds=14`, `clone_events=1`, `captured_entries=0`, `timed_out=false`
- `msm-audio-cal-threadset-p925.jsonl`: `tracee_adds=17`, `clone_events=0`, `captured_entries=0`, `timed_out=true`

Logcat did prove the Android-good ACDB/App Type edge during this same capture window:

- stimulus begin marker appeared.
- `select_devices` switched deep-buffer playback to speaker `acdb 15`.
- ACDB loader emitted topology/table/calibration calls, including `AUDIO_SET_AUDPROC_CAL` and `AUDIO_SET_AFE_CAL`.
- The active audio worker TID was `4578` under process `796`.
- `/proc/796/fd` showed fd `13 -> /dev/msm_audio_cal`.

## Interpretation

This is not a staging failure anymore; V2425's ADB wait fix worked.

However, this run is **not yet sufficient to escalate to an M1 temporary Magisk boot module**. The V2426 private JSONL shows a concrete M0 implementation gap: the helper observed clone creation for child TID `4578` (`tracee-add` + `clone`), and logcat later attributes the ACDB edge to that same TID, but the helper did not record any syscall stops or ioctl entries from it.

Source inspection of `a90_acdb_ioctl_capture_threadset_v2423.c` explains a plausible miss: on `PTRACE_EVENT_CLONE`, the helper records the child TID but only resumes the parent task immediately. It does not immediately initialize/resume the new child tracee in the clone-event branch. Therefore V2426 is better classified as **M0 clone-child resume gap**, not as a proven Magisk delivery-timing miss.

## Magisk direction

Keep the Wi-Fi-style Magisk strategy, but do not use it as the next step yet:

- **M0 remains primary**: transient Android/Magisk-root helper staged for the checked Android handoff.
- **M1 temporary Magisk module remains reserved**: use only if a fixed M0 observer, with clone-child resume handling, still misses a logcat-proven `/dev/msm_audio_cal` edge.
- **No native-init Magisk dependency**: Magisk is only an Android-good measurement/packaging layer for extracting ACDB payload facts.
- If M1 becomes justified later, it should package the same observer earlier in Android boot and change only delivery timing, not add native speaker writes or persistent runtime dependencies.

## Next unit

V2427 should be host-only helper hardening:

1. Fix clone-child handling so a child tracee from `PTRACE_EVENT_CLONE` is initialized and resumed for syscall tracing.
2. Add focused host tests/static checks around the clone branch behavior if practical.
3. Keep command safety unchanged: no helper-open of `/dev/msm_audio_cal`, no calibration ioctl issued by the helper, no persistent Magisk module.
4. Then perform a new exact-gated live rerun only after V2427 lands.

Native ACDB replay remains blocked until command order, decoded headers, private payload hashes, and cleanup policy are pinned.

## Validation

- `python3 -m py_compile` on touched V2424/V2426 runners and V2426 tests: pass.
- Focused V2426 tests: 3 pass.
- Focused V2424 regression tests: 6 pass.
- Full unittest suite: 1155 pass.
- `git diff --check`: pass.
