# v211 Plan: Firmware Path / Vendor Layout Policy

## Summary

v211 follows the v210 `firmware-path-policy-needed` result. The goal is to
design and validate a safe firmware path/layout policy before any Wi-Fi daemon,
HAL, supplicant, hostapd, rfkill, WLAN link-up, scan, or connect attempt.

This is still not Wi-Fi bring-up. v211 should not start `cnss-daemon`,
`cnss_diag`, Wi-Fi HAL, `wificond`, supplicant, or hostapd. It should only model
how native init could make Android vendor firmware paths discoverable by the
kernel and userspace later.

Implementation target:

- plan/report first; code only after the policy is accepted
- likely collector: `scripts/revalidation/native_firmware_path_policy_probe.py`
- evidence output: `tmp/wifi/v211-firmware-path-policy`
- report: `docs/reports/NATIVE_INIT_V211_FIRMWARE_PATH_POLICY_2026-05-13.md`

## Baseline

- v206 decision: `ready-for-native-preflight-plan`
- v207 decision: `missing-mounted-vendor`
- v208 decision: `vendor-block-candidate-found`
- v209 decision: `vendor-assets-visible`
- v210 decision: `firmware-path-policy-needed`
- v210 proved:
  - `sda29` major/minor is `259:22`
  - ext4 `ro,noload` mount works from native
  - cleanup succeeds and no leftover temporary vendor mount remains
  - required firmware files are visible:
    - `/vendor/firmware/wlan/qca_cld/WCNSS_qcom_cfg.ini`
    - `/vendor/firmware/wlan/qca_cld/bdwlan.bin`
    - `/vendor/firmware/wlan/qca_cld/regdb.bin`
    - `/vendor/firmware/wlanmdsp.mbn`
  - required init rc and service binaries are visible:
    - `cnss-daemon`
    - `cnss_diag`
    - `vendor.wifi_hal_ext`
    - `vendor.wifi_hal_legacy`
    - `wpa_supplicant`
    - `hostapd`
  - native current `firmware_class.path` is `/vendor/firmware_mnt/image`
  - required Wi-Fi firmware is not visible under that current loader path

## Reference Model

- Linux firmware lookup uses the optional `firmware_class.path` first, then
  standard `/lib/firmware...` paths. The runtime sysfs parameter exists, but a
  newline in the written value is significant, so any future write must be
  guarded and exact:
  <https://www.kernel.org/doc/html/v6.15/driver-api/firmware/fw_search_path.html>
- Android Wi-Fi is split across vendor HAL, supplicant HAL, and hostapd HAL
  surfaces. Android 13 and lower vendor partitions use HIDL for those surfaces,
  matching this A90 evidence:
  <https://source.android.com/docs/core/connect/wifi-hal>
- Android init service rc files define service executable, arguments, class,
  user, groups, capabilities, and flags. Native init cannot treat a vendor
  binary path alone as enough to safely launch the service:
  <https://android.googlesource.com/platform/system/core/+/master/init/README.md>
- Linux bind mounts and mount propagation matter if native init later creates a
  synthetic `/vendor` or firmware directory layout. Private/slave mount behavior
  must be understood before any bind layout is made persistent:
  <https://docs.kernel.org/filesystems/sharedsubtree.html>

## Core Question

v210 proved that vendor firmware exists, but current native firmware lookup does
not point to it. v211 must answer:

> What is the least risky native layout that lets the kernel find required
> Wi-Fi/CNSS firmware without enabling Wi-Fi yet?

## Policy Options

### Option A: Read-Only `/mnt/vendor` + `firmware_class.path=/mnt/vendor/firmware`

Mount `sda29` read-only at an isolated path such as `/mnt/vendor` or
`/tmp/a90-v211-*/vendor`, then later set `firmware_class.path` to that mounted
firmware root.

Pros:

- minimal directory layout
- no need to fake full Android `/vendor`
- likely maps requests like `wlan/qca_cld/bdwlan.bin` to the visible files
- easy rollback: restore old `firmware_class.path`, unmount vendor

Cons:

- writes a global kernel module parameter when implemented
- does not solve absolute userspace paths like `/vendor/bin/...`
- must prove requested firmware names are relative to that root

v211 action: model only. Do not write `firmware_class.path` yet.

### Option B: Synthetic Rootfs `/vendor/firmware_mnt/image` Bind Layout

Mount vendor read-only at an isolated path, then create a rootfs-owned synthetic
`/vendor/firmware_mnt/image` mountpoint and bind-mount the vendor firmware
directory there.

Pros:

- preserves current `firmware_class.path=/vendor/firmware_mnt/image`
- avoids changing firmware loader sysfs state
- can be made opt-in and temporary

Cons:

- requires creating `/vendor/...` paths on native rootfs
- risks conflict if `/vendor` later becomes a real mount
- needs careful bind mount cleanup and mount propagation control
- still does not expose every Android userspace absolute path unless additional
  bind mounts are added

v211 action: model only. If implemented later, require isolated temporary proof
and cleanup checks before using `/vendor`.

### Option C: Full Read-Only Vendor Layout

Mount or bind enough of vendor to make Android absolute paths visible:

- `/vendor/bin`
- `/vendor/etc`
- `/vendor/lib`
- `/vendor/lib64`
- `/vendor/firmware`
- `/vendor/firmware_mnt/image`

Pros:

- closest to Android userspace assumptions
- prepares later service feasibility work

Cons:

- much larger surface
- higher collision risk with native rootfs
- more cleanup complexity
- not necessary for a firmware-only next step

v211 action: reject as immediate next step; keep for later service feasibility.

### Option D: Copy Firmware Into `/lib/firmware`

Copy required firmware to a standard Linux firmware path.

Pros:

- uses default kernel search path
- avoids `firmware_class.path` writes

Cons:

- copies vendor firmware into native rootfs or SD/cache
- risks stale firmware and provenance confusion
- mutates storage and creates lifecycle questions

v211 action: reject for now.

## Recommended Direction

Use a two-stage policy:

1. v211: read-only policy probe and simulator
   - no sysfs writes
   - no bind mounts outside temporary path
   - no daemon starts
   - model whether required firmware names resolve under:
     - current `/vendor/firmware_mnt/image`
     - candidate `/mnt/vendor/firmware`
     - candidate synthetic `/vendor/firmware_mnt/image -> <vendor>/firmware`
2. v212: opt-in implementation of the chosen layout
   - start with Option A if request-name simulation is sufficient
   - fall back to Option B only if current path preservation is required
   - still no Wi-Fi daemon bring-up until path policy passes rollback tests

## Proposed Collector

Add `scripts/revalidation/native_firmware_path_policy_probe.py`.

Inputs:

- `--v210-manifest tmp/wifi/v210-vendor-asset-classifier/manifest.json`
- `--v209-manifest tmp/wifi/v209-vendor-ro-mount-probe/manifest.json`
- `--out-dir tmp/wifi/v211-firmware-path-policy`

Steps:

1. Require v210 decision `firmware-path-policy-needed` unless explicitly
   overridden.
2. Confirm native control with `version`, `status`, `bootstatus`.
3. Capture read-only state:
   - `/sys/module/firmware_class/parameters/path`
   - `/proc/mounts`
   - `/proc/filesystems`
   - `/sys/class/block/sda29/dev`
4. Create temporary paths under `/tmp/a90-v211-*`.
5. Create only a temporary `sda29` block node under that path.
6. Mount vendor with `run /cache/bin/toybox mount -t ext4 -o ro,noload`.
7. Read-only capture required firmware paths and directories.
8. Simulate search resolution for request names:
   - `WCNSS_qcom_cfg.ini`
   - `bdwlan.bin`
   - `regdb.bin`
   - `wlanmdsp.mbn`
   - `wlan/qca_cld/WCNSS_qcom_cfg.ini`
   - `wlan/qca_cld/bdwlan.bin`
   - `wlan/qca_cld/regdb.bin`
9. Score policy candidates:
   - current path
   - candidate isolated vendor firmware root
   - candidate synthetic firmware_mnt image layout
   - rejected copy-to-lib-firmware path
10. Unmount and verify no leftover mount remains.

## Command Guard

Allowed mutation-like commands are limited to:

- `mkdir /tmp/a90-v211-*/...`
- `mknodb /tmp/a90-v211-*/sda29 259 22`
- `run /cache/bin/toybox mount -t ext4 -o ro,noload /tmp/a90-v211-*/sda29 /tmp/a90-v211-*/vendor`
- `umount /tmp/a90-v211-*/vendor`

Forbidden:

- writing `/sys/module/firmware_class/parameters/path`
- bind mounting to `/vendor`, `/lib/firmware`, `/mnt/system`, `/cache`, or any
  persistent path
- creating `/dev/block/sda29`
- Wi-Fi enablement
- rfkill writes
- WLAN link-up
- scan/connect
- module load/unload
- daemon/HAL/supplicant/hostapd start
- copying firmware files
- destructive storage commands

## Decision Model

- `path-policy-ready`
  - candidate policy resolves all required firmware request names and cleanup is
    clean; next step can implement it behind an opt-in rollback guard.
- `request-name-unknown`
  - firmware files exist, but the likely kernel request names are not proven
    enough to choose between Option A and B.
- `bind-layout-needed`
  - current `firmware_class.path` should be preserved and a future synthetic
    read-only bind layout is required.
- `sysfs-path-update-needed`
  - isolated vendor firmware root is sufficient, but implementation requires a
    guarded `firmware_class.path` write with rollback.
- `vendor-layout-risk-too-high`
  - full `/vendor` layout would be needed before safe firmware feasibility.
- `cleanup-failed`
  - temporary mount remains or cleanup cannot be proven.
- `manual-review-required`
  - bridge/control/evidence is inconsistent.

## Validation Plan

Static validation:

```bash
python3 -m py_compile \
  scripts/revalidation/native_firmware_path_policy_probe.py \
  scripts/revalidation/native_vendor_asset_classifier.py \
  scripts/revalidation/a90harness/evidence.py

python3 - <<'PY'
import sys
sys.path.insert(0, 'scripts/revalidation')
import native_firmware_path_policy_probe
native_firmware_path_policy_probe.validate_policy_commands()
print('v211 command guard PASS')
PY

git diff --check
```

Native device validation:

```bash
python3 scripts/revalidation/a90ctl.py hide || true

python3 scripts/revalidation/native_firmware_path_policy_probe.py \
  --native-bridge \
  --v210-manifest tmp/wifi/v210-vendor-asset-classifier/manifest.json \
  --v209-manifest tmp/wifi/v209-vendor-ro-mount-probe/manifest.json \
  --out-dir tmp/wifi/v211-firmware-path-policy
```

Post-run sanity:

```bash
python3 scripts/revalidation/a90ctl.py cat /proc/mounts
python3 scripts/revalidation/a90ctl.py cat /sys/module/firmware_class/parameters/path
```

Expected output:

- private/no-follow evidence bundle
- `manifest.json`
- `summary.md`
- candidate policy matrix
- firmware request-name resolution matrix
- cleanup status
- no active Wi-Fi command evidence
- no `firmware_class.path` change

## Acceptance

- v211 performs no Wi-Fi bring-up.
- v211 performs no `firmware_class.path` write.
- v211 performs no bind mount outside `/tmp/a90-v211-*`.
- v211 proves whether all required firmware names resolve under at least one
  candidate policy.
- v211 identifies the safest v212 implementation path.
- Temporary vendor mount is cleaned up.

## Next

If v211 returns `path-policy-ready` or `sysfs-path-update-needed`, v212 should
implement an opt-in firmware path policy with strict rollback:

- save old `firmware_class.path`
- apply candidate path only when requested
- verify required firmware visibility
- restore old path on stop/failure
- log every transition
- still do not start Wi-Fi services by default

If v211 returns `bind-layout-needed`, v212 should implement a temporary
read-only bind-layout proof before any firmware loader change.

If v211 returns `request-name-unknown`, v212 should collect kernel log/request
name evidence without starting Wi-Fi userspace daemons.
