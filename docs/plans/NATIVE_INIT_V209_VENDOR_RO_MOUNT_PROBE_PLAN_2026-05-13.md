# v209 Plan: Vendor Read-Only Mount Probe

## Summary

v209 follows the v208 `vendor-block-candidate-found` result. The goal is to
prove whether the physical vendor candidate `sda29` can expose Android vendor
firmware/init assets from native init when mounted through a controlled,
non-mutating, temporary read-only path.

This is still not Wi-Fi bring-up. It is a storage visibility proof needed before
CNSS/ICNSS userspace feasibility work.

Implementation target:

- `scripts/revalidation/native_vendor_ro_mount_probe.py`
- evidence output: `tmp/wifi/v209-vendor-ro-mount-probe`
- report: `docs/reports/NATIVE_INIT_V209_VENDOR_RO_MOUNT_PROBE_2026-05-13.md`

## Baseline

- v206 decision: `ready-for-native-preflight-plan`
- v207 decision: `missing-mounted-vendor`
- v208 decision: `vendor-block-candidate-found`
- v208 proved:
  - native basic control works
  - `/proc/partitions` exposes `sda29`, `sda30`, and `sda32`
  - `/sys/class/block/sda29/dev` exposes `259:22`
  - `/sys/class/block/sda29/size` exposes `2764800`
  - `/dev/block/sda29` is absent
  - by-name paths are absent
  - `dm-*`/`super` evidence is absent
  - mounted vendor firmware/init paths are absent
  - firmware loader path is `/vendor/firmware_mnt/image`

## Reference Model

- Android dynamic partitions can expose `vendor` as a logical `dm-linear`
  device, but v208 did not find native `dm-*` or `super` evidence:
  <https://source.android.com/docs/core/ota/dynamic_partitions/implement>
- Linux `sysfs` exposes block devices and `/sys/dev/block/<major>:<minor>` style
  relationships; v208 already found `sda29` through `/sys/class/block`:
  <https://www.kernel.org/doc/html/next/filesystems/sysfs.html>
- `mknod` creates block device special files from major/minor numbers, which is
  required here because `/dev/block/sda29` is absent:
  <https://man7.org/linux/man-pages/man1/mknod.1.html>
- `mount(2)` `MS_RDONLY` creates a read-only mount, but that alone is not enough
  for ext4 journal safety:
  <https://man7.org/linux/man-pages/man2/mount.2.html>
- ext4 can replay the journal even when mounted read-only; `ro,noload` prevents
  that write path and is therefore mandatory for this probe:
  <https://www.kernel.org/doc/html/v4.19/filesystems/ext4/ext4.html>

## Critical Safety Rule

Do not use plain `mountfs <src> <dst> ext4 ro` for v209.

Reason: current native `mountfs` only passes `MS_RDONLY`. For ext4, read-only
mounts can still replay the journal and write to the partition. v209 must either
mount with `ro,noload` through a tool that supports mount options, or refuse to
mount and return `unsafe-ro-noload-unavailable`.

## Scope

Add `scripts/revalidation/native_vendor_ro_mount_probe.py`.

The script should:

1. Load v208 manifest and require decision `vendor-block-candidate-found` unless
   `--allow-non-v208-decision` is explicitly set.
2. Confirm native control with `version`, `status`, and `bootstatus`.
3. Confirm `sda29` block metadata:
   - `cat /sys/class/block/sda29/dev`
   - `cat /sys/class/block/sda29/size`
   - `cat /sys/class/block/sda29/ro`
   - optional `/sys/dev/block/259:22` visibility
4. Confirm `ext4` availability from `/proc/filesystems`.
5. Create a run-specific temporary base path, for example:
   - `/tmp/a90-v209-<runid>/sda29`
   - `/tmp/a90-v209-<runid>/vendor`
6. Create only the temporary block node:
   - `mkdir /tmp/a90-v209-<runid>`
   - `mkdir /tmp/a90-v209-<runid>/vendor`
   - `mknodb /tmp/a90-v209-<runid>/sda29 259 22`
7. Mount only through a command that supports ext4 options:
   - preferred: `run /cache/bin/toybox mount -t ext4 -o ro,noload <node> <mountpoint>`
8. Capture mounted vendor asset paths read-only.
9. Always attempt rollback:
   - `umount <mountpoint>`
   - capture post-mount `/proc/mounts`
10. Mark the run FAIL if the mount remains active after cleanup.

## Asset Checks

After mount, capture read-only listings/stats under the temporary mountpoint:

- `<mnt>/etc/init`
- `<mnt>/etc/init/hw`
- `<mnt>/firmware`
- `<mnt>/firmware_mnt`
- `<mnt>/firmware_mnt/image`
- `<mnt>/etc/wifi`
- `<mnt>/lib/modules`
- known Wi-Fi/CNSS firmware candidates from v206:
  - `bdwlan.bin`
  - `regdb.bin`
  - `wlanmdsp.mbn`
  - `cnss`/`icnss` path fragments

The script should compare discovered files with v206 Android path evidence and
record which Android-known vendor paths are now native-visible.

## Guardrails

The script must not:

- run plain `mountfs ... ro` for ext4
- run mount without `ro,noload`
- mount read-write
- remount an existing system/vendor mount
- mount over `/vendor`, `/mnt/system`, `/dev/block`, or any persistent path
- create `/dev/block/sda29` directly
- write `firmware_class.path`
- enable Wi-Fi
- write rfkill state
- bring up a WLAN interface
- scan/connect
- load/unload modules
- start `cnss-daemon`, `wificond`, Wi-Fi HAL, supplicant, or hostapd
- touch `efs`, `sec_efs`, modem, persist, key, vbmeta, bootloader, boot,
  recovery, or userdata partitions
- run `dd`, `mkfs`, `sgdisk`, `parted`, `blockdev --set*`, `fsck`, `e2fsck`, or
  destructive storage commands

## Command Guard

`native_vendor_ro_mount_probe.py` should include a static command guard.

Allowed mutation-like commands are limited to the temporary probe path:

- `mkdir /tmp/a90-v209-*/...`
- `mknodb /tmp/a90-v209-*/sda29 259 22`
- `run /cache/bin/toybox mount -t ext4 -o ro,noload /tmp/a90-v209-*/sda29 /tmp/a90-v209-*/vendor`
- `umount /tmp/a90-v209-*/vendor`

The guard must reject:

- any `mount` command missing `ro,noload`
- any target outside `/tmp/a90-v209-*`
- any source outside `/tmp/a90-v209-*`
- any direct `/dev/block/sda29` creation
- any Wi-Fi activation command pattern already blocked by v207/v208

## Decision Model

- `vendor-assets-visible`
  - safe `ro,noload` mount succeeds and expected vendor firmware/init assets are
    visible.
- `vendor-mounted-no-wifi-assets`
  - safe mount succeeds, but expected Wi-Fi/CNSS vendor assets are missing or too
    incomplete for the next step.
- `vendor-mount-failed`
  - temporary node exists, but safe `ro,noload` mount fails.
- `candidate-node-missing`
  - `sda29` major/minor cannot be confirmed.
- `unsafe-ro-noload-unavailable`
  - no available command path can guarantee `ro,noload` mount semantics.
- `cleanup-failed`
  - mount succeeded or partially succeeded but post-run cleanup cannot prove the
    temporary mount is gone.
- `manual-review-required`
  - bridge/control/evidence collection failed or evidence is inconsistent.

## Validation Plan

Static validation:

```bash
python3 -m py_compile \
  scripts/revalidation/native_vendor_ro_mount_probe.py \
  scripts/revalidation/native_vendor_mount_probe.py \
  scripts/revalidation/a90harness/evidence.py

python3 - <<'PY'
import sys
sys.path.insert(0, 'scripts/revalidation')
import native_vendor_ro_mount_probe
native_vendor_ro_mount_probe.validate_probe_commands()
print('v209 command guard PASS')
PY

git diff --check
```

Native device validation:

```bash
python3 scripts/revalidation/a90ctl.py hide || true

python3 scripts/revalidation/native_vendor_ro_mount_probe.py \
  --native-bridge \
  --v208-manifest tmp/wifi/v208-vendor-firmware-mount/manifest.json \
  --v206-manifest tmp/wifi/v206-android-icnss-cnss-map/manifest.json \
  --out-dir tmp/wifi/v209-vendor-ro-mount-probe
```

Post-run manual sanity checks if needed:

```bash
python3 scripts/revalidation/a90ctl.py mounts
python3 scripts/revalidation/a90ctl.py 'cat /proc/mounts'
python3 scripts/revalidation/a90ctl.py 'ls /tmp'
```

Expected output:

- private/no-follow evidence bundle
- `manifest.json`
- `summary.md`
- pre/post mount snapshots
- cleanup status
- one of the defined decisions
- no active Wi-Fi commands

## Acceptance

- `sda29` major/minor is confirmed from sysfs.
- Temporary block node creation is isolated under `/tmp/a90-v209-*`.
- The probe either uses `ro,noload` or refuses to mount.
- Any successful mount is unmounted before exit.
- Pre/post `/proc/mounts` proves no leftover temporary vendor mount.
- Vendor firmware/init visibility is classified against v206 Android evidence.
- Active Wi-Fi bring-up remains blocked.

## Next

If v209 returns `vendor-assets-visible`, v210 should classify vendor Wi-Fi/CNSS
assets and map the minimum native dependency set for ICNSS/CNSS userspace
feasibility.

If v209 returns `vendor-mounted-no-wifi-assets`, v210 should inspect whether the
firmware assets are under another physical candidate such as `sda30`, `sda32`,
`firmware`, or a vendor-specific firmware partition.

If v209 returns `unsafe-ro-noload-unavailable`, the next step is not to force a
mount. Either add a narrow native helper that performs `mount(2)` with
`MS_RDONLY` plus ext4 `noload` data, or boot Android/TWRP and extract the needed
vendor asset map without native mounting.
