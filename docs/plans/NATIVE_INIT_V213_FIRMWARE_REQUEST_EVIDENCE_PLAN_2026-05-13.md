# v213 Plan: Firmware Request Evidence / ICNSS Reprobe Preflight

## Summary

v213 follows the v212 `path-rollback-pass` result. The goal is to collect
evidence that the guarded firmware path policy can support a real ICNSS/WLAN
driver firmware request, while still avoiding Wi-Fi connection, scan, supplicant,
HAL, and hostapd bring-up.

This is not Wi-Fi connection work. The default mode must remain read-only. Any
driver reprobe must be opt-in, explicitly named, and immediately rolled back.

- baseline runtime: `A90 Linux init 0.9.59 (v159)`
- planned collector: `scripts/revalidation/native_firmware_request_probe.py`
- optional helper: `stage3/linux_init/helpers/a90_icnssctl.c`
- evidence output: `tmp/wifi/v213-firmware-request-evidence`
- report after implementation:
  `docs/reports/NATIVE_INIT_V213_FIRMWARE_REQUEST_EVIDENCE_2026-05-13.md`

## Current Evidence Chain

- v205: native ICNSS platform node exists, but no WLAN netdev, Wi-Fi rfkill, or
  wiphy is visible.
- v206: Android maps ICNSS/CNSS/Wi-Fi service state and vendor firmware paths.
- v207: native Wi-Fi preflight is blocked by missing mounted vendor firmware.
- v208: `sda29` is the vendor block candidate.
- v209: temporary ext4 `ro,noload` vendor mount exposes vendor firmware/init
  assets.
- v210: vendor firmware exists, but current native firmware lookup does not find
  it.
- v211: `/mnt/vendor/firmware` is the preferred firmware path policy.
- v212: `firmware_class.path=/mnt/vendor/firmware` can be applied, verified,
  and rolled back with no leftover mount.

Important v212 result:

```text
decision=path-rollback-pass
applied firmware_class.path=/mnt/vendor/firmware
rolled back firmware_class.path=/vendor/firmware_mnt/image
```

## Reference Notes

- Linux firmware lookup checks optional `firmware_class.path` before default
  `/lib/firmware...` paths. The runtime sysfs parameter is writable, but newline
  characters become part of the value:
  <https://www.kernel.org/doc/html/latest/driver-api/firmware/fw_search_path.html>
- `request_firmware()` receives a firmware `name`, which can include a relative
  path such as `wlan/qca_cld/bdwlan.bin`. The driver processes the returned
  firmware and then releases it:
  <https://www.kernel.org/doc/html/v4.17/driver-api/firmware/request_firmware.html>
- Dynamic debug would be useful for firmware/driver request evidence, but it is
  only available when `/proc/dynamic_debug/control` exists:
  <https://kernel.org/doc/html/next/admin-guide/dynamic-debug-howto.html>
- Event tracing would be useful if tracefs and matching events are available,
  but this device currently has no visible `/sys/kernel/tracing/events` path:
  <https://origin.kernel.org/doc/html/v6.13/trace/events.html>
- Android Wi-Fi bring-up is layered through framework services, Wi-Fi HAL,
  wificond, and nl80211. v213 must stay below this layer and avoid framework or
  supplicant bring-up:
  <https://source.android.com/docs/core/connect/wifi-overview?hl=en>

## Live Constraints Observed Before Planning

Observed on the current native device:

- `/proc/dynamic_debug/control`: absent
- `/sys/kernel/tracing/events`: absent
- `/sys/kernel/debug/tracing/events/firmware`: absent
- ICNSS platform node: `/sys/devices/platform/soc/18800000.qcom,icnss`
- ICNSS driver: `/sys/bus/platform/drivers/icnss`
- ICNSS driver controls:
  - `/sys/bus/platform/drivers/icnss/bind`
  - `/sys/bus/platform/drivers/icnss/unbind`
- ICNSS uevent reports:

```text
DRIVER=icnss
OF_NAME=qcom,icnss
OF_FULLNAME=/soc/qcom,icnss@18800000
OF_COMPATIBLE_0=qcom,icnss
MODALIAS=of:Nqcom,icnssT<NULL>Cqcom,icnss
```

Because dynamic debug and trace events are not available, the useful v213
evidence source is controlled ICNSS reprobe plus before/after `dmesg`, sysfs,
netdev, rfkill, and wiphy snapshots.

## Core Question

v213 must answer:

> If native init temporarily exposes `/mnt/vendor/firmware` through
> `firmware_class.path`, does a controlled ICNSS/WLAN driver reprobe produce
> firmware request evidence, WLAN netdev/wiphy/rfkill evidence, or an explicit
> failure reason, and can all state be rolled back safely?

## Scope

Allowed by default:

- read existing v205-v212 manifests
- collect `version`, `status`, `bootstatus`
- collect current `firmware_class.path`
- inspect `/proc/mounts`, `/proc/filesystems`
- inspect ICNSS platform sysfs and driver sysfs
- inspect `/sys/class/net`, `/sys/class/rfkill`, `/sys/class/ieee80211`
- collect filtered `dmesg`
- verify `/cache/bin/a90_fwpathctl` availability

Allowed only with explicit `--apply-path`:

- temporary `sda29` block node under `/tmp/a90-v213-*`
- temporary `/mnt/vendor` mount with ext4 `ro,noload`
- `run /cache/bin/a90_fwpathctl write /mnt/vendor/firmware`
- rollback to the saved original `firmware_class.path`
- `umount /mnt/vendor`

Allowed only with explicit `--reprobe` and a second confirmation flag such as
`--i-understand-icnss-reprobe`:

- write `18800000.qcom,icnss` to
  `/sys/bus/platform/drivers/icnss/unbind`
- write `18800000.qcom,icnss` to
  `/sys/bus/platform/drivers/icnss/bind`
- compare post-reprobe ICNSS/netdev/rfkill/wiphy/dmesg evidence

Forbidden:

- `svc wifi`
- `cmd wifi`
- `rfkill block` / `rfkill unblock`
- `ip link set wlan0 up`
- scan/connect commands
- `cnss-daemon`, `cnss_diag`, Wi-Fi HAL, `wificond`, `wpa_supplicant`,
  `hostapd`
- module load/unload
- firmware file copy
- `/lib/firmware` mutation
- persistent mount or bind mount
- boot image or PID1 change

## Recommended Implementation

Add `scripts/revalidation/native_firmware_request_probe.py`.

Inputs:

- `--v209-manifest tmp/wifi/v209-vendor-ro-mount-probe/manifest.json`
- `--v210-manifest tmp/wifi/v210-vendor-asset-classifier/manifest.json`
- `--v211-manifest tmp/wifi/v211-firmware-path-policy/manifest.json`
- `--v212-manifest tmp/wifi/v212-firmware-path-rollback/manifest.json`
- `--out-dir tmp/wifi/v213-firmware-request-evidence`
- `--apply-path`
- `--reprobe`
- `--i-understand-icnss-reprobe`

Modes:

1. `baseline`
   - no mutation
   - captures ICNSS/sysfs/dmesg baseline only
   - decision should be `baseline-only`
2. `--apply-path`
   - performs v212-style mount/path apply/readback/rollback
   - no ICNSS unbind/bind
   - decision should be `path-only-pass` or a failure decision
3. `--apply-path --reprobe --i-understand-icnss-reprobe`
   - applies firmware path
   - captures pre-reprobe evidence
   - unbinds/binds ICNSS through an exact fixed-target helper or guarded command
   - captures post-reprobe evidence
   - rolls back firmware path and unmounts vendor
   - decision should identify captured request evidence or explicit missing
     evidence

Prefer a tiny static helper if the shell cannot safely write ICNSS bind/unbind:

- `stage3/linux_init/helpers/a90_icnssctl.c`
- fixed device id: `18800000.qcom,icnss`
- fixed targets:
  - `/sys/bus/platform/drivers/icnss/unbind`
  - `/sys/bus/platform/drivers/icnss/bind`
- commands:
  - `status`
  - `unbind`
  - `bind`
- no arbitrary path writes

## Evidence Commands

Baseline captures:

- `version`
- `status`
- `bootstatus`
- `cat /sys/module/firmware_class/parameters/path`
- `cat /proc/mounts`
- `cat /proc/filesystems`
- `cat /sys/devices/platform/soc/18800000.qcom,icnss/uevent`
- `cat /sys/devices/platform/soc/18800000.qcom,icnss/modalias`
- `ls /sys/devices/platform/soc/18800000.qcom,icnss`
- `ls /sys/devices/platform/soc/18800000.qcom,icnss/ramdump`
- `ls /sys/bus/platform/drivers/icnss`
- `stat /sys/bus/platform/drivers/icnss/bind`
- `stat /sys/bus/platform/drivers/icnss/unbind`
- `ls /sys/class/net`
- `ls /sys/class/rfkill`
- `ls /sys/class/ieee80211`
- `run /cache/bin/toybox dmesg`

The collector should filter and record lines matching:

```text
firmware|icnss|cnss|wlan|wifi|qca|wcn|bdwlan|regdb|wlanmdsp|WCNSS
```

Post-reprobe captures must repeat the net/rfkill/wiphy/ICNSS/dmesg captures and
compare before/after deltas.

## Command Guard

The collector must include a static guard similar to v207-v212.

Allowed mutation-like commands are limited to:

- v212-style temporary mount and `a90_fwpathctl` apply/rollback commands
- optional ICNSS reprobe only when both `--reprobe` and
  `--i-understand-icnss-reprobe` are present
- exact ICNSS device id: `18800000.qcom,icnss`
- exact bind/unbind target paths

Any command containing the forbidden Wi-Fi activation patterns must fail before
execution.

## Decision Model

- `baseline-only`
  - read-only baseline was collected; no apply/reprobe was requested
- `path-only-pass`
  - firmware path apply/readback/rollback passed; no reprobe was requested
- `request-evidence-captured`
  - reprobe produced firmware request or related WLAN/ICNSS evidence
- `request-evidence-missing`
  - reprobe completed but no firmware request, netdev, rfkill, wiphy, or useful
    dmesg evidence appeared
- `icnss-rebind-failed`
  - ICNSS did not return to a bound driver state
- `path-rollback-failed`
  - original `firmware_class.path` was not restored
- `cleanup-failed`
  - `/mnt/vendor` or `/tmp/a90-v213-*` mount remained
- `manual-review-required`
  - prerequisite manifests, paths, or state did not match expected v209-v212
    decisions

## Validation

Static validation:

```text
python3 -m py_compile \
  scripts/revalidation/native_firmware_request_probe.py \
  scripts/revalidation/native_firmware_path_apply_probe.py \
  scripts/revalidation/a90harness/evidence.py

python3 - <<'PY'
import sys
sys.path.insert(0, 'scripts/revalidation')
import native_firmware_request_probe
native_firmware_request_probe.validate_no_active_wifi_commands()
native_firmware_request_probe.validate_command_guard()
print('v213 command guard PASS')
PY

git diff --check
```

Baseline live validation:

```text
python3 scripts/revalidation/native_firmware_request_probe.py \
  --native-bridge \
  --v209-manifest tmp/wifi/v209-vendor-ro-mount-probe/manifest.json \
  --v210-manifest tmp/wifi/v210-vendor-asset-classifier/manifest.json \
  --v211-manifest tmp/wifi/v211-firmware-path-policy/manifest.json \
  --v212-manifest tmp/wifi/v212-firmware-path-rollback/manifest.json \
  --out-dir tmp/wifi/v213-firmware-request-evidence
```

Path-only live validation:

```text
python3 scripts/revalidation/native_firmware_request_probe.py \
  --native-bridge \
  --apply-path \
  --v209-manifest tmp/wifi/v209-vendor-ro-mount-probe/manifest.json \
  --v210-manifest tmp/wifi/v210-vendor-asset-classifier/manifest.json \
  --v211-manifest tmp/wifi/v211-firmware-path-policy/manifest.json \
  --v212-manifest tmp/wifi/v212-firmware-path-rollback/manifest.json \
  --out-dir tmp/wifi/v213-firmware-request-evidence
```

Reprobe validation is intentionally separate and must only be run after the
baseline and path-only modes pass:

```text
python3 scripts/revalidation/native_firmware_request_probe.py \
  --native-bridge \
  --apply-path \
  --reprobe \
  --i-understand-icnss-reprobe \
  --v209-manifest tmp/wifi/v209-vendor-ro-mount-probe/manifest.json \
  --v210-manifest tmp/wifi/v210-vendor-asset-classifier/manifest.json \
  --v211-manifest tmp/wifi/v211-firmware-path-policy/manifest.json \
  --v212-manifest tmp/wifi/v212-firmware-path-rollback/manifest.json \
  --out-dir tmp/wifi/v213-firmware-request-evidence
```

## Acceptance

- Default baseline mode performs no mutation.
- Path-only mode proves the v212 path policy is reusable and rollback-safe.
- Reprobe mode, if executed, leaves ICNSS bound again.
- Final `firmware_class.path` equals the original value.
- No `/mnt/vendor` or `/tmp/a90-v213-*` mount remains.
- No Wi-Fi framework service, HAL, `wificond`, supplicant, or hostapd starts.
- Evidence clearly states whether firmware request evidence was captured or
  missing.

## Next Step After PASS

If v213 captures useful firmware request evidence and ICNSS returns to a safe
state, v214 can plan a stricter controlled ICNSS/CNSS service preflight. If v213
does not capture request evidence, v214 should focus on better observability
first, such as pstore/dmesg persistence, kernel loglevel policy, or a safer
driver-specific evidence helper.
