# v208 Native Vendor/Firmware Mount Visibility

## Summary

v208 adds and validates a native-side read-only vendor/firmware mount visibility
collector. It does not modify the native boot image, does not enable Wi-Fi, and
does not mount or unmount anything by default.

Result: PASS.

Final decision: `vendor-block-candidate-found`.

Reason: native can see plausible physical vendor/product/OMR block candidates,
but the default native mount layout does not expose Android vendor firmware/init
assets.

Active Wi-Fi bring-up remains blocked.

## Changes

- Added `scripts/revalidation/native_vendor_mount_probe.py`.
- Added v208 plan:
  `docs/plans/NATIVE_INIT_V208_VENDOR_FIRMWARE_MOUNT_PLAN_2026-05-13.md`.
- Updated task queue and next-work notes.

## Scope

The collector captures read-only native evidence from:

- version/status/bootstatus
- current mount state from `mounts` and `/proc/mounts`
- partition inventory from `/proc/partitions`
- `/dev/block` and by-name path visibility
- `/sys/class/block` and `/sys/block` inventory
- known physical candidates: `sda28`, `sda29`, `sda30`, `sda32`
- possible dynamic/logical candidates: `dm-*`, `super`, `metadata`
- current vendor path visibility under `/mnt/system/vendor` and `/vendor`
- firmware loader search path
- v206/v207 manifest decisions

## Guardrails

- No Wi-Fi enablement.
- No rfkill write.
- No WLAN link-up.
- No scan/connect.
- No module load/unload.
- No firmware path write.
- No firmware mutation.
- No `cnss-daemon`, `wificond`, Wi-Fi HAL, supplicant, or hostapd start.
- No vendor/product/system writes.
- No mount/umount by default.
- No destructive storage commands.

## Static Validation

```bash
python3 -m py_compile \
  scripts/revalidation/native_vendor_mount_probe.py \
  scripts/revalidation/native_wifi_preflight.py \
  scripts/revalidation/a90harness/evidence.py
```

Result: PASS.

```bash
python3 - <<'PY'
import sys
sys.path.insert(0, 'scripts/revalidation')
import native_vendor_mount_probe
native_vendor_mount_probe.validate_no_mutating_commands()
print('v208 command guard PASS')
PY
```

Result: PASS.

```bash
git diff --check
```

Result: PASS.

## Device Validation

Bridge precheck:

```bash
python3 scripts/revalidation/a90ctl.py --json version
```

Result: PASS.

Runtime:

- `A90 Linux init 0.9.59 (v159)`

Collector run:

```bash
python3 scripts/revalidation/a90ctl.py hide || true

python3 scripts/revalidation/native_vendor_mount_probe.py \
  --native-bridge \
  --v207-manifest tmp/wifi/v207-native-wifi-preflight/manifest.json \
  --v206-manifest tmp/wifi/v206-android-icnss-cnss-map/manifest.json \
  --out-dir tmp/wifi/v208-vendor-firmware-mount
```

Result: PASS.

Decision:

```text
vendor-block-candidate-found
```

Evidence:

- `tmp/wifi/v208-vendor-firmware-mount/manifest.json`
- `tmp/wifi/v208-vendor-firmware-mount/summary.md`
- `tmp/wifi/v208-vendor-firmware-mount/native/commands/`

Hashes:

- `tmp/wifi/v208-vendor-firmware-mount/manifest.json`:
  `73938c3ec139dbee5fbd5c61c13335f5bf530ed40873b5ef249cff81e2048755`
- `tmp/wifi/v208-vendor-firmware-mount/summary.md`:
  `81d8af25a7e0a0620233fbe1e179dae87fcb96b61e345cae14d1f79d9d53ea10`

## Current Result

- `basic_control_ok`: `true`
- `existing_vendor_mount`: `false`
- `known_physical_vendor`: `true`
- `product_or_omr_candidates`: `true`
- `byname_vendor`: `false`
- `dm_vendor`: `false`
- `dm_or_super_present`: `false`
- `existing_android_firmware_path`: `false`
- `firmware_class_path`: `/vendor/firmware_mnt/image`
- `v206_decision`: `ready-for-native-preflight-plan`
- `v207_decision`: `missing-mounted-vendor`

Important evidence:

```text
259       22    1382400 sda29
259       26     204800 sda30
259       29      51200 sda32
/sys/class/block/sda29
/sys/class/block/sda30
/sys/class/block/sda32
/sys/class/block/sda29/dev -> 259:22
/sys/class/block/sda29/size -> 2764800
stat: /dev/block/sda29: No such file or directory
ls: /dev/block/by-name: No such file or directory
ls: /dev/block/bootdevice/by-name: No such file or directory
cat: /sys/class/block/dm-0/dm/name: No such file or directory
ls: /mnt/system/vendor/firmware: No such file or directory
ls: /mnt/system/vendor/firmware_mnt: No such file or directory
ls: /mnt/system/vendor/etc/wifi: No such file or directory
ls: /vendor/firmware_mnt/image: No such file or directory
/vendor/firmware_mnt/image
```

## Interpretation

v207 showed that native can see ICNSS but cannot see Android vendor firmware/init
paths through the existing mounted-system view. v208 narrows that gap: native can
see `sda29` in `/proc/partitions` and `/sys/class/block`, which matches the
older vendor partition candidate, but the matching `/dev/block/sda29` node and
by-name links are not currently present.

No `dm-*` names or `super` evidence appeared in the native read-only inventory,
so the next step should not start with dynamic-partition mapping. The next useful
step is a narrow read-only vendor partition mount probe that first creates or
locates the needed block device node safely, mounts only read-only at an isolated
mountpoint, checks firmware/init assets, then unmounts.

## Acceptance

- Native block/mount/device-mapper inventory captured.
- v206 Android vendor firmware/init paths compared against native visibility.
- v207 `missing-mounted-vendor` explained by block/mount evidence.
- Command guard blocks mount/write/destructive and active Wi-Fi patterns.
- Evidence output uses private/no-follow `EvidenceStore`.
- Live native run completed through the bridge.
- Decision produced without enabling Wi-Fi and without mount/write mutation.

## Next

Recommended v209 scope: explicit read-only vendor partition mount probe.

Start from `sda29` as the vendor candidate. The probe should create or resolve
only the required block node, mount it read-only under an isolated temporary
mountpoint, verify firmware/init path visibility, record pre/post mounts, and
unmount before exit. Active Wi-Fi bring-up remains blocked until vendor firmware
visibility and CNSS/ICNSS userspace prerequisites are proven.
