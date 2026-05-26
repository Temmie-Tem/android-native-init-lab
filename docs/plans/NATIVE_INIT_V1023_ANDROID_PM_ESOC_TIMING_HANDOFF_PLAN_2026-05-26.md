# V1023 Android PM/eSoC Timing Handoff Plan

- date: `2026-05-26`
- type: bounded Android handoff + read-only timing capture
- selected after: V1022 Android PM/eSoC sampler source validation

## Objective

Run V1022 in a controlled Android handoff so Android-good PM/eSoC timing is
captured without relying on a manual Android boot.

V1022 is useful only when Android ADB is present. The current device state before
V1023 was native init v724 with ACM bridge present and no Android ADB. V1023
therefore temporarily flashes a known Android boot image, starts V1022 as soon
as ADB reaches `device`, captures a boot-complete fallback sample, then restores
native init v724.

## Gate

Execution order:

1. verify current native `bootstatus`
2. enter TWRP recovery through the native bridge
3. push, hash-check, flash, and read back Android boot image
4. reboot Android and wait for first ADB `device`
5. run V1022 early sampler immediately
6. wait for Android boot-complete
7. run V1022 late fallback sampler
8. reboot recovery
9. push, hash-check, flash, and read back native v724 boot image
10. reboot native and require `BOOT OK`

## Hard Gates

- no native `/dev/subsys_esoc0` retry
- no `/dev/esoc-*` ioctl
- no eSoC notify, image response, or BOOT_DONE
- no GPIO/sysfs/debugfs write
- no Wi-Fi command, scan/connect/link-up, credential use, DHCP/route, or external ping
- Android boot write must be followed by native readback and native `BOOT OK`

## Validation

Static:

```bash
python3 -m py_compile scripts/revalidation/android_pm_esoc_timing_handoff_v1023.py
python3 scripts/revalidation/android_pm_esoc_timing_handoff_v1023.py --allow-android-boot-flash --assume-yes --i-understand-native-rollback dry-run
git diff --check
```

Live:

```bash
RUN_DIR="tmp/wifi/v1023-android-pm-esoc-timing-handoff-live-$(date +%Y%m%d-%H%M%S)"
echo "$RUN_DIR" > tmp/wifi/latest-v1023-android-pm-esoc-timing-handoff.txt
python3 scripts/revalidation/android_pm_esoc_timing_handoff_v1023.py \
  --out-dir "$RUN_DIR" \
  --allow-android-boot-flash \
  --assume-yes \
  --i-understand-native-rollback \
  run
```

## Success Criteria

- V1022 early or late capture produces useful Android PM/eSoC timing evidence.
- Native v724 rollback is verified by native boot readback and `BOOT OK`.
- No active Wi-Fi control, credential use, DHCP/route, or external ping occurs.

