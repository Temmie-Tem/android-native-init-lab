# V1000 Android eSoC/GPIO Recapture Handoff Plan Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| V913 handoff plan mode under V1000 output path | `tmp/wifi/v1000-android-esoc-gpio-recapture-handoff-plan/manifest.json` | `v913-handoff-plan-ready` |

V1000 is ready for a bounded Android handoff run. The actual live handoff has
not run in this report.

## Findings

- Native rollback image is present:
  `stage3/boot_linux_v724.img`.
- Android boot image candidate is present:
  `backups/baseline_a_20260423_025322/boot.img`.
- The Android and native boot images are distinct.
- The generated handoff sequence has `18` steps:
  - native health/status checks;
  - recovery handoff;
  - Android boot image push/flash/readback;
  - Android boot-complete wait;
  - V913 read-only ADB timeline collector;
  - recovery rollback;
  - native image restore.
- Plan mode skipped all device commands and mutations.

## Live Command

```bash
python3 scripts/revalidation/android_esoc_gpio_timeline_handoff_v913.py \
  --out-dir tmp/wifi/v1000-android-esoc-gpio-recapture-handoff-live \
  --allow-android-boot-flash \
  --assume-yes \
  --i-understand-native-rollback \
  run
```

## Guardrails

- Plan mode did not run ADB or serial device commands.
- Plan mode did not reboot, flash, or write the boot partition.
- Live mode must remain read-only from Android userspace: no Wi-Fi
  scan/connect/link-up, no credential use, no DHCP/routes, no external ping, no
  GPIO/sysfs/debugfs write, no eSoC ioctl, and no native subsystem trigger.
- Live mode intentionally writes boot for temporary Android handoff and then
  restores native v724.

## Validation

Executed:

```bash
python3 scripts/revalidation/android_esoc_gpio_timeline_handoff_v913.py \
  --out-dir tmp/wifi/v1000-android-esoc-gpio-recapture-handoff-plan \
  plan
```

Result:

```text
decision: v913-handoff-plan-ready
pass: True
device_commands_executed: False
device_mutations: False
wifi_bringup_executed: False
external_ping_executed: False
```

## Next

Run the live V1000 handoff. If ADB read-only evidence still lacks GPIO transition
timing, plan a separate Magisk early-sampler unit instead of repeating blind
native `/dev/subsys_esoc0` or stale `IWifi.start` retries.
