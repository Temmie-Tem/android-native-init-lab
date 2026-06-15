# NATIVE_INIT V2429 — ACDB M1 Magisk module planner

## Scope

- Unit: host-only M1 temporary Magisk module/service planner after V2428.
- Device action: none.
- Android boot: none.
- Magisk install: none.
- Native speaker write: none.
- Calibration ioctl issued by helper: none.
- Persistent module dependency: none.

## Why M1 is now justified

V2428 proved the fixed M0 observer was correctly staged and running:

- Android handoff/staging/playback/artifact pull/cleanup/rollback passed.
- Final V2321 native `selftest verbose` was `fail=0`.
- The helper emitted `clone-child-resumed` for worker TID `4619`.
- Logcat showed that same TID running the Android-good speaker/ACDB path with `/dev/msm_audio_cal` open.
- The observer still captured `0` `/dev/msm_audio_cal` ioctl entries.

That closes the previous M0 implementation-gap explanations. The remaining useful discriminator is
placement/timing: start the same observer earlier in Android boot/service lifetime.

## Magisk basis

Web references checked during design:

- Magisk module guide: `service.sh` runs in late_start service mode; `post-fs-data.sh` is blocking and should be used only when necessary. Source: https://github.com/topjohnwu/Magisk/blob/master/docs/guides.md
- Magisk internal details: modules and service scripts live under Magisk's `/data/adb` control area. Source: https://topjohnwu.github.io/Magisk/details.html

Design consequence:

- Use `service.sh`, not `post-fs-data.sh`, for the default M1 observer. `post-fs-data` is too early and blocking for this measurement.
- Keep all raw observer artifacts under `/data/local/tmp/a90-audio-acdb-m1-v2429/artifacts`.
- Treat `/data/adb/modules/<module-id>` activation/removal as a future exact-gated Android live step, not something V2429 runs.

## Implementation

New host-only planner:

- `workspace/public/src/scripts/revalidation/native_audio_acdb_m1_magisk_module_planner_v2429.py`

It emits:

- `run_id=V2429`
- `build_tag=v2429-audio-acdb-m1-magisk-module-planner`
- exact future gate:

```text
AUD-5G-acdb-m1-magisk-module-capture go: rollbackable Android AudioTrack speaker msm_audio_cal ioctl payload capture with temporary Magisk service module, no native calibration ioctl, no native speaker write, cleanup module and rollback to V2321
```

It can materialize a private module template under:

- `workspace/private/builds/audio/v2429-acdb-m1-magisk-module/`

Materialized private artifacts from the validation run:

- helper binary: `workspace/private/builds/audio/v2429-acdb-m1-magisk-module/bin/a90_acdb_ioctl_capture_threadset_v2423`
- helper SHA256: `80206c64f7783384be06baa508c03f9492e8c420c6a867821fa8379d5b0f6d9a`
- module zip: `workspace/private/builds/audio/v2429-acdb-m1-magisk-module/a90_audio_acdb_m1_v2429.zip`
- module zip SHA256: `8c5d64acdfd3abe904043b4291b8c0a49d27b0b7c9333028bcdb52773d29d78b`
- zip mode: `0600`
- manifest mode: `0600`

These artifacts are private and are not tracked.

## M1 service behavior

`service.sh` uses `MODDIR="${0%/*}"`, starts a background supervisor, and exits immediately.

The supervisor:

1. Creates `/data/local/tmp/a90-audio-acdb-m1-v2429/artifacts`.
2. Waits for `android.hardware.audio.service` and `audioserver`.
3. Starts the existing V2423 `a90_acdb_ioctl_capture_threadset_v2423` helper once per PID.
4. Uses thread-set clone-following options:
   - `--tgid`
   - `--fd-pid`
   - `--device-substr /dev/msm_audio_cal`
   - `--duration-sec`
   - `--max-bytes`
   - `--max-events`
5. Writes private JSONL and process/fd snapshots only.
6. Stops on bounded duration.

## Hard boundaries

Allowed:

- Android-good measurement packaging only.
- Temporary Magisk service module for earlier observer placement.
- Same V2423 ptrace observer semantics.
- Private run-local artifacts only.
- Future exact-gated activation and cleanup.

Forbidden:

- `magisk --install-module` as a default or baseline command.
- `post-fs-data.sh` default hook.
- Helper-open of `/dev/msm_audio_cal`.
- Calibration ioctl issued by the helper.
- Native ACDB replay.
- Native speaker write, `tinymix set`, `tinyplay`, `/dev/snd` writes.
- Persistent native-init dependency on Magisk/Android.

## Future live sequence

V2429 does not execute this. A future V2430 live unit would need the exact AUD-5G phrase and should:

1. Flash pinned Android with the checked helper.
2. Verify Android ADB and Magisk root.
3. Remove stale M1 module/artifact paths.
4. Stage the private module under `/data/adb/modules/a90_audio_acdb_m1_v2429`.
5. Reboot Android once so `service.sh` starts before ADB staging.
6. Wait for Android ADB/root after reboot.
7. Launch the existing bounded AudioTrack stimulus APK.
8. Pull private artifacts.
9. Remove the module and artifact dir.
10. Reboot Android to recovery and checked-rollback to V2321.

If the M1 module captures ioctl entries, the next unit is private payload decode. If it still captures zero entries while logcat proves the edge, the next escalation is not more M1 retries; it is a fresh analysis of whether ptrace/seccomp/thread state makes syscall capture unsuitable or whether an M2 vendor-wrapper approach is justified.

## Validation

- `python3 -m py_compile` on V2429 planner/test: pass.
- Focused V2429 tests: 4 pass.
- Materialized dry-run with private helper build and module zip: pass.
- Command safety scanner: pass.
- Full unittest suite: pass.
- `git diff --check`: pass.
