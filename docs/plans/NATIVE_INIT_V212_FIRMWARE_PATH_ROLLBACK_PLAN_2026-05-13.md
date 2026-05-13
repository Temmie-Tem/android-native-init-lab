# v212 Plan: Guarded Firmware Path Apply / Rollback Probe

## Summary

v212 follows the v211 `sysfs-path-update-needed` result. The goal is to prove
that native init can temporarily point the Linux firmware loader at the mounted
vendor firmware root, verify readback and request-name resolution, and restore
the original path without leaving mounts behind.

This is still not Wi-Fi bring-up.

Implementation target:

- collector: `scripts/revalidation/native_firmware_path_apply_probe.py`
- evidence output: `tmp/wifi/v212-firmware-path-rollback`
- report: `docs/reports/NATIVE_INIT_V212_FIRMWARE_PATH_ROLLBACK_2026-05-13.md`
- device boot image: unchanged; current target runtime remains
  `A90 Linux init 0.9.59 (v159)`

## Baseline

- v209 decision: `vendor-assets-visible`
- v210 decision: `firmware-path-policy-needed`
- v211 decision: `sysfs-path-update-needed`
- v211 proved:
  - current `firmware_class.path=/vendor/firmware_mnt/image`
  - current path does not resolve the likely Wi-Fi/CNSS request names
  - isolated vendor firmware root model resolves likely request names:
    - `wlan/qca_cld/WCNSS_qcom_cfg.ini`
    - `wlan/qca_cld/bdwlan.bin`
    - `wlan/qca_cld/regdb.bin`
    - `wlanmdsp.mbn`
  - synthetic `/vendor/firmware_mnt/image` bind model also resolves them, but
    has higher mount layout and cleanup risk
  - uncertain bare request names remain unresolved:
    - `WCNSS_qcom_cfg.ini`
    - `bdwlan.bin`
    - `regdb.bin`

## Reference Notes

- Linux firmware search uses optional `firmware_class.path` first, followed by
  default `/lib/firmware...` paths. The runtime sysfs value is writable through
  `/sys/module/firmware_class/parameters/path`, but newline characters become
  part of the configured value. Therefore v212 must use an exact no-newline
  write, not a plain `echo`:
  <https://www.kernel.org/doc/html/v6.15/driver-api/firmware/fw_search_path.html>
- `request_firmware()` accepts a firmware `name` that may include subdirectories,
  and forbids `..` path components. This supports the v211 model that
  `wlan/qca_cld/*` requests are legitimate request names:
  <https://www.kernel.org/doc/html/next/driver-api/firmware/request_firmware.html>
- Bind mount fallback is deliberately not the first implementation path because
  mount propagation and cleanup semantics can create additional risk:
  <https://docs.kernel.org/filesystems/sharedsubtree.html>
- Android Wi-Fi HAL and service startup remain out of scope. HAL/service
  behavior is a later stage after firmware path rollback is proven:
  <https://source.android.com/docs/core/connect/wifi-hal>

## Core Question

v212 must answer:

> Can native init safely apply `firmware_class.path=/mnt/vendor/firmware`, prove
> the likely firmware requests resolve, and roll back to the original value
> without starting Wi-Fi or leaving state behind?

## Scope

Allowed:

- create `/mnt/vendor` if absent
- create a temporary block node under `/tmp/a90-v212-*`
- mount `sda29` read-only with `ext4 ro,noload`
- read required firmware paths
- save current `firmware_class.path`
- write `/mnt/vendor/firmware` to `firmware_class.path` with no newline
- read back and verify the sysfs value
- restore the original `firmware_class.path` exactly
- unmount `/mnt/vendor`
- record evidence in a private host bundle

Forbidden:

- Wi-Fi enablement
- rfkill writes
- `ip link set wlan0 up`
- scan/connect
- module load/unload
- `cnss-daemon`, `cnss_diag`, Wi-Fi HAL, `wificond`, supplicant, or hostapd
  start
- firmware file copy
- `/vendor` bind mount
- `/lib/firmware` mutation
- persistent flag creation
- partition writes or formatting

## Proposed Collector

Add `scripts/revalidation/native_firmware_path_apply_probe.py`.

Inputs:

- `--v209-manifest tmp/wifi/v209-vendor-ro-mount-probe/manifest.json`
- `--v210-manifest tmp/wifi/v210-vendor-asset-classifier/manifest.json`
- `--v211-manifest tmp/wifi/v211-firmware-path-policy/manifest.json`
- `--out-dir tmp/wifi/v212-firmware-path-rollback`
- `--apply` required for the sysfs write phase

Default mode should be dry-run/read-only and refuse to write sysfs unless
`--apply` is explicitly present.

Steps:

1. Require v209/v210/v211 expected decisions unless override flags are present.
2. Capture `version`, `status`, `bootstatus`.
3. Capture current `firmware_class.path`.
4. Confirm `sda29` major/minor `259:22`.
5. Confirm `ext4` support.
6. Create `/mnt/vendor`.
7. Create temporary `/tmp/a90-v212-*/sda29` block node.
8. Mount vendor read-only:

   ```text
   run /cache/bin/toybox mount -t ext4 -o ro,noload /tmp/a90-v212-*/sda29 /mnt/vendor
   ```

9. Confirm required firmware exists under `/mnt/vendor/firmware`.
10. If `--apply` is absent, stop after modeling and cleanup with decision
    `apply-required`.
11. If `--apply` is present, write `/mnt/vendor/firmware` to
    `/sys/module/firmware_class/parameters/path` with an exact no-newline write.
12. Read back `firmware_class.path` and require exact match.
13. Re-check likely request paths:

    ```text
    /mnt/vendor/firmware/wlan/qca_cld/WCNSS_qcom_cfg.ini
    /mnt/vendor/firmware/wlan/qca_cld/bdwlan.bin
    /mnt/vendor/firmware/wlan/qca_cld/regdb.bin
    /mnt/vendor/firmware/wlanmdsp.mbn
    ```

14. Restore original `firmware_class.path` exactly.
15. Read back and require original value.
16. Unmount `/mnt/vendor`.
17. Confirm no `/mnt/vendor` or `/tmp/a90-v212-*` mount remains.

## Write Strategy

The write mechanism is the highest-risk part of v212.

Final sequence:

1. Use the static `/cache/bin/a90_fwpathctl` helper for the fixed sysfs target.
   The current `/cache/bin/toybox` has no `sh` applet, so shell redirection is
   not an acceptable write mechanism.
2. Never use plain `echo` or shell redirection.
3. Never put untrusted or variable shell fragments into the write command.
4. Only permit two exact target values:
   - candidate: `/mnt/vendor/firmware`
   - original value read from `/sys/module/firmware_class/parameters/path`

If `/cache/bin/a90_fwpathctl` is missing or cannot read the sysfs parameter,
v212 must stop with `write-helper-unavailable`.

## Command Guard

Allowed mutation-like commands are limited to:

- `mkdir /mnt/vendor`
- `mkdir /tmp/a90-v212-*`
- `mknodb /tmp/a90-v212-*/sda29 259 22`
- `run /cache/bin/toybox mount -t ext4 -o ro,noload /tmp/a90-v212-*/sda29 /mnt/vendor`
- `run /cache/bin/a90_fwpathctl read`
- `run /cache/bin/a90_fwpathctl write /mnt/vendor/firmware`, only with
  `--apply`
- `run /cache/bin/a90_fwpathctl write <original-firmware-class-path>`, only
  after a successful apply attempt or during cleanup
- `umount /mnt/vendor`

Forbidden command patterns:

- `svc wifi`
- `cmd wifi`
- `rfkill block` / `rfkill unblock`
- `ip link set ... up`
- `insmod`, `rmmod`, `modprobe`
- `cnss-daemon`, `cnss_diag`, `wificond`, `hostapd`, `wpa_supplicant`
- `mount --bind`, `mount -o bind`
- `dd`, `mkfs`, `sgdisk`, `parted`, `fsck`, `e2fsck`
- any write to firmware files or `/lib/firmware`

## Decision Model

- `path-rollback-pass`
  - candidate path applied
  - readback matched `/mnt/vendor/firmware`
  - likely request paths resolve
  - original path restored
  - cleanup passed
- `apply-required`
  - dry-run mode succeeded and no sysfs write was attempted
- `write-helper-unavailable`
  - safe no-newline write method could not be proven
- `path-readback-mismatch`
  - sysfs readback did not match candidate value
- `rollback-failed`
  - original `firmware_class.path` could not be restored
- `cleanup-failed`
  - `/mnt/vendor` mount or temporary mount remained
- `request-name-unknown`
  - path update worked, but modeled request names still do not resolve
- `manual-review-required`
  - preflight, mount, firmware visibility, or control evidence failed

## Test Plan

Static validation:

```text
python3 -m py_compile \
  scripts/revalidation/native_firmware_path_apply_probe.py \
  scripts/revalidation/native_firmware_path_policy_probe.py \
  scripts/revalidation/a90harness/evidence.py

python3 - <<'PY'
import sys
sys.path.insert(0, 'scripts/revalidation')
import native_firmware_path_apply_probe
native_firmware_path_apply_probe.validate_apply_commands()
print('v212 command guard PASS')
PY

git diff --check
```

Helper build:

```text
scripts/revalidation/build_fwpathctl_helper.sh
```

Dry-run live validation:

```text
python3 scripts/revalidation/native_firmware_path_apply_probe.py \
  --native-bridge \
  --v209-manifest tmp/wifi/v209-vendor-ro-mount-probe/manifest.json \
  --v210-manifest tmp/wifi/v210-vendor-asset-classifier/manifest.json \
  --v211-manifest tmp/wifi/v211-firmware-path-policy/manifest.json \
  --out-dir tmp/wifi/v212-firmware-path-rollback
```

Expected dry-run decision:

```text
apply-required
```

Apply/rollback live validation:

```text
python3 scripts/revalidation/native_firmware_path_apply_probe.py \
  --native-bridge \
  --apply \
  --v209-manifest tmp/wifi/v209-vendor-ro-mount-probe/manifest.json \
  --v210-manifest tmp/wifi/v210-vendor-asset-classifier/manifest.json \
  --v211-manifest tmp/wifi/v211-firmware-path-policy/manifest.json \
  --out-dir tmp/wifi/v212-firmware-path-rollback
```

Expected apply decision:

```text
path-rollback-pass
```

Post-run checks:

```text
python3 scripts/revalidation/a90ctl.py cat /sys/module/firmware_class/parameters/path
python3 scripts/revalidation/a90ctl.py cat /proc/mounts
```

Expected:

- `firmware_class.path` restored to `/vendor/firmware_mnt/image`
- no `/mnt/vendor` mount remains
- no `/tmp/a90-v212-*` mount remains

## Acceptance

- Dry-run mode never writes sysfs.
- Apply mode changes only `firmware_class.path`, and only with `--apply`.
- `firmware_class.path` is restored to its original value even on intermediate
  failure paths where rollback is possible.
- Evidence proves before/after readback.
- Evidence proves `/mnt/vendor/firmware` resolves the likely request names while
  the candidate path is active.
- No active Wi-Fi bring-up occurs.
- No daemon/HAL/supplicant/hostapd starts.
- No persistent mount, bind mount, or copied firmware remains.

## Next Step After PASS

If v212 passes, v213 should still not jump straight to Wi-Fi connection. The
next safe candidates are:

1. collect firmware request-name evidence around a controlled driver probe if
   possible without enabling WLAN link-up, or
2. decide whether `/cache/bin/a90_fwpathctl` should remain an external helper
   or move into PID1/ramdisk for future controlled Wi-Fi preflight, or
3. plan `cnss-daemon`/ICNSS service preflight with no supplicant, no scan, and
   strict rollback.
