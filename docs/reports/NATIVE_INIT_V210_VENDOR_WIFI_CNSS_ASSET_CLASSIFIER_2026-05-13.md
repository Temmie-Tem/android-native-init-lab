# v210 Vendor Wi-Fi/CNSS Asset Classifier

## Summary

v210 adds and validates a read-only native vendor Wi-Fi/CNSS asset classifier.
It reuses the v209 isolated `sda29` temporary mount pattern, captures firmware,
init rc, service binary, library/module, VINTF, and firmware loader evidence,
then compares the native-visible asset map against v206 Android evidence.

Result: PASS.

Final decision: `firmware-path-policy-needed`.

Reason: required Wi-Fi/CNSS firmware exists under the native-visible vendor
filesystem, but the current native `firmware_class.path` is
`/vendor/firmware_mnt/image` and does not point at the visible
`/vendor/firmware/wlan/...` layout.

Active Wi-Fi bring-up remains blocked.

## Changes

- Added `scripts/revalidation/native_vendor_asset_classifier.py`.
- Added v210 plan:
  `docs/plans/NATIVE_INIT_V210_VENDOR_WIFI_CNSS_ASSET_CLASSIFIER_PLAN_2026-05-13.md`.
- Updated task queue and next-work notes.

## Scope

The collector performs a controlled native probe:

- confirms v209 decision `vendor-assets-visible`
- confirms native control with `version`, `status`, and `bootstatus`
- confirms `sda29` major/minor `259:22`
- confirms ext4 availability
- creates temporary paths only under `/tmp/a90-v210-*`
- creates only a temporary block node for `sda29`
- mounts only with `run /cache/bin/toybox mount -t ext4 -o ro,noload ...`
- captures targeted vendor firmware/init/binary/library/VINTF assets
- parses Wi-Fi/CNSS-relevant init service blocks
- checks `firmware_class.path` read-only
- unmounts and verifies no leftover mount remains

## Guardrails

- No plain `mountfs ... ext4 ro`.
- No mount without `ro,noload`.
- No read-write mount.
- No persistent `/dev/block/sda29` creation.
- No mount over `/vendor`, `/mnt/system`, `/dev/block`, or other persistent paths.
- No `firmware_class.path` write.
- No Wi-Fi enablement.
- No rfkill write.
- No WLAN link-up.
- No scan/connect.
- No module load/unload.
- No `cnss-daemon`, `cnss_diag`, Wi-Fi HAL, `wificond`, supplicant, or hostapd start.
- No destructive storage commands.

## Static Validation

```bash
python3 -m py_compile \
  scripts/revalidation/native_vendor_asset_classifier.py \
  scripts/revalidation/native_vendor_ro_mount_probe.py \
  scripts/revalidation/a90harness/evidence.py \
  scripts/revalidation/a90ctl.py
```

Result: PASS.

```bash
python3 - <<'PY'
import sys
sys.path.insert(0, 'scripts/revalidation')
import native_vendor_asset_classifier
native_vendor_asset_classifier.validate_classifier_commands()
print('v210 command guard PASS')
PY
```

Result: PASS.

```bash
git diff --check
```

Result: PASS.

## Device Validation

Runtime:

- `A90 Linux init 0.9.59 (v159)`

Collector run:

```bash
python3 scripts/revalidation/a90ctl.py hide || true

python3 scripts/revalidation/native_vendor_asset_classifier.py \
  --native-bridge \
  --v209-manifest tmp/wifi/v209-vendor-ro-mount-probe/manifest.json \
  --v206-manifest tmp/wifi/v206-android-icnss-cnss-map/manifest.json \
  --out-dir tmp/wifi/v210-vendor-asset-classifier
```

Result: PASS.

Decision:

```text
firmware-path-policy-needed
```

Evidence:

- `tmp/wifi/v210-vendor-asset-classifier/manifest.json`
- `tmp/wifi/v210-vendor-asset-classifier/summary.md`
- `tmp/wifi/v210-vendor-asset-classifier/native/commands/`

Hashes:

- `tmp/wifi/v210-vendor-asset-classifier/manifest.json`:
  `8a820f74497de2118e3bcc5f7e9af718894f5504993caccfe811fffdbd1b0fd7`
- `tmp/wifi/v210-vendor-asset-classifier/summary.md`:
  `5ec39f8a7d4d71c824015acb3cb6c7a9cae77630d2e929dbd10a9628a3af9588`

Post-run sanity:

```text
no v210 leftover mount
```

## Current Result

- `decision`: `firmware-path-policy-needed`
- `major_minor`: `259:22`
- `expected_major_minor`: `true`
- `ext4_available`: `true`
- `mount_attempted`: `true`
- `mount_ok`: `true`
- `mounted_after_mount`: `true`
- `cleanup_rc`: `0`
- `leftover_mount`: `false`
- `visible_count`: `47`
- `missing_required_firmware`: `0`
- `missing_required_init_rc`: `0`
- `missing_required_binaries`: `0`
- `parsed_services`: `btcoex_cont_config`, `cnss-daemon`, `cnss_diag`,
  `hostapd`, `vendor.wifi_hal_ext`, `vendor.wifi_hal_legacy`,
  `wpa_supplicant`
- `firmware_class.path`: `/vendor/firmware_mnt/image`
- `firmware_loader.policy_needed`: `true`

Important evidence:

```text
/tmp/a90-v210-*/sda29 /tmp/a90-v210-*/vendor ext4 ro,relatime,norecovery,i_version 0 0
firmware_class.path: /vendor/firmware_mnt/image
required firmware visible: WCNSS_qcom_cfg.ini, bdwlan.bin, regdb.bin, wlanmdsp.mbn
required firmware under current loader path: none
```

## Native Asset Map

The Android v206 assets are visible from the native v210 vendor mount:

- `/vendor/bin/cnss-daemon`
- `/vendor/bin/cnss_diag`
- `/vendor/bin/hw/android.hardware.wifi@1.0-service`
- `/vendor/bin/hw/vendor.samsung.hardware.wifi@2.0-service`
- `/vendor/bin/hw/wpa_supplicant`
- `/vendor/bin/hw/hostapd`
- `/vendor/firmware/wlan/qca_cld/WCNSS_qcom_cfg.ini`
- `/vendor/firmware/wlan/qca_cld/bdwlan.bin`
- `/vendor/firmware/wlan/qca_cld/regdb.bin`
- `/vendor/firmware/wlanmdsp.mbn`
- `/vendor/etc/init/hw/init.qcom.rc`
- `/vendor/etc/init/hw/init.target.rc`
- `/vendor/etc/init/android.hardware.wifi@1.0-service.rc`
- `/vendor/etc/init/android.hardware.wifi.supplicant-service.rc`
- `/vendor/etc/init/hostapd.android.rc`
- `/vendor/etc/init/vendor.samsung.hardware.wifi@2.0-service.rc`
- `/vendor/etc/vintf/manifest/*.xml` Wi-Fi/supplicant/hostapd entries

Parsed service metadata confirms the expected Android services and capability
requirements:

- `cnss-daemon`: `/system/vendor/bin/cnss-daemon`, `NET_ADMIN`,
  `system inet net_admin wifi`
- `cnss_diag`: `/system/vendor/bin/cnss_diag`, `system wifi inet sdcard_rw media_rw diag`
- `vendor.wifi_hal_legacy`: `/vendor/bin/hw/android.hardware.wifi@1.0-service`,
  `NET_ADMIN NET_RAW SYS_MODULE`, `wifi gps`
- `vendor.wifi_hal_ext`: `/vendor/bin/hw/vendor.samsung.hardware.wifi@2.0-service`,
  `NET_ADMIN NET_RAW SYS_MODULE`, `wifi gps`
- `wpa_supplicant`: `/vendor/bin/hw/wpa_supplicant`, `disabled oneshot`
- `hostapd`: `/vendor/bin/hw/hostapd`, `NET_ADMIN NET_RAW`,
  `wifi net_raw net_admin`, `disabled oneshot`

## Interpretation

v209 proved that the vendor partition can be mounted safely read-only. v210
proves that the Android-side Wi-Fi/CNSS asset set is visible from native init
once that mount exists. The remaining blocker is not missing firmware, missing
init rc, or missing service binaries. The immediate blocker is path policy:
native currently reports `firmware_class.path=/vendor/firmware_mnt/image`, while
the required Wi-Fi firmware is under the mounted vendor filesystem at
`firmware/wlan/qca_cld` and `firmware/wlanmdsp.mbn`.

The next step should therefore avoid daemon bring-up and first design a
non-mutating firmware path/layout policy. That plan should decide whether native
init should prepare a future `/vendor` bind layout, a firmware symlink layout, or
an opt-in guarded firmware loader path update with rollback.

## Acceptance

- v210 uses only isolated ext4 `ro,noload` temporary mount.
- Required vendor firmware files are classified.
- Required init rc files and service definitions are parsed.
- Required service binaries are visible.
- VINTF Wi-Fi/supplicant/hostapd entries are captured.
- Current firmware loader implication is documented.
- Android v206 evidence is compared against native-visible vendor assets.
- The temporary mount is cleaned up.
- Active Wi-Fi bring-up remains blocked.
