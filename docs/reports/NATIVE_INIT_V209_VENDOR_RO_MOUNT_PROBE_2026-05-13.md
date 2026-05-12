# v209 Vendor Read-Only Mount Probe

## Summary

v209 adds and validates a native-side vendor partition mount probe. It creates a
temporary block node for the v208 `sda29` vendor candidate, mounts it only under
an isolated `/tmp/a90-v209-*` mountpoint, uses ext4 `ro,noload`, captures vendor
asset visibility, and unmounts before exit.

Result: PASS.

Final decision: `vendor-assets-visible`.

Reason: `sda29` can be mounted safely with `ro,noload` from native init and it
exposes vendor firmware/init assets.

Active Wi-Fi bring-up remains blocked.

## Changes

- Added `scripts/revalidation/native_vendor_ro_mount_probe.py`.
- Added v209 plan:
  `docs/plans/NATIVE_INIT_V209_VENDOR_RO_MOUNT_PROBE_PLAN_2026-05-13.md`.
- Updated task queue and next-work notes.

## Scope

The collector performs a controlled native probe:

- confirms v208 decision `vendor-block-candidate-found`
- confirms `sda29` major/minor from `/sys/class/block/sda29/dev`
- confirms ext4 availability from `/proc/filesystems`
- creates temporary paths under `/tmp/a90-v209-*`
- creates only a temporary block node for `sda29`
- mounts only with `run /cache/bin/toybox mount -t ext4 -o ro,noload ...`
- captures vendor init/firmware paths
- unmounts and verifies no leftover mount remains

## Guardrails

- No plain `mountfs ... ext4 ro`.
- No mount without `ro,noload`.
- No read-write mount.
- No persistent `/dev/block/sda29` creation.
- No mount over `/vendor`, `/mnt/system`, `/dev/block`, or other persistent paths.
- No Wi-Fi enablement.
- No rfkill write.
- No WLAN link-up.
- No scan/connect.
- No module load/unload.
- No firmware path write.
- No `cnss-daemon`, `wificond`, Wi-Fi HAL, supplicant, or hostapd start.
- No destructive storage commands.

## Static Validation

```bash
python3 -m py_compile \
  scripts/revalidation/native_vendor_ro_mount_probe.py \
  scripts/revalidation/native_vendor_mount_probe.py \
  scripts/revalidation/a90harness/evidence.py
```

Result: PASS.

```bash
python3 - <<'PY'
import sys
sys.path.insert(0, 'scripts/revalidation')
import native_vendor_ro_mount_probe
native_vendor_ro_mount_probe.validate_probe_commands()
print('v209 command guard PASS')
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

python3 scripts/revalidation/native_vendor_ro_mount_probe.py \
  --native-bridge \
  --v208-manifest tmp/wifi/v208-vendor-firmware-mount/manifest.json \
  --v206-manifest tmp/wifi/v206-android-icnss-cnss-map/manifest.json \
  --out-dir tmp/wifi/v209-vendor-ro-mount-probe
```

Result: PASS.

Decision:

```text
vendor-assets-visible
```

Evidence:

- `tmp/wifi/v209-vendor-ro-mount-probe/manifest.json`
- `tmp/wifi/v209-vendor-ro-mount-probe/summary.md`
- `tmp/wifi/v209-vendor-ro-mount-probe/native/commands/`

Hashes:

- `tmp/wifi/v209-vendor-ro-mount-probe/manifest.json`:
  `b5a4fc182c84c97d9ae5533f4f39e57ce55765461e919bcf5f9fd67a34ed4b1c`
- `tmp/wifi/v209-vendor-ro-mount-probe/summary.md`:
  `f7f01980ce2a580839bb7996ae985659f7d33a2114e044d5b982fe1e1cb66f42`

## Current Result

- `decision`: `vendor-assets-visible`
- `major_minor`: `259:22`
- `expected_major_minor`: `true`
- `ext4_available`: `true`
- `mount_attempted`: `true`
- `mount_ok`: `true`
- `mounted_after_mount`: `true`
- `cleanup_rc`: `0`
- `leftover_mount`: `false`
- `visible_asset_count`: `16`
- `firmware_asset_count`: `12`
- `v206_decision`: `ready-for-native-preflight-plan`
- `v208_decision`: `vendor-block-candidate-found`

Important evidence:

```text
/tmp/a90-v209-20260512T205836Z/sda29 /tmp/a90-v209-20260512T205836Z/vendor ext4 ro,relatime,norecovery,i_version 0 0
post-mount sanity PASS: no v209 leftover mount
```

Visible vendor paths:

```text
etc/init
etc/init/hw
etc/init/android.hardware.wifi.supplicant-service.rc
etc/init/android.hardware.wifi@1.0-service.rc
etc/init/hostapd.android.rc
etc/init/hw/init.qcom.rc
etc/wifi
firmware
firmware/wlan
firmware/wlan/qca_cld
firmware/wlan/qca_cld/WCNSS_qcom_cfg.ini
firmware/wlan/qca_cld/bdwlan.bin
firmware/wlan/qca_cld/regdb.bin
firmware/wlanmdsp.mbn
firmware_mnt
lib/modules
```

## Interpretation

v208 proved that native can see the physical vendor candidate but lacks a default
vendor mount. v209 proves that the candidate is usable: `sda29` mounted with
`ro,noload` exposes the vendor init and firmware assets needed for the next
Wi-Fi/CNSS dependency analysis step.

The mount output shows `norecovery`, which is the kernel-visible form of the
`noload` ext4 behavior. Cleanup succeeded and a post-run `/proc/mounts` check
showed no leftover v209 mount.

One detail remains important: `/vendor/firmware_mnt/image` is still not proven as
a populated path under this mount. The visible Wi-Fi firmware assets are under
`vendor/firmware/wlan/...`, including `bdwlan.bin`, `regdb.bin`, and
`wlanmdsp.mbn`. v210 should classify the vendor asset map and decide how native
firmware lookup should use these paths without mutating `firmware_class.path` yet.

## Acceptance

- `sda29` major/minor confirmed from sysfs.
- Temporary block node creation isolated under `/tmp/a90-v209-*`.
- Probe used `ro,noload`; plain `mountfs ... ro` was not used.
- Successful mount was unmounted before exit.
- Pre/post mount snapshots prove no leftover temporary vendor mount.
- Vendor firmware/init visibility classified against v206 Android evidence.
- Active Wi-Fi bring-up remains blocked.

## Next

Recommended v210 scope: vendor Wi-Fi/CNSS asset classifier.

v210 should take the v209 mounted-vendor evidence and produce a minimal native
asset/dependency map: firmware files, init rc files, vendor binaries, libraries,
firmware search path implications, and whether a later read-only CNSS/ICNSS
userspace feasibility step has enough prerequisites to proceed.
