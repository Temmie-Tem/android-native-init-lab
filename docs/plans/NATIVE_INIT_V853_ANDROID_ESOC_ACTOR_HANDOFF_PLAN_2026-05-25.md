# Native Init V853 Android eSoC Actor Handoff Plan

## Goal

Capture the Android actor/device-node path that brings the mdm3/ext-sdx50m
provider online, then rollback to native v724.

## Inputs

- V852 Android provider positive-control:
  `tmp/wifi/v852-android-ext-mdm-provider-surface-handoff/manifest.json`
- Native rollback image:
  `stage3/boot_linux_v724.img`
- Android boot candidate:
  `backups/baseline_a_*/boot.img`

## Method

1. From healthy native v724, enter recovery through the serial bridge.
2. Flash a known Android boot image and verify boot partition readback hash.
3. Boot Android, wait for `sys.boot_completed=1`, then settle briefly.
4. Run Android read-only V853 actor collector over ADB root shell.
5. Reboot recovery and restore native v724 with verification.
6. Classify eSoC/subsys node ownership, FD holders, SELinux labels, and
   init/ueventd service ordering.

## Guardrails

- Handoff may temporarily write the boot partition but must restore native v724.
- Android collector is read-only.
- No direct open/ioctl of eSoC/subsys nodes; only `/proc/<pid>/fd` symlinks are
  inspected.
- No Wi-Fi enable/disable, scan/connect, credential use, DHCP/routes, external
  ping, provider sysfs/debugfs write, GPIO export/write, module load/unload,
  direct service start, raw eSoC ioctl, or custom kernel flash.

## Success Criteria

- Android boot-complete is reached.
- `/dev/esoc-0` and `/dev/subsys_esoc0` surfaces are captured.
- FD holder, SELinux, ueventd, and init/service-order evidence is captured.
- Native v724 rollback verifies `BOOT OK` and selftest `fail=0`.
- The result selects the smallest native-equivalent prerequisite below Wi-Fi
  HAL/connect.

## Commands

```bash
python3 scripts/revalidation/android_esoc_actor_handoff_v853.py \
  --out-dir tmp/wifi/v853-android-esoc-actor-handoff \
  --native-image stage3/boot_linux_v724.img \
  --native-expect-version 'A90 Linux init 0.9.68 (v724)' \
  --allow-android-boot-flash \
  --assume-yes \
  --i-understand-native-rollback \
  --timeout 45 \
  --recovery-timeout 240 \
  --android-timeout 360 \
  --boot-complete-timeout 360 \
  run
```
