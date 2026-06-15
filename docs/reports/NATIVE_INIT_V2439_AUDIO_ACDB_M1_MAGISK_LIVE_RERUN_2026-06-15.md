# NATIVE_INIT_V2439_AUDIO_ACDB_M1_MAGISK_LIVE_RERUN_2026-06-15

## Summary

V2439 ran the exact-gated V2438 M1 Magisk-module retry live. It proved the V2438
staging-transfer fix: all module payload files were pushed into the shell-owned
incoming directory, Magisk root validated the exact SHA-256 values, and the
final module path was installed under `/data/adb/modules/a90_audio_acdb_m1_v2429`
with restrictive root-owned permissions.

The run did not reach logcat capture, playback stimulus, or ACDB payload
collection. After the planned Android reboot for Magisk `service.sh` activation,
`adb wait-for-device` and boot-complete recheck both passed, but the immediate
Magisk root check failed with:

```text
adb: no devices/emulators found
```

Cleanup-finally then reacquired ADB, uninstalled the APK, removed the module and
run directory, and rolled back to V2321. Final native selftest remained `fail=0`.

This is not a staging-transfer failure and not a module-namespace blocker. It is
a post-module-reboot ADB/root-settle robustness gap before capture started.

## Exact Gate

```text
AUD-5J-acdb-m1-magisk-module-retry go: rollbackable Android AudioTrack speaker msm_audio_cal ioctl payload capture with temporary Magisk service module, corrected su-c staging, exact cleanup, no native calibration ioctl, no native speaker write, rollback to V2321
```

## Evidence

- Private run directory:
  `workspace/private/runs/audio/v2439-acdb-m1-magisk-module-retry-20260615-141231`
- Runner source: `native_audio_acdb_m1_magisk_module_retry_live_handoff_v2438.py`
- Runner decision: `v2438-acdb-m1-magisk-module-retry-failed-before-rollback`
- Runner `ok`: `false`
- `rolled_back`: `true`
- Final native image:
  `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`
- Final native selftest: `pass=11 warn=1 fail=0`

## Step Timeline

| Step | Result | Notes |
| --- | --- | --- |
| `flash-android` | pass | checked helper, 73.358 s |
| initial `android-post-handoff-settle-0..2` | pass | ADB, boot-complete, Magisk root |
| `stage-0` | pass | Magisk namespace read-only probe |
| `stage-1` | pass | mount-master read-only probe |
| `stage-2` | pass | `A90_M1_RESIDUE_CHECK_OK` |
| `stage-3` | pass | incoming dir setup; `A90_M1_INCOMING_READY` |
| `stage-4..7` | pass | four `adb push` operations into `/incoming/` |
| `stage-8` | pass | stimulus APK install |
| `stage-9` | pass | SHA validation + module install; `A90_M1_INSTALL_OK` |
| `android-reboot-for-magisk-service` | pass | planned module activation reboot |
| post-reboot settle 0 | pass | `adb wait-for-device` after 36.576 s |
| post-reboot settle 1 | pass | boot-complete recheck |
| post-reboot settle 2 | fail | `adb: no devices/emulators found` during `su -c id` |
| `cleanup-finally-0` | pass | ADB reacquired |
| `cleanup-finally-1` | pass | APK uninstalled |
| `cleanup-finally-2` | pass | `A90_M1_CLEANUP_OK` |
| `cleanup-finally-3` | pass | no module/run-dir residue |
| `rollback-v2321` | pass | checked rollback, 72.196 s |

## Stage-9 Install Proof

The final root install step reported:

```text
A90_M1_INSTALL_BEGIN
A90_M1_INCOMING_SHA_OK module.prop 46fc54b76f605f7ee09692981ed86626b7a30af229797c82d10d42e55f26f6dd
A90_M1_INCOMING_SHA_OK service.sh cedb3e3c502421878e4efa9731816eea2c33b121b82d80f2fc666263fccf4945
A90_M1_INCOMING_SHA_OK README.md aa9237b16cb21d52d81d16d6c7f7cf8ad1cdb96fdd7cae7dcdbd489a68f84607
A90_M1_INCOMING_SHA_OK a90_acdb_ioctl_capture_threadset_v2423 80206c64f7783384be06baa508c03f9492e8c420c6a867821fa8379d5b0f6d9a
A90_M1_INCOMING_HASH_OK
A90_M1_INSTALL_OK
```

The installed module listing showed only the expected files:

```text
/data/adb/modules/a90_audio_acdb_m1_v2429:
README.md
bin
module.prop
service.sh

/data/adb/modules/a90_audio_acdb_m1_v2429/bin:
a90_acdb_ioctl_capture_threadset_v2423
```

## Cleanup Proof

Cleanup-finally removed the module and run directory:

```text
A90_M1_CLEANUP_BEGIN
A90_M1_CLEANUP_OK
ls: /data/adb/modules/a90_audio_acdb_m1_v2429: No such file or directory
ls: /data/local/tmp/a90-audio-acdb-m1-v2429: No such file or directory
```

## Classification

`post-module-reboot-adb-root-settle-transient-before-capture`

Closed:

- V2437 staging-transfer permission wall.
- Exact payload hash validation before module install.
- Exact module cleanup after attempted activation.

Still open:

- Whether the temporary `service.sh` observer captures `/dev/msm_audio_cal`
  payload events after module activation.

No payload-capture conclusion can be drawn from V2439 because logcat, playback,
and artifact collection never started.

## Next Unit

V2440 should be host-only runner hardening:

- keep V2438 staging/install unchanged;
- replace the single post-module-reboot `su -c id` root check with a bounded ADB
  re-acquire + Magisk-root retry loop;
- record each failed root-check attempt as metadata;
- proceed only after a clean `uid=0` root check;
- keep exact cleanup and checked V2321 rollback unchanged;
- do not alter the observer, module payload, playback stimulus, or native audio
  boundaries.

