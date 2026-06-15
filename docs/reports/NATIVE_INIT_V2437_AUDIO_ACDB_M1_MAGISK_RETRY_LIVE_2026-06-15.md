# NATIVE_INIT_V2437_AUDIO_ACDB_M1_MAGISK_RETRY_LIVE_2026-06-15

## Summary

V2437 executed the exact-gated Android M1 Magisk-module retry runner from V2436.
The checked Android handoff, Magisk root settle, module-namespace read-only
probes, pre-residue check, and root-side staging-directory setup all passed.
The run then stopped before module installation or activation because `adb push`
could not write into the root-created `module-stage` directory:

```text
adb: error: stat failed when trying to push to
/data/local/tmp/a90-audio-acdb-m1-v2429/module-stage/module.prop:
Permission denied
```

No Magisk `service.sh` module was installed, no Android reboot for module
activation occurred, no ACDB payload artifact was captured, and no native audio
state was touched. Cleanup-finally and checked rollback to V2321 completed; the
final native selftest remained `fail=0`.

## Exact Gate

```text
AUD-5J-acdb-m1-magisk-module-retry go: rollbackable Android AudioTrack speaker msm_audio_cal ioctl payload capture with temporary Magisk service module, corrected su-c staging, exact cleanup, no native calibration ioctl, no native speaker write, rollback to V2321
```

## Evidence

- Private run directory:
  `workspace/private/runs/audio/v2437-acdb-m1-magisk-module-retry-20260615-135015`
- Runner source: `native_audio_acdb_m1_magisk_module_retry_live_handoff_v2436.py`
- Runner decision: `v2436-acdb-m1-magisk-module-retry-failed-before-rollback`
- Runner `ok`: `false`
- `rolled_back`: `true`
- Android boot image sealed to private run copy, mode `0600`, SHA256 matched
  `c15ce425abb8da41f0b1696d19d05a625fd7cec949b4ae50651a5f1e7293057b`
- Final native image:
  `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`
- Final native selftest: `pass=11 warn=1 fail=0`

## Step Timeline

| Step | Result | Notes |
| --- | --- | --- |
| `flash-android` | pass | checked helper, 71.010 s |
| `android-post-handoff-settle-0` | pass | `adb wait-for-device` |
| `android-post-handoff-settle-1` | pass | boot-complete check |
| `android-post-handoff-settle-2` | pass | `su -c id` root check |
| `stage-0` | pass | Magisk namespace read-only probe |
| `stage-1` | pass | mount-master read-only probe |
| `stage-2` | pass | `A90_M1_RESIDUE_CHECK_OK` |
| `stage-3` | pass | root-side `module-stage` setup |
| `stage-4-adb-wait-before-push` | pass | ADB still available |
| `stage-4` | fail | `adb push` permission denied into root-owned stage dir |
| `cleanup-finally-0` | pass | `adb wait-for-device` |
| `cleanup-finally-1` | non-fatal fail | APK uninstall returned rc 1; install had not occurred |
| `cleanup-finally-2` | pass | root cleanup script completed |
| `cleanup-finally-3` | pass | residue listing check |
| `android-reboot-recovery-for-rollback` | pass | Android recovery handoff |
| `rollback-v2321` | pass | checked V2321 rollback, 66.000 s |

## Root Cause

The V2436 runner creates the remote staging tree through Magisk root and sets:

```text
chmod 700 "$RUN_DIR" "$STAGE_DIR" "$STAGE_DIR/bin" "$ARTIFACT_DIR"
```

The following `adb push` commands run as the Android `shell` user. They therefore
cannot stat/write paths inside the root-owned `0700` `module-stage` directory.
This is a runner staging design bug, not evidence that Magisk modules are
blocked.

V2435 already proved that exact create/remove under `/data/adb/modules` works
when performed by correctly quoted Magisk root shell commands. V2437 only shows
that the intermediate payload-transfer path must be split by privilege:

1. push files into a shell-writable staging area under `/data/local/tmp`, or
   make only the inert staging area temporarily shell-writable;
2. validate exact filenames and hashes;
3. use `su -c` to copy/install those exact files into
   `/data/adb/modules/a90_audio_acdb_m1_v2429`;
4. tighten permissions on the final module path;
5. keep exact cleanup before V2321 rollback.

## Magisk Direction

The Magisk-module direction remains valid, with the same boundary used in the
earlier Wi-Fi-style handoffs: Magisk is an Android-good measurement and
packaging mechanism, not a native-init runtime dependency.

For this audio frontier, the M1 module should continue to be used only to move
the ptrace observer earlier in Android boot/service lifetime so it can capture
the stock HAL's `/dev/msm_audio_cal` ioctl payloads. It must not become the final
native playback mechanism, and it must not issue native calibration ioctls,
native mixer writes, PCM playback, Wi-Fi actions, DHCP, routes, or ping.

The next iteration should fix staging transport only. It should not change the
observer, module payload, or activation semantics.

## Classification

`m1-staging-transfer-permission-denied-before-install`

The module path is still viable. The failed boundary is:

```text
root-created 0700 staging directory + shell-user adb push
```

not:

```text
Magisk module namespace blocked
```

and not:

```text
early payload capture failed after module activation
```

## Next Unit

V2438 should be host-only:

- keep V2436's exact-gated runner wrapper;
- change module-file transfer to a shell-writable incoming directory under
  `/data/local/tmp/a90-audio-acdb-m1-v2429/`;
- add manifest/hash validation before root install into `/data/adb/modules`;
- keep exact pre-residue and exact cleanup markers;
- keep `magisk --install-module` deferred;
- keep live activation behind a fresh exact gate after static validation.

