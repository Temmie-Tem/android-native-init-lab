# NATIVE_INIT_V2430_AUDIO_ACDB_M1_MAGISK_MODULE_LIVE_2026-06-15

## Summary

V2430 implemented and ran the exact-gated Android-good M1 capture path from V2429:
stage a private temporary Magisk `service.sh` module, reboot Android once so
late_start service mode can start the V2423 thread-set clone-following observer,
launch bounded Android framework `AudioTrack` speaker playback, pull private
artifacts, remove the module, and roll back to V2321.

The run did **not** reach module activation. Direct `su -c` staging into
`/data/adb/modules/a90_audio_acdb_m1_v2429` failed with `Permission denied`.
Cleanup and checked rollback succeeded; final native V2321 `selftest verbose`
reported `fail=0`.

## Scope And Safety

- Run ID: `V2430`
- Build tag: `v2430-audio-acdb-m1-magisk-module-live`
- Runner:
  `workspace/public/src/scripts/revalidation/native_audio_acdb_m1_magisk_module_live_handoff_v2430.py`
- Test:
  `tests/test_native_audio_acdb_m1_magisk_module_live_handoff_v2430.py`
- Private run dir:
  `workspace/private/runs/audio/v2430-acdb-m1-magisk-module-capture-20260615-124447`
- Exact gate used:

```text
AUD-5G-acdb-m1-magisk-module-capture go: rollbackable Android AudioTrack speaker msm_audio_cal ioctl payload capture with temporary Magisk service module, no native calibration ioctl, no native speaker write, cleanup module and rollback to V2321
```

Safety boundaries held:

- no native-init `/dev/msm_audio_cal` open or calibration ioctl issue
- no native speaker/mixer/PCM write
- no `magisk --install-module`
- no `post-fs-data.sh`
- no Wi-Fi/DHCP/routes/ping
- no non-boot partition flashing or raw partition writes
- Android APK was uninstalled during cleanup-finally
- `/data/local/tmp/a90-audio-acdb-m1-v2429` was removed during cleanup-finally
- checked rollback to V2321 completed

## Static Validation

Commands:

```bash
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/native_audio_acdb_m1_magisk_module_live_handoff_v2430.py \
  tests/test_native_audio_acdb_m1_magisk_module_live_handoff_v2430.py
PYTHONPATH=tests python3 -m unittest tests/test_native_audio_acdb_m1_magisk_module_live_handoff_v2430.py
PYTHONPATH=workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/native_audio_acdb_m1_magisk_module_live_handoff_v2430.py \
  --dry-run --materialize-module-template
PYTHONPATH=tests python3 -m unittest discover -s tests
```

Results:

- focused V2430 tests: `5` passed
- full unittest suite: `1167` passed
- materialized dry-run:
  - `ok=true`
  - `future_live_ready=true`
  - `command_safety.ok=true`
  - module helper SHA256:
    `80206c64f7783384be06baa508c03f9492e8c420c6a867821fa8379d5b0f6d9a`
  - module zip SHA256:
    `1bc2a243fe7048bbd0f8ea29be82b28830c08088f88a9d28a2e16c5bdbe9f1de`

## Live Result

Preflight:

- rollback image V2321 SHA256 matched:
  `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- deeper V2237 fallback SHA256 matched:
  `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`
- resident native bridge was reachable on V2321
- resident native `selftest verbose` before live: `fail=0`

Live sequence:

1. Sealed Android boot image into the private run dir with mode `0600`.
2. Flashed Android via checked `native_init_flash.py`.
3. Android ADB/root handoff passed.
4. Staged module files under `/data/local/tmp/a90-audio-acdb-m1-v2429/module-stage`.
5. Installed `com.a90.nativeinit.audio` stimulus APK.
6. Failed while copying module files into `/data/adb/modules/a90_audio_acdb_m1_v2429`.
7. Ran cleanup-finally.
8. Rebooted Android to recovery.
9. Flashed checked V2321 rollback image.
10. Final native `selftest verbose`: `fail=0`.

Runner result:

```json
{
  "decision": "v2430-acdb-m1-magisk-module-capture-failed-before-rollback",
  "ok": false,
  "rolled_back": true,
  "error": "stage-6 failed rc=1"
}
```

The decision string says `failed-before-rollback` because the failure was raised
before the runner appended a success suffix, but `rolled_back=true` and the
checked helper plus final native selftest prove rollback completed.

## Failure Evidence

`stage-6.stderr.txt`:

```text
mkdir: '/data/adb/modules': Permission denied
cp: /data/adb/modules/a90_audio_acdb_m1_v2429/module.prop: Permission denied
cp: /data/adb/modules/a90_audio_acdb_m1_v2429/service.sh: Permission denied
cp: /data/adb/modules/a90_audio_acdb_m1_v2429/README.md: Permission denied
cp: /data/adb/modules/a90_audio_acdb_m1_v2429/bin/a90_acdb_ioctl_capture_threadset_v2423: Permission denied
rm: /data/adb/modules/a90_audio_acdb_m1_v2429/disable: Permission denied
rm: /data/adb/modules/a90_audio_acdb_m1_v2429/remove: Permission denied
chown: /data/adb/modules/a90_audio_acdb_m1_v2429: Permission denied
chmod: /data/adb/modules/a90_audio_acdb_m1_v2429: Permission denied
```

Cleanup proof:

```text
ls: /data/adb/modules/a90_audio_acdb_m1_v2429: No such file or directory
ls: /data/local/tmp/a90-audio-acdb-m1-v2429: No such file or directory
```

## Interpretation

This is not an ACDB payload result. The module never reached the reboot/late_start
activation point, so there are no M1 `msm_audio_cal` ioctl artifacts to compare
against V2428.

The new blocker is Android-side Magisk module staging:

- Magisk `su -c id` worked in the Android handoff.
- `/data/local/tmp` staging and APK install worked.
- direct file placement under `/data/adb/modules` failed with permission denial
  despite using `su -c`.

This means the next unit should be host-only design for the Android/Magisk
staging mechanism, not another blind live rerun. Candidate paths to evaluate:

1. whether Magisk requires its own module-install flow for `/data/adb/modules`;
2. whether `su` mount namespace options or context affect direct access to
   `/data/adb/modules`;
3. whether an equivalent temporary boot hook can be installed and removed
   without making Magisk a native-init runtime dependency.

Any path that uses `magisk --install-module` must get a new explicit safety
design because V2429/V2430 intentionally forbade it.

## Next Unit

V2431 should be host-only first:

- inspect the Magisk staging mechanism already present in the Android image;
- decide whether direct `/data/adb/modules` staging is fixable or whether a
  bounded `magisk --install-module` flow is the only correct interface;
- keep the same boundaries: temporary measurement only, cleanup before rollback,
  no native replay, no native calibration ioctl, no speaker write.

