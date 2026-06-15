# NATIVE_INIT V2435 — Magisk Cleanup-Probe Live Run

Date: 2026-06-15

## Purpose

Run the V2434 exact-gated cleanup-probe runner once against normal Android. This unit proves
whether the project can create and remove one inert, non-module path under Magisk's module
namespace with deterministic cleanup before any M1 temporary module activation is retried.

This is not an M1 activation run. It does not create `module.prop`, `service.sh`,
`post-fs-data.sh`, `system.prop`, `sepolicy.rule`, executable payloads, playback actions,
ACDB replay, or calibration ioctls.

## Gate

Exact gate used:

```text
AUD-5I-magisk-cleanup-probe go: rollbackable Android Magisk module namespace create-remove probe, inert unique directory only, no module.prop, no service.sh, no reboot before cleanup, rollback to V2321
```

Runner:

```text
workspace/public/src/scripts/revalidation/native_audio_magisk_cleanup_probe_live_handoff_v2434.py
```

Private evidence root:

```text
workspace/private/runs/audio/v2435-magisk-cleanup-probe-20260615-133444/
```

## Result

Decision:

```text
v2434-magisk-cleanup-probe-cleanup-probe-ok-before-rollback-rollback-pass
```

Top-level result:

```text
ok=true
rolled_back=true
cleanup_summary.classification=cleanup-probe-ok
```

Probe path used during Android-good boot:

```text
/data/adb/modules/.a90_v2433_cleanup_probe_v2435_20260615-133444
```

Cleanup summary:

| Field | Value |
| --- | --- |
| `root_readonly_ok` | `true` |
| `root_mount_master_readonly_ok` | `true` |
| `cleanup_step_ok` | `true` |
| `created_marker_seen` | `true` |
| `removed_marker_seen` | `true` |
| `no_residue_seen` | `true` |
| `permission_denied_lines` | `[]` |
| `residue_lines` | `[]` |

## Step Timeline

| Step | Result | rc | Elapsed |
| --- | --- | --- | --- |
| `flash-android` | OK | `0` | `71.168s` |
| `android-post-handoff-settle-0` | OK | `0` | `0.004s` |
| `android-post-handoff-settle-1` | OK | `0` | `0.058s` |
| `android-post-handoff-settle-2` | OK | `0` | `0.074s` |
| `root-readonly-probe` | OK | `0` | `0.248s` |
| `root-mount-master-readonly-probe` | OK | `0` | `0.178s` |
| `magisk-cleanup-create-remove` | OK | `0` | `0.335s` |
| `android-wait-device-before-rollback` | OK | `0` | `0.005s` |
| `android-reboot-recovery-for-rollback` | OK | `0` | `3.044s` |
| `rollback-v2321` | OK | `0` | `66.374s` |

## Rollback / Final Health

The runner rebooted Android to recovery and flashed V2321 through the checked helper. Final native
verification after rollback:

```text
A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)
selftest: pass=11 warn=1 fail=0
```

The device is resident on V2321 after the run.

## Interpretation

V2435 closes the cleanup bridge that V2433/V2434 intentionally placed between read-only Magisk
access and real M1 module activation. The corrected `adb shell "su -c '<script>'"` path can create
and remove one exact inert directory under `/data/adb/modules`, and `su -mm -c` remains available
for mount-master read-only probes. No residue was reported before rollback.

This means the earlier V2430 direct-staging failure is no longer evidence that Magisk's module
namespace is generally blocked. It is consistent with the V2432 conclusion that command
construction/quoting was the likely failure mode.

## Next Step

The next meaningful unit is a new source/test-only M1 retry runner or runner update that uses the
corrected quoting and the V2435 cleanup discipline. It should remain Android-good measurement only:

- temporary module only,
- exact path and cleanup-finally logic,
- no native speaker/mixer/PCM write,
- no `/dev/msm_audio_cal` ioctl from native init,
- no `magisk --install-module` unless direct targeted staging fails again,
- checked Android handoff and V2321 rollback.

Do not proceed directly to native ACDB replay. Native replay remains blocked until M1 or another
Android-good measurement captures raw `msm_audio_cal` command order, decoded headers, private
payload hashes, mem-handle policy, and cleanup behavior.
