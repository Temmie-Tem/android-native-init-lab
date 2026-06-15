# NATIVE_INIT V2424 — ACDB thread-set clone-follow live runner and first live result

## Scope

- Unit: AUD-5F / Android-good `/dev/msm_audio_cal` payload observation with the V2423 hybrid thread-set clone-following observer.
- Device action: exact-gated Android handoff executed under the preauthorized recoverable envelope.
- Native replay: none.
- Native speaker write: none.
- Calibration ioctl from native init: none.
- Persistent Magisk module install: none.

## Source changes

V2424 adds the exact-gated live runner for the V2423 observer:

- `workspace/public/src/scripts/revalidation/native_audio_acdb_threadset_clone_follow_live_handoff_v2424.py`
- `tests/test_native_audio_acdb_threadset_clone_follow_live_handoff_v2424.py`

The runner follows the existing checked Android handoff model:

1. Seal the pinned Android boot image into the private run directory as `0600`.
2. Flash Android with `native_init_flash.py --post-flash-target android-adb`.
3. Re-check Android boot-complete and `adb shell su -c id`.
4. Stage the V2423 private static observer and AudioTrack APK.
5. Start full logcat capture and the V2423 thread-set clone-follow controller.
6. Run bounded Android framework `AudioTrack` speaker playback.
7. Pull private artifacts.
8. Clean up Android scratch paths.
9. Reboot Android to recovery and roll back to V2321 with checked helper verification.

Public summaries hash raw payload bytes and never include raw `bytes_hex`.

## Validation before live

- `python3 -m py_compile` on the V2424 runner and tests: pass.
- Focused V2424 tests: 5 pass.
- V2424 materialized dry-run:
  - `ok=true`
  - `future_live_ready=true`
  - `future_live_blockers=[]`
  - `command_safety.ok=true`
  - helper SHA256 `804668b1c7350953bc3151b34cdbfa27d32f2802819c58fddc01a74f45268e1d`

## Live run

Private run directory:

- `workspace/private/runs/audio/v2424-acdb-threadset-clone-follow-capture-20260615-113932`

Final decision:

- `v2424-acdb-threadset-clone-follow-capture-failed-before-rollback`

Safety result:

- Android boot flash: pass.
- Android post-handoff settle: pass.
- Magisk root re-check: pass (`su -c id` succeeded).
- Stage 0 remote directory creation: pass.
- Rollback to V2321: pass.
- Final resident checkpoint: V2321.
- Final native selftest: `fail=0`.

## Failure point

The run failed before starting the observer:

- Failed step: `stage-1`.
- Command class: `adb push` of the V2423 private static observer binary.
- Error: `adb: error: failed to get feature set: no devices/emulators found`.

The failure occurred after Android was alive and after the first root shell staging command
succeeded. It is therefore classified as an Android ADB stage-transfer stability gap, not
an ACDB/observer result.

No `payload_capture_summary` exists because capture never started.

## Interpretation

V2424 proves the V2423 live-runner skeleton and rollback envelope are valid, but the first
live attempt did not reach the measurement window. The next useful unit is host-only
runner hardening:

- add `adb wait-for-device` before each `adb push` / `adb install` staging operation,
- keep the existing Android boot-complete and Magisk root settle checks,
- preserve the same V2423 observer semantics,
- rerun only after focused tests prove the stage-wait plan is present.

This does not justify M1 temporary Magisk module escalation. The M0 observer has not yet
been tested because staging failed before helper execution.
