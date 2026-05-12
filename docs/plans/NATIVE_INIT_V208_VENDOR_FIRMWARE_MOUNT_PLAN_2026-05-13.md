# v208 Plan: Native Vendor/Firmware Mount Visibility

## Summary

v208 follows the v207 `missing-mounted-vendor` result. The goal is to identify,
from native init, which block device or existing mount path can expose Android
vendor firmware/init assets needed for later Wi-Fi/CNSS feasibility work.

This is a read-only visibility step, not Wi-Fi bring-up and not a boot image
change.

Implementation target:

- `scripts/revalidation/native_vendor_mount_probe.py`
- evidence output: `tmp/wifi/v208-vendor-firmware-mount`
- report: `docs/reports/NATIVE_INIT_V208_VENDOR_FIRMWARE_MOUNT_2026-05-13.md`

## Baseline

- v207 decision: `missing-mounted-vendor`
- v207 proved:
  - native basic control works
  - `mountsystem ro` works
  - ICNSS sysfs is visible
  - mounted system init path is visible
  - mounted vendor firmware/init paths are missing
  - WLAN netdev/wiphy/rfkill are absent
- Older storage map identifies `vendor -> /dev/block/sda29`,
  `product -> /dev/block/sda30`, and `omr -> /dev/block/sda32` as read-only
  reference candidates.

## Reference Model

- Android dynamic partitions use `super` plus logical sub-partitions, so vendor
  may be exposed through a physical partition or a device-mapper logical device:
  <https://source.android.com/docs/core/ota/dynamic_partitions>
- AOSP dynamic partition implementation uses `dm-linear`; first-stage init reads
  metadata and creates virtual block devices for logical partitions:
  <https://source.android.com/docs/core/ota/dynamic_partitions/implement>
- Android init `mount_all` uses fs_mgr-format fstab files and can process early
  or late mount entries; native init does not run that Android fs_mgr flow:
  <https://android.googlesource.com/platform/system/core/+/master/init/README.md>
- Linux device-mapper is the kernel layer behind logical block device mapping:
  <https://docs.kernel.org/admin-guide/device-mapper/index.html>
- Linux firmware loader can use `/sys/module/firmware_class/parameters/path`,
  but v208 reads this only and must not write it:
  <https://docs.kernel.org/driver-api/firmware/fw_search_path.html>

## Scope

Add `scripts/revalidation/native_vendor_mount_probe.py`.

The default collector is read-only and captures:

- native version/status/bootstatus
- current mount state from `/proc/mounts`
- partition list from `/proc/partitions`
- `/dev/block` node visibility
- `/dev/block/by-name`, `/dev/block/bootdevice/by-name`, and
  `/dev/block/platform/*/by-name` visibility if present
- `/sys/class/block` inventory, including `dev`, `size`, `ro`, `dm/name`,
  `slaves`, and `holders` where available
- known physical candidates:
  - `sda28` system
  - `sda29` vendor
  - `sda30` product
  - `sda32` omr
- possible dynamic/logical candidates:
  - `dm-*`
  - `super`
  - `metadata`
- current filesystem visibility:
  - `/mnt/system/vendor`
  - `/mnt/system/vendor/etc/init`
  - `/mnt/system/vendor/firmware`
  - `/mnt/system/vendor/firmware_mnt`
  - `/mnt/system/vendor/etc/wifi`
  - `/vendor`
  - `/vendor/firmware`
  - `/vendor/firmware_mnt`
  - `/vendor/firmware_mnt/image`
- v206 Android firmware/init path comparison
- v207 missing-path comparison

## Optional Mount Probe

Default v208 must not mount or unmount anything. If later needed, a separate
explicit flag may be added:

```text
--allow-ro-mount-probe
```

That option is not required for v208 PASS. If implemented later, it must:

- only use `MS_RDONLY`
- use an isolated mountpoint under `/tmp` or `/mnt`
- record pre/post `/proc/mounts`
- unmount before exit
- never mount read-write
- never touch `efs`, `sec_efs`, modem, persist, key, vbmeta, bootloader, boot,
  recovery, or userdata partitions

## Guardrails

The collector must not:

- enable Wi-Fi
- write rfkill state
- bring up any WLAN interface
- scan/connect
- load/unload modules
- write `firmware_class.path`
- mutate firmware files
- start `cnss-daemon`, `wificond`, Wi-Fi HAL, supplicant, or hostapd
- write to vendor/product/system partitions
- run `dd`, `mkfs`, `sgdisk`, `parted`, `blockdev --set*`, `dmsetup create`,
  or any destructive storage command
- mount or unmount by default

## Decision Model

- `vendor-visible-existing-mount`
  - vendor firmware/init assets are already visible from an existing native
    mount path.
- `vendor-block-candidate-found`
  - a plausible vendor block candidate such as `sda29`, by-name `vendor`, or
    a vendor-named dm node exists, but no default mount exposes the assets.
- `dynamic-partition-mapping-required`
  - evidence points to `super` or `dm-*` logical partition mapping, but no
    vendor-specific logical device is currently visible.
- `vendor-path-still-missing`
  - no plausible vendor block or mount candidate was found.
- `manual-review-required`
  - bridge/control or evidence collection failed.

## Validation Plan

Static validation:

```bash
python3 -m py_compile \
  scripts/revalidation/native_vendor_mount_probe.py \
  scripts/revalidation/native_wifi_preflight.py \
  scripts/revalidation/a90harness/evidence.py

python3 - <<'PY'
import sys
sys.path.insert(0, 'scripts/revalidation')
import native_vendor_mount_probe
native_vendor_mount_probe.validate_no_mutating_commands()
print('v208 command guard PASS')
PY

git diff --check
```

Native device validation:

```bash
python3 scripts/revalidation/a90ctl.py hide || true

python3 scripts/revalidation/native_vendor_mount_probe.py \
  --native-bridge \
  --v207-manifest tmp/wifi/v207-native-wifi-preflight/manifest.json \
  --v206-manifest tmp/wifi/v206-android-icnss-cnss-map/manifest.json \
  --out-dir tmp/wifi/v208-vendor-firmware-mount
```

Expected output:

- private/no-follow evidence bundle
- `manifest.json`
- `summary.md`
- one of the defined decisions
- no mutating command in command guard

## Acceptance

- Native block/mount/device-mapper inventory is captured.
- v206 Android vendor firmware/init paths are compared against native paths.
- v207 missing vendor paths are explained by block/mount visibility evidence.
- A clear next decision is produced without Wi-Fi enablement and without
  write/mount mutation by default.

## Next

If v208 returns `vendor-block-candidate-found`, v209 should design a narrow,
explicit read-only mount probe for the candidate vendor partition, likely
`sda29`, and verify firmware/init asset visibility.

If v208 returns `dynamic-partition-mapping-required`, v209 should map Android
dynamic partition metadata and device-mapper state before attempting any mount.

If v208 returns `vendor-visible-existing-mount`, v209 can move to CNSS/ICNSS
userspace daemon dependency feasibility, still without scan/connect.
