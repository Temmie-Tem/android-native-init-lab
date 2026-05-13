# v210 Plan: Vendor Wi-Fi/CNSS Asset Classifier

## Summary

v210 follows the v209 `vendor-assets-visible` result. The goal is to classify the
native-visible vendor Wi-Fi/CNSS asset set and decide whether the next step can
safely move to read-only CNSS/ICNSS userspace feasibility.

This is not Wi-Fi bring-up. v210 should not start daemons, write firmware loader
state, bring up WLAN, scan, or connect. It only maps files, init service metadata,
firmware lookup implications, binary/library presence, and Android-vs-native
asset parity.

Implementation target:

- `scripts/revalidation/native_vendor_asset_classifier.py`
- evidence output: `tmp/wifi/v210-vendor-asset-classifier`
- report: `docs/reports/NATIVE_INIT_V210_VENDOR_WIFI_CNSS_ASSET_CLASSIFIER_2026-05-13.md`

## Baseline

- v206 decision: `ready-for-native-preflight-plan`
- v207 decision: `missing-mounted-vendor`
- v208 decision: `vendor-block-candidate-found`
- v209 decision: `vendor-assets-visible`
- v209 proved:
  - `sda29` major/minor is `259:22`
  - ext4 `ro,noload` mount works from native
  - cleanup succeeds and no leftover mount remains
  - native-visible vendor assets include:
    - `etc/init`
    - `etc/init/hw`
    - `etc/init/android.hardware.wifi.supplicant-service.rc`
    - `etc/init/android.hardware.wifi@1.0-service.rc`
    - `etc/init/hostapd.android.rc`
    - `etc/init/hw/init.qcom.rc`
    - `etc/wifi`
    - `firmware/wlan/qca_cld/bdwlan.bin`
    - `firmware/wlan/qca_cld/regdb.bin`
    - `firmware/wlanmdsp.mbn`
    - `lib/modules`

## Reference Model

- Android Wi-Fi HAL is split across framework-visible Wi-Fi services, vendor HAL
  implementations, supplicant, and hostapd. Android 13 and lower use HIDL vendor
  HAL definitions, so vendor `bin/hw` and init rc service mapping matter:
  <https://source.android.com/docs/core/connect/wifi-hal>
- Android init service definitions encode service executable, args, class, user,
  group, capabilities, disabled/oneshot policy, and import ordering. Native init
  cannot assume that running a vendor binary directly is equivalent to Android
  init launching the service:
  <https://android.googlesource.com/platform/system/core/+/master/init/README.md>
- Android ambient capabilities show Wi-Fi-related services such as `wificond`
  need groups/capabilities like `wifi`, `net_raw`, `net_admin`, `NET_RAW`, and
  `NET_ADMIN`; v210 should classify required capabilities but not execute
  services:
  <https://source.android.com/docs/core/permissions/ambient>
- Linux firmware loader search paths and `firmware_class.path` determine whether
  visible firmware files are actually discoverable by the kernel. v210 reads the
  current state only and must not write the sysfs parameter:
  <https://www.kernel.org/doc/html/v6.15/driver-api/firmware/fw_search_path.html>

## Scope

Add `scripts/revalidation/native_vendor_asset_classifier.py`.

The collector should reuse the v209 safe mount pattern:

1. Load v209 manifest and require decision `vendor-assets-visible` unless
   `--allow-non-v209-decision` is explicitly set.
2. Confirm native control with `version`, `status`, and `bootstatus`.
3. Confirm `sda29` major/minor and ext4 availability.
4. Create a run-specific temporary base path under `/tmp/a90-v210-*`.
5. Create a temporary block node only under that base path.
6. Mount vendor with `run /cache/bin/toybox mount -t ext4 -o ro,noload`.
7. Capture asset inventory.
8. Always unmount and verify no leftover mount remains.

## Inventory Targets

### Firmware

Capture read-only presence/listings/stats for:

- `firmware`
- `firmware/wlan`
- `firmware/wlan/qca_cld`
- `firmware/wlan/qca_cld/WCNSS_qcom_cfg.ini`
- `firmware/wlan/qca_cld/bdwlan.bin`
- `firmware/wlan/qca_cld/bdwlan.bin*`
- `firmware/wlan/qca_cld/regdb.bin`
- `firmware/wlanmdsp.mbn`
- `firmware_mnt`
- `firmware_mnt/image`
- `bt_firmware`
- `firmware-modem`

### Init and Service RC

Capture read-only files and grep results for:

- `etc/init`
- `etc/init/hw`
- `etc/init/hw/init.qcom.rc`
- `etc/init/android.hardware.wifi@1.0-service.rc`
- `etc/init/android.hardware.wifi.supplicant-service.rc`
- `etc/init/hostapd.android.rc`
- `etc/init/btcoex_cont_config.rc`
- any file matching `wifi|wlan|cnss|icnss|qca|qti|hostapd|supplicant|firmware`

Parse service blocks when possible:

- service name
- executable path
- arguments
- class
- user
- groups
- capabilities
- disabled/oneshot/critical
- seclabel
- socket/file/sysfs dependencies if visible in nearby lines

### Binaries

Capture read-only presence for likely Android v206 service binaries:

- `bin/cnss-daemon`
- `bin/cnss_diag`
- `bin/hw/android.hardware.wifi@1.0-service`
- `bin/hw/vendor.samsung.hardware.wifi@2.0-service`
- `bin/hw/wpa_supplicant`
- `bin/hw/hostapd`
- `bin/hostapd_cli`
- `bin/init.crda.sh`
- `bin/init.qcom.sdio.sh`
- `bin/wifi_ftmd`

### Libraries and Modules

Capture read-only presence/listings for:

- `lib`
- `lib64`
- `lib/modules`
- library names referenced by Wi-Fi/CNSS vendor binaries if `readelf`, `objdump`,
  or `strings` is available from existing tools
- otherwise record `dependency-parser-unavailable` and keep the decision
  conservative

### VINTF and HAL Manifests

Capture read-only presence/listings/grep for:

- `etc/vintf`
- `etc/vintf/manifest.xml`
- `etc/vintf/manifest/*.xml`
- HAL entries matching `wifi|wlan|supplicant|hostapd|qti|samsung`

### Firmware Loader State

Capture read-only native state:

- `cat /sys/module/firmware_class/parameters/path`
- current vendor mount path from v210
- whether expected firmware files are under a path the kernel would search now
- whether a future bind/symlink or firmware path policy is needed

Do not write `firmware_class.path` in v210.

## Android-vs-Native Comparison

Compare against v206 Android evidence:

- Android running service state:
  - `cnss-daemon`
  - `cnss_diag`
  - `vendor.wifi_hal_legacy`
  - `vendor.wifi_hal_ext`
  - `wificond`
  - `wpa_supplicant`
- Android-known vendor firmware paths:
  - `bdwlan.bin`
  - `regdb.bin`
  - `WCNSS_qcom_cfg.ini`
  - `wlanmdsp.mbn`
- Android-known init rc files and service definitions
- Android-known netdev/wiphy result:
  - `wlan0`
  - `phy0`

The output should include a parity matrix:

```text
android item | native vendor path | visible | category | next implication
```

## Guardrails

The script must not:

- run plain `mountfs ... ro`
- run mount without `ro,noload`
- mount read-write
- remount an existing system/vendor mount
- mount over `/vendor`, `/mnt/system`, `/dev/block`, or any persistent path
- create `/dev/block/sda29` directly
- write `firmware_class.path`
- write vendor/product/system/cache firmware files
- enable Wi-Fi
- write rfkill state
- bring up a WLAN interface
- scan/connect
- load/unload modules
- start `cnss-daemon`, `cnss_diag`, Wi-Fi HAL, `wificond`, supplicant, or hostapd
- touch `efs`, `sec_efs`, modem, persist, key, vbmeta, bootloader, boot,
  recovery, or userdata partitions
- run `dd`, `mkfs`, `sgdisk`, `parted`, `blockdev --set*`, `fsck`, `e2fsck`, or
  destructive storage commands

## Command Guard

`native_vendor_asset_classifier.py` should include a static command guard.

Allowed mutation-like commands are limited to the temporary probe path:

- `mkdir /tmp/a90-v210-*/...`
- `mknodb /tmp/a90-v210-*/sda29 259 22`
- `run /cache/bin/toybox mount -t ext4 -o ro,noload /tmp/a90-v210-*/sda29 /tmp/a90-v210-*/vendor`
- `umount /tmp/a90-v210-*/vendor`

All other commands should be read-only observation commands such as `cat`, `ls`,
`stat`, `find`, `grep`, `strings`, or `readelf` if the tool exists and is used
only on files under the temporary v210 mountpoint.

The guard must reject:

- any `mount` command missing `ro,noload`
- any probe source/target outside `/tmp/a90-v210-*`
- direct `/dev/block/sda29` creation
- Wi-Fi activation command patterns already blocked by v207/v208/v209
- daemon start or binary execution for Wi-Fi/CNSS services

## Decision Model

- `asset-map-ready`
  - firmware, init rc, service binary, and enough library/module evidence are
    visible to design read-only CNSS/ICNSS userspace feasibility.
- `firmware-path-policy-needed`
  - required firmware exists, but current native firmware loader search path
    would not find it without a future bind/symlink/path policy.
- `service-dependency-gap`
  - firmware exists, but service binaries, libraries, capabilities, or init
    execution metadata are incomplete or too risky to model yet.
- `vendor-assets-incomplete`
  - vendor mount works but required Wi-Fi/CNSS files are missing.
- `dependency-parser-unavailable`
  - asset files exist, but available native tools cannot inspect binary/library
    dependencies enough for a safe next step.
- `cleanup-failed`
  - mount succeeded or partially succeeded but post-run cleanup cannot prove the
    temporary mount is gone.
- `manual-review-required`
  - bridge/control/evidence collection failed or evidence is inconsistent.

## Validation Plan

Static validation:

```bash
python3 -m py_compile \
  scripts/revalidation/native_vendor_asset_classifier.py \
  scripts/revalidation/native_vendor_ro_mount_probe.py \
  scripts/revalidation/a90harness/evidence.py

python3 - <<'PY'
import sys
sys.path.insert(0, 'scripts/revalidation')
import native_vendor_asset_classifier
native_vendor_asset_classifier.validate_classifier_commands()
print('v210 command guard PASS')
PY

git diff --check
```

Native device validation:

```bash
python3 scripts/revalidation/a90ctl.py hide || true

python3 scripts/revalidation/native_vendor_asset_classifier.py \
  --native-bridge \
  --v209-manifest tmp/wifi/v209-vendor-ro-mount-probe/manifest.json \
  --v206-manifest tmp/wifi/v206-android-icnss-cnss-map/manifest.json \
  --out-dir tmp/wifi/v210-vendor-asset-classifier
```

Post-run sanity checks if needed:

```bash
python3 scripts/revalidation/a90ctl.py cat /proc/mounts
python3 scripts/revalidation/a90ctl.py ls /tmp
```

Expected output:

- private/no-follow evidence bundle
- `manifest.json`
- `summary.md`
- asset parity matrix
- service metadata summary
- firmware lookup implication summary
- pre/post mount snapshots and cleanup status
- one of the defined decisions
- no active Wi-Fi commands

## Acceptance

- Vendor mount is performed only with `ro,noload` and cleaned up.
- No leftover v210 mount remains.
- Wi-Fi/CNSS firmware paths are classified.
- Vendor init rc service definitions are parsed or captured with enough evidence.
- Service binary/library/module presence is classified.
- Current native firmware loader search-path implication is documented.
- Android v206 service/firmware evidence is compared against native-visible
  vendor assets.
- A clear next decision is produced without Wi-Fi enablement.

## Next

If v210 returns `asset-map-ready`, v211 should design read-only CNSS/ICNSS
userspace feasibility: no daemon start by default, only service environment,
capability, library, property, socket, firmware lookup, and kernel-side readiness
checks.

If v210 returns `firmware-path-policy-needed`, v211 should design a non-mutating
firmware path policy proposal first, such as temporary bind/symlink layout or a
future opt-in firmware_class path write guarded by rollback.

If v210 returns `service-dependency-gap`, v211 should focus on vendor binary and
init rc dependency expansion before any daemon feasibility work.
