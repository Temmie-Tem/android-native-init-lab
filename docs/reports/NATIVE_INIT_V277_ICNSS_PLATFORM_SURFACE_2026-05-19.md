# Native Init v277 ICNSS/CNSS Platform Surface Report

## Summary

- status: PASS
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- new tool: `scripts/revalidation/wifi_icnss_platform_surface_classifier.py`
- evidence: `tmp/wifi/v277-icnss-platform-surface/`
- decision: `icnss-platform-present-no-wlan-netdev`
- packet transmission: none
- daemon execution: none
- sysfs writes: none

v277 classified the static CNSS/WLAN/QRTR platform surfaces found by v276. The
native state exposes ICNSS and QCA6390 platform nodes plus `/sys/module/wlan`,
but still has no `wlan*` netdev, wiphy, or Wi-Fi rfkill readiness surface.

## Live Findings

| field | result |
| --- | --- |
| ICNSS platform node | present |
| ICNSS driver path | present |
| ICNSS driver-device link | present |
| QCA6390 CNSS platform node | present |
| QCA6390 driver link | absent |
| `/sys/module/wlan` | present |
| `wlan` in `/proc/modules` | absent |
| firmware class path | `/vendor/firmware_mnt/image` |
| `wlan*` netdev | absent |
| wiphy | absent |
| Wi-Fi rfkill | absent |
| ICNSS node entries | `50` |
| QCA6390 node entries | `12` |
| WLAN module entries | `14` |
| devicetree entries | `71` |

Notable surfaces:

- `/sys/devices/platform/soc/18800000.qcom,icnss`
- `/sys/bus/platform/drivers/icnss/18800000.qcom,icnss`
- `/sys/devices/platform/soc/a0000000.qcom,cnss-qca6390`
- `/sys/module/wlan/parameters/fwpath`
- `/sys/firmware/devicetree/base/soc/qcom,icnss@18800000/qcom,wlan-msa-memory`
- `/sys/firmware/devicetree/base/soc/qcom,cnss-qca6390@a0000000/wlan-en-gpio`

## Checks

All critical checks passed:

- expected native init version
- required live captures
- v276 prerequisite decision `qrtr-cnss-platform-surface-visible`
- ICNSS platform node and driver present
- QCA6390 platform node present
- WLAN module surface present
- CNSS process table clean
- no `wlan*`, wiphy, or Wi-Fi rfkill readiness surface

## Interpretation

- Native state is not missing the whole WLAN platform description. ICNSS,
  QCA6390, devicetree, firmware path, and WLAN module surfaces are visible.
- The QCA6390 node does not expose a driver symlink, and no netdev/wiphy/rfkill
  readiness surface is visible. That narrows the blocker to platform-driver
  lifecycle or userspace runtime sequencing before WLAN interface registration.
- QMI payload escalation is still not justified. The next step should classify
  the QCA6390 driver/bus match and safe read-only module parameters, then decide
  whether another bounded CNSS start-only observation is useful.

## Guardrails Preserved

- no sysfs/control writes
- no ICNSS `bind`, `unbind`, `driver_override`, recovery, ramdump, or assert controls
- no QRTR nameservice packet transmission
- no QMI request payload
- no `cnss-daemon`, `cnss_diag`, HAL, supplicant, wificond, or hostapd start
- no Wi-Fi scan/connect/link-up
- no credentials, DHCP, routing, or Internet-facing exposure
- no reboot or remount

## Postflight

- `version`: `A90 Linux init 0.9.60 (v261)`
- `status`: shell responsive, `selftest fail=0`, `netservice: disabled tcpctl=stopped`
- `pidof cnss-daemon`: rc `1`, process absent
- `/proc/net/dev`: `ncm0` present; no `wlan*` interface observed

## Next Step

v278 should focus on the QCA6390 platform-driver gap and WLAN module parameter
surface:

- read-only QCA6390 modalias/uevent/compatible correlation
- safe read-only WLAN module parameter values, especially `fwpath`, `con_mode`,
  `country_code`, and scan/DFS related flags
- compare driver binding expectations without writing `bind`, `unbind`, or
  `driver_override`
- decide whether a later CNSS start-only observation should watch QCA6390 driver
  state transitions, still without scan/connect/link-up
