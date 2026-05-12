# v204 Plan: Android/TWRP Wi-Fi Driver and Firmware Baseline

## Summary

v204 collects Android-boot and TWRP read-only Wi-Fi evidence before any active
native-init Wi-Fi bring-up. The v203 native/mounted-system baseline passed, but
its final decision is `no-go`: Android-side Wi-Fi files exist while the native
kernel-facing gates are still absent.

v204 therefore answers one narrower question:

> When Android or TWRP owns the device state, what Wi-Fi driver, firmware, HAL,
> init, module, rfkill, and kernel log evidence is visible without enabling or
> mutating Wi-Fi?

This is a host-side evidence step. It does not build or flash a new native-init
boot image.

## Background

- v203 PASS result: `docs/reports/NATIVE_INIT_V203_WIFI_BASELINE_REFRESH_2026-05-13.md`
- v203 final decision: `no-go`
- v203 missing gates:
  - `native-wlan-interface`
  - `wifi-rfkill`
  - `wlan-cnss-qca-module-evidence`
- v203 Android-side candidates were framework/init/permission files only, not a
  proven kernel-facing WLAN device or driver path.

Reference model:

- Android Wi-Fi is service/HAL driven. The framework talks to Wi-Fi services,
  Wi-Fi HAL surfaces, `wificond`, supplicant, hostapd, and the kernel driver.
- Linux wireless user space talks to kernel wireless drivers through
  `cfg80211`/`nl80211` paths.
- Linux firmware loading is driver request based, so firmware path candidates
  are useful only when correlated with an actual driver/module/log hint.

References:

- <https://source.android.com/docs/core/connect/wifi-overview>
- <https://source.android.com/docs/core/connect/wifi-hal>
- <https://docs.kernel.org/driver-api/80211/cfg80211.html>
- <https://www.kernel.org/doc/html/latest/driver-api/firmware/fw_search_path.html>

## Goals

- Implement a host-side read-only collector:
  `scripts/revalidation/android_twrp_wifi_baseline.py`.
- Support Android ADB and TWRP ADB evidence modes.
- Keep all output private/no-follow through existing evidence helpers.
- Compare Android/TWRP evidence against the v203 native result.
- Produce a clear next-step decision for v205.

## Non-Goals

- Do not enable Wi-Fi.
- Do not run `svc wifi enable`, `cmd wifi set-wifi-enabled`, or equivalent.
- Do not run `rfkill unblock` or write any rfkill state.
- Do not run `ip link set wlan0 up` or bring any WLAN interface up.
- Do not load, unload, or insert modules.
- Do not copy, patch, replace, or relocate firmware.
- Do not start supplicant, hostapd, vendor Wi-Fi daemons, or Android Wi-Fi
  services manually.
- Do not collect `/data/misc/wifi` by default.
- Do not capture SSIDs, PSKs, saved networks, tokens, or account data.
- Do not expose Wi-Fi/NCM/broker/tcpctl outside the current trusted USB-local
  boundary.

## Collector Design

`android_twrp_wifi_baseline.py` supports:

```text
--android-adb
--twrp-adb
--adb adb
--serial <optional-adb-serial>
--timeout 30
--out-dir tmp/wifi/v204-android-twrp-baseline-<UTC>
--v203-manifest tmp/wifi/v203-baseline/manifest.json
--include-sensitive-default-off
```

Suggested output:

```text
tmp/wifi/v204-android-twrp-baseline-<UTC>/
├── manifest.json
├── summary.md
├── android/
│   └── commands/*.txt
├── twrp/
│   └── commands/*.txt
└── compare/
    └── v203-v204-matrix.json
```

## Evidence Matrix

### Safe Android/TWRP Commands

These commands are read-only and should be captured per selected mode:

- Identity and environment:
  - `getprop ro.product.model`
  - `getprop ro.build.fingerprint`
  - `getprop ro.boot.*` filtered to non-sensitive fields
  - `uname -a`
  - `id`
- Kernel/network visibility:
  - `ip link`
  - `ls -l /sys/class/net /sys/class/rfkill`
  - `cat /proc/modules`
  - `cat /proc/cmdline`
  - `dmesg | grep -Ei 'wlan|wifi|qca|qcacld|cnss|wcn|firmware|cfg80211|nl80211' | tail -n 200`
- Android/Vendor Wi-Fi metadata:
  - `getprop | grep -Ei 'wifi|wlan|qca|qcacld|cnss|wcn|firmware'`
  - `find /vendor /odm /product /system -maxdepth 6` for Wi-Fi patterns
  - VINTF manifest files under `/vendor/etc/vintf`, `/odm/etc/vintf`,
    `/system/etc/vintf`
  - init rc files under `/vendor/etc/init`, `/odm/etc/init`, `/system/etc/init`
  - firmware-like paths under `/vendor/firmware`, `/vendor/firmware_mnt`,
    `/vendor/etc/wifi`, `/odm/etc/wifi`, `/product/etc/wifi`, `/system/etc/wifi`

### Explicitly Excluded by Default

- `/data/misc/wifi`
- `dumpsys wifi`
- `cmd wifi status`
- `wpa_cli`
- `iw` commands that talk to nl80211
- any command that starts, stops, enables, or mutates Wi-Fi state

`dumpsys wifi` and `/data/misc/wifi` may only be considered later with a
separate redaction plan and explicit operator approval.

## Parsing and Classification

The collector should classify evidence into these buckets:

- `interface_evidence`
  - `wlan*`, `swlan*`, `p2p*`, `wifi-aware`, `phy*`, or clear wireless netdev
- `rfkill_evidence`
  - Wi-Fi-like rfkill node, not Bluetooth-only `bt_power`
- `module_evidence`
  - `wlan`, `qcacld`, `qca`, `cnss`, `wcn`, `ath`, `cfg80211`, `mac80211`
- `firmware_evidence`
  - `bdwlan`, `qwlan`, `wlanmdsp`, `Data.msc`, `WCNSS`, QCA/CNSS firmware paths
- `hal_evidence`
  - `android.hardware.wifi`, `vendor.qti.hardware.wifi`, supplicant/hostapd HAL
- `init_service_evidence`
  - `wifi.rc`, `wificond.rc`, vendor Wi-Fi init services
- `kernel_log_evidence`
  - driver probe, firmware request, CNSS/WCN/QCA failures or success messages

## Decision Model

The v204 report should emit one of these decisions:

- `blocked-no-android-kernel-gate`
  - Android/TWRP also shows no WLAN/rfkill/module/log evidence.
- `driver-candidate-found`
  - Android/TWRP shows driver/module/firmware/log candidates, but native init
    still lacks the gate.
- `ready-for-readonly-nl80211-probe-plan`
  - Android/TWRP shows a plausible WLAN/rfkill/module/log path and native next
    step can be a separate v205 read-only nl80211/cfg80211 probe plan.
- `manual-review-required`
  - Evidence conflicts, permissions are insufficient, or mode coverage is
    incomplete.

No v204 decision may approve active Wi-Fi enablement.

## Guardrails

The collector must hard-fail before execution if its command list includes active
mutation patterns:

```text
rfkill unblock
ip link set .* up
insmod
rmmod
modprobe
svc wifi
cmd wifi set-wifi-enabled
wpa_supplicant
hostapd
```

Read-only path searches may mention `wpa_supplicant` or `hostapd` as filenames,
but must not execute those binaries.

## Validation

Static validation:

```bash
git diff --check

python3 -m py_compile \
  scripts/revalidation/android_twrp_wifi_baseline.py \
  scripts/revalidation/wifi_baseline_refresh.py \
  scripts/revalidation/a90_kernel_tools.py \
  scripts/revalidation/a90harness/evidence.py

python3 - <<'PY'
import sys
sys.path.insert(0, "scripts/revalidation")
import android_twrp_wifi_baseline
android_twrp_wifi_baseline.validate_no_active_wifi_commands()
print("android/twrp wifi baseline command guard PASS")
PY
```

Android mode validation:

```bash
python3 scripts/revalidation/android_twrp_wifi_baseline.py \
  --android-adb \
  --v203-manifest tmp/wifi/v203-baseline/manifest.json \
  --out-dir tmp/wifi/v204-android-baseline
```

TWRP mode validation:

```bash
python3 scripts/revalidation/android_twrp_wifi_baseline.py \
  --twrp-adb \
  --v203-manifest tmp/wifi/v203-baseline/manifest.json \
  --out-dir tmp/wifi/v204-twrp-baseline
```

Combined mode validation, if both environments are available in one maintenance
cycle:

```bash
python3 scripts/revalidation/android_twrp_wifi_baseline.py \
  --android-adb \
  --twrp-adb \
  --v203-manifest tmp/wifi/v203-baseline/manifest.json \
  --out-dir tmp/wifi/v204-android-twrp-baseline
```

## Acceptance

- Android and/or TWRP evidence is captured into private bundle output.
- The collector never mutates Wi-Fi, rfkill, module, firmware, service, firewall,
  debug, storage, or boot state.
- The report compares v203 native missing gates against Android/TWRP evidence.
- The result is one of the four v204 decisions above.
- If `ready-for-readonly-nl80211-probe-plan` is reached, v205 must still be a
  separate read-only probe plan, not active Wi-Fi bring-up.

## Next

If v204 finds real Android/TWRP driver/module/rfkill/log evidence, plan v205 as
controlled read-only `nl80211/cfg80211` probing. If not, keep Wi-Fi bring-up
blocked and pivot to documenting missing kernel/vendor driver conditions.
