# V1000 Android eSoC/GPIO Recapture Handoff Plan

## Goal

Temporarily boot the known-good Android boot image, collect read-only ADB
evidence for the MDM3/eSoC/GPIO/PMIC/PCIe timing gap, then restore the native
v724 boot image.

V1000 exists because V998 removed the SELinux/service-window blocker but WLFW
still did not appear. V999 selected Android-positive read-only recapture before
any new native lower trigger.

## Scope

V1000 reuses the existing bounded V913 handoff and collector:

- handoff wrapper:
  `scripts/revalidation/android_esoc_gpio_timeline_handoff_v913.py`
- Android read-only collector:
  `scripts/revalidation/native_wifi_android_esoc_gpio_timeline_v913.py`

The V913 collector already captures the surfaces required for this gate:

- full `dmesg`;
- focused `dmesg` for MDM/eSoC/GPIO/PMIC/PCIe/MHI/CNSS/WLFW markers;
- focused `/proc/interrupts`;
- `/sys/kernel/debug/gpio` if readable;
- `subsys9` and `esoc0` read-only sysfs surfaces;
- bounded process/fd summaries for `mdm_helper`, `ks`, and related actors.

## Plan Evidence

Plan mode evidence:

```text
tmp/wifi/v1000-android-esoc-gpio-recapture-handoff-plan/manifest.json
```

Plan mode selected:

- native rollback image: `stage3/boot_linux_v724.img`
- Android boot image: `backups/baseline_a_20260423_025322/boot.img`
- V913 collector out dir:
  `tmp/wifi/v1000-android-esoc-gpio-recapture-handoff-plan/v913-android-esoc-gpio-timeline-run`
- step count: `18`

Plan mode did not execute device commands, reboot, flash, run ADB, or mutate the
boot partition.

## Live Command

```bash
python3 scripts/revalidation/android_esoc_gpio_timeline_handoff_v913.py \
  --out-dir tmp/wifi/v1000-android-esoc-gpio-recapture-handoff-live \
  --allow-android-boot-flash \
  --assume-yes \
  --i-understand-native-rollback \
  run
```

## Success Criteria

- Android boot-complete gate passes.
- V913 read-only collector passes.
- Native v724 rollback completes.
- Result contains enough timing evidence to classify at least one of:
  - GPIO135/AP2MDM assertion timing;
  - PMIC GPIO9 reset/deassert timing;
  - GPIO142/MDM2AP interrupt/status timing;
  - PCIe/MHI timing relative to `cnss-daemon wlfw_start`;
  - whether the existing Android evidence is still insufficient and Magisk
    early sampling is required.

## Guardrails

- No Wi-Fi scan/connect/link-up.
- No credential use.
- No DHCP, route mutation, or external ping.
- No GPIO/sysfs/debugfs write.
- No eSoC ioctl from the native side.
- No native `/dev/subsys_esoc0` trigger.
- No module load/unload.
- No firmware mutation.

V1000 does write the boot partition as part of the bounded Android handoff, and
the same wrapper restores the native v724 image afterward.

## Validation

```bash
python3 scripts/revalidation/android_esoc_gpio_timeline_handoff_v913.py \
  --out-dir tmp/wifi/v1000-android-esoc-gpio-recapture-handoff-plan \
  plan
```

Expected plan-mode result:

```text
decision: v913-handoff-plan-ready
pass: True
device_commands_executed: False
device_mutations: False
wifi_bringup_executed: False
external_ping_executed: False
```
