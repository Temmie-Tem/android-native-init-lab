# NATIVE_INIT V2397 — Android/Magisk ACDB live runner source gate

## Scope

Source/test-only unit after V2396. No flash, Android boot, Magisk install, Android playback, ADSP
command, `/dev/snd` open, mixer write, HAL ptrace, or ACDB ioctl ran in this unit.

V2397 extends the V2396 planner script into an exact-gated live runner while leaving default behavior
host-only.

Touched public paths:

- `workspace/public/src/scripts/revalidation/native_audio_acdb_android_measurement_planner_v2396.py`
- `tests/test_native_audio_acdb_android_measurement_planner_v2396.py`

## Decision

`--run-live` is now implemented but gated by the exact AUD-5A phrase. Without that phrase the CLI
returns a JSON refusal before materializing live state, flashing Android, or touching the device.

Required future live approval phrase remains:

```text
AUD-5A-android-acdb-magisk-measurement go: rollbackable Android AudioTrack speaker ACDB/AppType capture, transient Magisk-root observer only, no native speaker write, rollback to V2321
```

## Live runner behavior

When invoked with the exact phrase, V2397 will:

1. Force private module template materialization under `workspace/private`.
2. Verify the V2396 dry-run preflight reports `future_live_ready=true` and `command_safety.ok=true`.
3. Create a private run directory under `workspace/private/runs/audio/v2397-android-acdb-measurement-*`.
4. Seal the Android boot image into that run directory as `android_boot_0600.img`.
5. Flash Android through `native_init_flash.py --post-flash-target android-adb`.
6. Stage pinned `tinymix`, the transient Magisk-style observer files, the private module zip, and the
   V2373 AudioTrack APK.
7. Capture baseline observer state.
8. Clear logcat, start full logcat capture, and record the ACDB/App Type filter for offline parsing.
9. Start bounded Android framework `AudioTrack` speaker playback.
10. Capture active and post observer state.
11. Pull `/cache/a90-audio-acdb-v2396/` into the private run directory.
12. Cleanup Android-side artifacts, reboot Android to recovery, and roll back to V2321.

The runner records `v2397-android-acdb-measurement-captured-rollback-pass` only if capture completes
and rollback finishes. If rollback needs fallback, it records that explicitly. It still does not parse
or classify the ACDB sequence as native-solvable; that remains a post-live analysis step.

## Safety boundary

The live runner preserves the V2396 boundaries:

- exact approval phrase required for live mode;
- boot partition only, through the checked flash helper;
- Android playback only via the existing framework APK path;
- transient Magisk-root observer only, no persistent `magisk --install-module` default;
- no native speaker write;
- no native `/dev/snd` open;
- no native mixer set;
- no native ACDB ioctl;
- no HAL ptrace by default;
- raw logs and module artifacts remain under `workspace/private`;
- rollback to V2321 is mandatory after any Android flash.

## Validation

Commands run:

```text
python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_android_measurement_planner_v2396.py tests/test_native_audio_acdb_android_measurement_planner_v2396.py
PYTHONPATH=tests python3 -m unittest tests/test_native_audio_acdb_android_measurement_planner_v2396.py
PYTHONPATH=tests python3 -m unittest discover -s tests
python3 workspace/public/src/scripts/revalidation/native_audio_acdb_android_measurement_planner_v2396.py --dry-run --materialize-module-template
python3 workspace/public/src/scripts/revalidation/native_audio_acdb_android_measurement_planner_v2396.py --run-live --approval nope
git diff --check
```

Focused unit tests: `10` tests passed. Full test suite: `1079` tests passed.

Dry-run with module materialization still reports:

```json
{
  "decision": "v2396-audio-acdb-android-magisk-planner-dry-run",
  "ok": true,
  "future_live_ready": true,
  "blockers": [],
  "command_safety_ok": true
}
```

Bad approval live probe returned JSON refusal:

```json
{
  "decision": "v2397-android-acdb-measurement-live-refused",
  "ok": false,
  "reason": "exact AUD-5A Android ACDB measurement approval phrase is required for --run-live",
  "rolled_back": false
}
```

No live-approved command was run.

## Next frontier

V2398 can run the exact-gated V2397 live measurement only after the operator supplies the full AUD-5A
phrase. The expected output is private Android logcat plus baseline/active/post observer artifacts.
Only after that capture should the project decide whether native speaker audio can use a bounded ACDB
bootstrap or should be classified as Android HAL dependent.
