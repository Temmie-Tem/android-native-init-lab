# NATIVE_INIT V2396 — Android/Magisk ACDB measurement planner

## Scope

Host-only implementation unit after V2395. No flash, Android boot, Magisk module install, ADSP
command, `/dev/snd` open, mixer write, PCM playback, HAL ptrace, or ACDB ioctl ran in this unit.

V2396 turns the V2395 Branch-A discriminator into a dry-run-only planner:

- public planner script: `workspace/public/src/scripts/revalidation/native_audio_acdb_android_measurement_planner_v2396.py`
- public tests: `tests/test_native_audio_acdb_android_measurement_planner_v2396.py`
- generated private module template: `workspace/private/builds/audio/v2396-acdb-magisk-measurement-module/`

## Decision

`v2396-audio-acdb-android-magisk-planner-dry-run` passed in host-only mode.

The future live plan is ready from the host side:

```json
{
  "ok": true,
  "future_live_ready": true,
  "future_live_blockers": [],
  "command_safety_ok": true
}
```

Required future live approval phrase:

```text
AUD-5A-android-acdb-magisk-measurement go: rollbackable Android AudioTrack speaker ACDB/AppType capture, transient Magisk-root observer only, no native speaker write, rollback to V2321
```

## What the planner does

The planner reuses the proven Android route-delta handoff machinery instead of inventing a new flash
path:

1. Seal the known Android boot image into a private `0600` run-local copy.
2. Flash Android via `native_init_flash.py --post-flash-target android-adb --expect-android-magic`.
3. Stage the pinned V2345 `tinymix`, the V2373 modern-target AudioTrack APK, and a transient
   Magisk-style observer module under `/data/local/tmp/a90-audio-acdb-v2396/`.
4. Run baseline, active, and post observer snapshots via `su -c`.
5. Capture full Android logcat with an offline ACDB/App Type filter.
6. Start one bounded low-amplitude Android framework `AudioTrack` speaker playback.
7. Pull observer artifacts from `/cache/a90-audio-acdb-v2396/` into a private run directory.
8. Uninstall/cleanup Android-side artifacts, reboot Android to recovery, and roll back to V2321.

This remains a plan only in V2396. No live command was executed.

## Magisk module direction

V2396 deliberately does **not** use a persistent Magisk module install by default.

The default delivery model is a transient Magisk-root helper:

- generate a Magisk-style module layout privately;
- stage it under `/data/local/tmp/a90-audio-acdb-v2396/module/`;
- invoke `service.sh`/`a90_acdb_probe.sh` manually through `su -c` after Android is booted;
- remove staged files before rollback.

This keeps the Wi-Fi-style advantage of Magisk packaging and root delivery without making Magisk a
native-init runtime dependency or leaving a boot-time module as the default. Full `magisk
--install-module` is intentionally absent from the command plan.

Generated private files:

| Artifact | Mode | Purpose |
|---|---:|---|
| `workspace/private/builds/audio/v2396-acdb-magisk-measurement-module/module.prop` | `0600` | Magisk module metadata |
| `workspace/private/builds/audio/v2396-acdb-magisk-measurement-module/service.sh` | `0700` | manual/boot-style entrypoint |
| `workspace/private/builds/audio/v2396-acdb-magisk-measurement-module/system/bin/a90_acdb_probe.sh` | `0700` | ACDB/App Type observer helper |
| `workspace/private/builds/audio/v2396-acdb-magisk-measurement-module/a90_audio_acdb_probe_v2396.zip` | `0600` | private module zip |
| `workspace/private/builds/audio/v2396-acdb-magisk-measurement-module/manifest.json` | `0600` | private artifact manifest |

Private dry-run evidence:

- module zip SHA256: `4e14e9fe4b8995c5e5beb828d701350e933444282ebf68dc3285b96f07d81e2f`
- private manifest SHA256: `ce45d4c881d0edaeb53cb873588dc2b77311c445913bd1d9b172d6ecfdaef9c7`

## Captured state in the future live plan

The observer helper records only read-only state:

- audio-related `getprop` keys;
- process list;
- `android.hardware.audio.service` PID, maps, and fd table;
- `/dev/msm_audio_cal`, `/dev/ion`, and `/dev/snd` node state;
- `/proc/asound/cards` and `/proc/asound/pcm`;
- `tinymix -D 0 --all-values`;
- bounded `dmesg | tail -n 400`.

The logcat capture is filtered offline for:

```text
ACDB|acdb|audio_hw|platform|adm|afe|q6asm|app_type|App Type|AudioFlinger|AudioTrack|A90_AUDIO_STIMULUS|msm_audio_cal|send_afe_cal|q6asm_send_cal|adm_open
```

Optional HAL `strace` is represented as disabled-by-default metadata only. It is not part of the
future default live plan because ptrace can perturb audio timing.

## Safety boundary

The V2396 command safety scanner passed. The planned default command set excludes:

- `tinyplay`;
- native speaker pilot commands;
- native `tinymix set`;
- direct block writes;
- `fastboot`;
- `magisk --install-module`;
- Android audio policy mutation commands;
- `settings put`.

V2396 also preserves these hard boundaries:

- no native-init runtime dependency on Magisk or Android services;
- no native speaker write;
- no `/dev/snd` open from native;
- no mixer writes outside existing Android route snapshot/playback behavior;
- all raw Android logs and generated module artifacts stay under `workspace/private/`;
- any future live run must roll back to V2321.

## Validation

Commands run:

```text
python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_android_measurement_planner_v2396.py tests/test_native_audio_acdb_android_measurement_planner_v2396.py
PYTHONPATH=tests python3 -m unittest tests/test_native_audio_acdb_android_measurement_planner_v2396.py
python3 workspace/public/src/scripts/revalidation/native_audio_acdb_android_measurement_planner_v2396.py --dry-run --materialize-module-template
```

Focused unit tests: `6` tests passed.

Dry-run result:

```json
{
  "decision": "v2396-audio-acdb-android-magisk-planner-dry-run",
  "ok": true,
  "future_live_ready": true,
  "blockers": [],
  "command_safety_ok": true
}
```

## Next frontier

V2397 can run the exact-gated live Android ACDB/App Type measurement using the V2396 planner. It
must use the full approval phrase above, perform the checked Android handoff, collect only private
artifacts, and roll back to V2321. It still must not classify native speaker audio as solved until
the captured ACDB/App Type sequence proves a bounded native bootstrap path.
