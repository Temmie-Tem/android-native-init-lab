# Native Init V1058 First-Open Runtime Prerequisite Plan

Date: `2026-05-27`

## Goal

Classify the read-only runtime prerequisites for the native count-zero modem first-open path before another PM actor live retry.

V1056 proved that Android can enter `__subsystem_get(): modem count:0` successfully, while native count-zero attempts block.  V1058 checks whether the current native boot has the same lower prerequisites that a successful first open needs, without opening any modem/eSoC device node.

## Inputs

- Current native v724 boot over the ACM bridge.
- V1056 report: `docs/reports/NATIVE_INIT_V1056_PM_FIRST_OPENER_RECLASSIFIER_2026-05-26.md`.
- Native config hard requirement: `firmware_class.path=/vendor/firmware_mnt/image`.
- Expected PIL blob candidates: `modem.b00` and `modem.mdt` under the firmware-class path and sibling modem firmware roots.

## Method

1. Verify native health with `version`, `selftest`, and `netservice status`.
2. Read `firmware_class.path`.
3. Read filtered `/proc/mounts` for firmware/vendor/modem-related mounts.
4. Stat-only check firmware directories and modem PIL blobs.
5. Stat-only check `/dev/subsys_modem`, `/dev/subsys_esoc0`, and `/dev/esoc-0` node presence without opening them.
6. Read MSM subsystem names/states from sysfs.
7. Read filtered dmesg markers for modem/PIL/eSoC/WLFW state, bounded by line count.
8. Produce a private manifest and summary with a route decision.

## Success Criteria

- Evidence captures are written under `tmp/wifi/v1058-first-open-runtime-prereq/` with private file permissions.
- The classifier records whether:
  - `firmware_class.path` is Android-equivalent;
  - global firmware mounts are currently present;
  - `modem.b00` and `modem.mdt` are visible at the firmware-class path;
  - modem/eSoC device nodes exist without being opened;
  - current boot already has lower modem/PIL perturbation markers.
- The decision routes the next cycle to either prerequisite repair or a bounded Android-faithful PM first-open live gate.

## Hard Gates

- Read-only device commands only.
- No `/dev/subsys_modem`, `/dev/subsys_esoc0`, or `/dev/esoc-0` open.
- No eSoC ioctl, actor start, daemon start, service-manager start, Wi-Fi HAL start, scan/connect, credentials, DHCP/routes, external ping, module load, firmware mutation, sysfs write, debugfs write, partition write, boot image write, or reboot.

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_first_open_runtime_prereq_v1058.py
python3 scripts/revalidation/native_wifi_first_open_runtime_prereq_v1058.py run
```
