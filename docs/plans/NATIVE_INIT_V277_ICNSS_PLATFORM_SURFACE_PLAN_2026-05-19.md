# Native Init v277 ICNSS/CNSS Platform Surface Plan

## Summary

- target: v277 ICNSS/CNSS platform surface classifier
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- new tool: `scripts/revalidation/wifi_icnss_platform_surface_classifier.py`
- packet transmission: none
- daemon execution: none
- sysfs writes: none

v276 found that active QRTR service notifications are absent, while static
CNSS/WLAN/QRTR platform surfaces exist in `/sys`. v277 narrows those surfaces by
classifying ICNSS/QCA6390 driver/device/module/devicetree state with read-only
commands only.

## Scope

Read-only live captures:

- ICNSS platform device: `/sys/devices/platform/soc/18800000.qcom,icnss`
- ICNSS driver binding path: `/sys/bus/platform/drivers/icnss`
- QCA6390 CNSS platform device: `/sys/devices/platform/soc/a0000000.qcom,cnss-qca6390`
- WLAN kernel module surface: `/sys/module/wlan`, `/proc/modules`
- firmware path state: `/sys/module/firmware_class/parameters/path`
- WLAN/rfkill/wiphy absence or presence: `/sys/class/net`, `/sys/class/rfkill`, `/sys/class/ieee80211`
- devicetree hints under `qcom,icnss@18800000` and `qcom,cnss-qca6390@a0000000`

## Decision Model

Expected likely decision:

```text
icnss-platform-bound-no-wlan-netdev
```

This means:

- ICNSS/QCA6390 platform surfaces are visible and likely bound.
- WLAN module/platform state is present.
- No `wlan*` netdev, wiphy, or Wi-Fi rfkill is active in native state.
- Therefore the missing step is still userspace/runtime registration or driver
  lifecycle sequencing, not link-up/scan/connect.

Alternative decisions:

- `icnss-platform-incomplete`: required ICNSS/QCA/sysfs evidence is missing.
- `icnss-wlan-readiness-visible`: read-only state unexpectedly exposes `wlan*`,
  wiphy, or Wi-Fi rfkill surfaces.
- `icnss-safety-regression`: `cnss-daemon` appears, `wlan*` appears after the
  no-write pass, or a denied command pattern enters the command set.

## Guardrails

v277 must not:

- write to ICNSS, rfkill, firmware, module, debugfs, configfs, or Android paths
- use ICNSS `bind`, `unbind`, `driver_override`, recovery, ramdump, or assert controls
- start `cnss-daemon`, `cnss_diag`, HAL, supplicant, wificond, hostapd, DHCP,
  or routing commands
- scan/connect/link-up Wi-Fi
- send QRTR nameservice packets or QMI payloads
- reboot or remount partitions

## Validation

Run:

```bash
python3 scripts/revalidation/wifi_icnss_platform_surface_classifier.py \
  --out-dir tmp/wifi/v277-icnss-platform-surface \
  run
```

Static:

```bash
python3 -m py_compile \
  scripts/revalidation/wifi_icnss_platform_surface_classifier.py \
  scripts/revalidation/wifi_qrtr_cnss_registration_correlator.py \
  scripts/revalidation/a90ctl.py

git diff --check
```

Postflight:

```bash
python3 scripts/revalidation/a90ctl.py --json version
python3 scripts/revalidation/a90ctl.py status
python3 scripts/revalidation/a90ctl.py run /cache/bin/toybox pidof cnss-daemon || true
python3 scripts/revalidation/a90ctl.py cat /proc/net/dev
```

## Acceptance

- v277 sends no packets, starts no daemon, and writes no sysfs/control paths.
- required v276 manifest is loaded and checked.
- live read-only captures classify ICNSS/QCA6390/module/netdev/wiphy/rfkill state.
- postflight remains clean: no `cnss-daemon`, no `wlan*` interface.
- report identifies a concrete next step without escalating to QMI payloads.
