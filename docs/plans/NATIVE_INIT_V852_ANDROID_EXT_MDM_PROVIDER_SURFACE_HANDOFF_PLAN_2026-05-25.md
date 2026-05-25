# Native Init V852 Android ext-mdm Provider Surface Handoff Plan

## Goal

Capture an Android positive-control snapshot of the same ext-mdm provider
surface captured by V851, then rollback to native v724.

## Inputs

- V851 native provider snapshot:
  `tmp/wifi/v851-ext-mdm-provider-surface-snapshot/manifest.json`
- Native rollback image:
  `stage3/boot_linux_v724.img`
- Android boot candidate:
  `backups/baseline_a_*/boot.img`

## Method

1. From healthy native v724, enter recovery through the serial bridge.
2. Flash a known Android boot image and verify boot partition readback hash.
3. Boot Android, wait for `sys.boot_completed=1`, then settle briefly.
4. Run Android read-only V852 provider collector over ADB root shell.
5. Reboot recovery and restore native v724 with verification.
6. Compare Android provider surface against V851 native evidence.

## Guardrails

- Handoff may temporarily write the boot partition but must restore native v724.
- Android collector is read-only.
- No Wi-Fi enable/disable, scan/connect, credential use, DHCP/routes, external
  ping, provider sysfs/debugfs write, GPIO export/write, module load/unload,
  direct daemon/service start, or custom kernel flash.

## Success Criteria

- Android boot-complete is reached.
- Android provider surface is captured with mdm3/mss state and provider signals.
- Native v724 rollback verifies `BOOT OK` and selftest `fail=0`.
- The result selects the next native prerequisite below Wi-Fi HAL/connect.

## Commands

```bash
python3 scripts/revalidation/android_ext_mdm_provider_surface_handoff_v852.py \
  --out-dir tmp/wifi/v852-android-ext-mdm-provider-surface-handoff \
  --native-image stage3/boot_linux_v724.img \
  --native-expect-version 'A90 Linux init 0.9.68 (v724)' \
  --allow-android-boot-flash \
  --assume-yes \
  --i-understand-native-rollback \
  run
```
