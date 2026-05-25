# Native Init V913 Android eSoC GPIO Timeline Handoff Plan Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| handoff wrapper static validation | `scripts/revalidation/android_esoc_gpio_timeline_handoff_v913.py` | `py_compile pass` |
| handoff plan mode | `tmp/wifi/v913-android-esoc-gpio-timeline-handoff-plan/manifest.json` | `v913-handoff-plan-ready` |

V913 now has both pieces needed for the Android positive-control capture:

- the read-only collector:
  `scripts/revalidation/native_wifi_android_esoc_gpio_timeline_v913.py`;
- the bounded Android boot / capture / native rollback handoff wrapper:
  `scripts/revalidation/android_esoc_gpio_timeline_handoff_v913.py`.

## Plan Evidence

Plan mode selected:

- native rollback image:
  `stage3/boot_linux_v724.img`
- native expected marker:
  `A90 Linux init 0.9.68 (v724)`
- Android boot candidate:
  `backups/baseline_a_20260423_025322/boot.img`
- collector output directory:
  `tmp/wifi/v913-android-esoc-gpio-timeline-handoff-plan/v913-android-esoc-gpio-timeline-run`

The generated step sequence is:

```text
native-version
native-status
hide-menu
native-recovery
wait-recovery
push-android-boot
remote-android-sha
flash-android-boot
readback-android-boot
reboot-android
wait-android
wait-boot-complete
settle-after-boot-complete
v913-android-esoc-gpio-timeline
wait-android-before-rollback
reboot-recovery-for-rollback
wait-rollback-recovery
restore-native
```

Plan mode did not execute device commands, reboot, flash, enter recovery, or
write the boot partition.

## Guardrails

The handoff wrapper keeps these flags false in plan mode and is designed to
preserve them during the Android collector step:

- `wifi_bringup_executed=false`
- `credential_use_executed=false`
- `dhcp_route_executed=false`
- `external_ping_executed=false`
- `provider_sysfs_write_executed=false`
- `gpio_write_executed=false`
- `esoc_ioctl_executed=false`
- `native_subsys_trigger_executed=false`
- `module_load_unload_executed=false`

Live `run` still requires explicit flags:

```text
--allow-android-boot-flash
--assume-yes
--i-understand-native-rollback
```

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/android_esoc_gpio_timeline_handoff_v913.py
python3 scripts/revalidation/android_esoc_gpio_timeline_handoff_v913.py \
  --out-dir tmp/wifi/v913-android-esoc-gpio-timeline-handoff-plan \
  plan
```

## Next

Run the V913 handoff live only when ready to temporarily boot Android and then
restore native v724:

```bash
python3 scripts/revalidation/android_esoc_gpio_timeline_handoff_v913.py \
  --allow-android-boot-flash \
  --assume-yes \
  --i-understand-native-rollback \
  run
```

If the collector proves the Android-positive GPIO/eSoC order, proceed to V914
source/build-only helper support for
`wifi-companion-mdm-helper-runtime-subsys-trigger-capture`.
