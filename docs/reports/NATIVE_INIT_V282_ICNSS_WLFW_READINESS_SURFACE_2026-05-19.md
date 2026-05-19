# Native Init v282 ICNSS/WLFW Readiness Surface Report

## Summary

- plan: `docs/plans/NATIVE_INIT_V282_ICNSS_WLFW_READINESS_SURFACE_PLAN_2026-05-19.md`
- tool: `scripts/revalidation/wifi_icnss_wlfw_readiness_surface.py`
- evidence: `tmp/wifi/v282-icnss-wlfw-readiness-surface/`
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- decision: `icnss-readiness-sysfs-candidates-limited`
- result: PASS

v282 ran a no-start, read-only ICNSS/WLFW readiness surface observer. It found
ICNSS core still bound and WLAN module sysfs still present, but no direct
WLFW/firmware-ready state file, no ICNSS debugfs directory, no readiness kernel
log history, and no WLAN netdev/wiphy.

## References Used

- Qualcomm ICNSS source shows WLFW QMI indication registration, firmware-ready
  event handling, and host-driver probe gating through `icnss_register_driver()`:
  https://android.googlesource.com/kernel/msm/+/android-7.1.0_r0.2/drivers/soc/qcom/icnss.c
- Qualcomm ICNSS QMI source shows WLFW service connection state logging:
  https://android.googlesource.com/kernel/msm/+/79a5a3af469e5d38c649dbe3dc7340d96990fd68/drivers/soc/qcom/icnss_qmi.c
- Qualcomm ICNSS devicetree binding describes WLAN FW communication over QMI
  and WLAN on/off messages:
  https://android.googlesource.com/kernel/msm/+/157ab4a1b7d2bf3275a20ee90d855bec184d742e/Documentation/devicetree/bindings/cnss/icnss.txt
- Linux debugfs documentation notes that debugfs is not a stable ABI and allows
  arbitrary driver-defined files, so v282 did not mount or write debugfs:
  https://docs.kernel.org/filesystems/debugfs.html
- Linux driver binding documentation is the reference for interpreting sysfs
  driver/device links:
  https://docs.kernel.org/driver-api/driver-model/binding.html

## Live Result

Command:

```bash
python3 scripts/revalidation/wifi_icnss_wlfw_readiness_surface.py \
  --out-dir tmp/wifi/v282-icnss-wlfw-readiness-surface \
  run
```

Result:

```text
decision: icnss-readiness-sysfs-candidates-limited
pass: True
reason: sysfs has state-looking ICNSS/WLAN paths but no direct firmware-ready state
```

## Captured State

| field | value |
| --- | --- |
| ICNSS compatible | `qcom,icnss` |
| ICNSS driver-device link | present |
| QCA6390 compatible | `qcom,cnss-qca6390` |
| QCA6390 driver link | absent |
| WLAN module sysfs | present |
| WLAN module loaded in `/proc/modules` | no |
| WLAN params | `fwpath=""`, `country_code=(null)`, `con_mode=0` |
| ICNSS params | `quirks=128`, `dynamic_feature_mask=1` |
| `CONFIG_ICNSS` / `CONFIG_ICNSS_QMI` | `y` / `y` |
| `CONFIG_ICNSS_DEBUG` | `n` |
| `CONFIG_DEBUG_FS` | `y` |
| debugfs mounted | no |
| `/sys/kernel/debug/icnss` | absent |
| `/sys/kernel/shutdown_wlan` | present but not readable |
| ICNSS/WLFW readiness dmesg lines | `0` |
| WLAN netdev/wiphy | absent |
| target CNSS process | clean |

Readiness-looking sysfs candidates were limited to generic runtime power,
ramdump, and WLAN parameter paths:

- `/sys/devices/platform/soc/18800000.qcom,icnss/power/runtime_status`
- `/sys/devices/platform/soc/18800000.qcom,icnss/ramdump/ramdump_wcss_msa0`
- `/sys/devices/platform/soc/18800000.qcom,icnss/ramdump/ramdump_wcss_msa0/power/runtime_status`
- `/sys/devices/platform/soc/18800000.qcom,icnss/ramdump/ramdump_wcss_msa0/power/control`
- `/sys/module/wlan/parameters/fwpath`

These are not direct WLFW firmware-ready state surfaces.

## Postflight

Postflight after the observer:

- `status`: PASS, shell responsive, selftest `fail=0`
- `run /cache/bin/toybox pidof cnss-daemon`: rc `1`, no target daemon
- `cat /proc/net/dev`: only existing baseline interfaces including `ncm0`; no
  `wlan*`

## Interpretation

- The live kernel still matches the v281 model: ICNSS core is bound and WLAN host
  driver surfaces exist, but firmware-ready/host-driver probe completion is not
  exposed as a stable read-only file in the current no-start state.
- `CONFIG_DEBUG_FS=y` alone is not enough: debugfs is not mounted and
  `CONFIG_ICNSS_DEBUG=n`, so an ICNSS debugfs readiness tree is not visible.
- `/sys/kernel/shutdown_wlan` exists but is not a useful read-only state file.
- v282 did not create any new readiness surface and did not alter Wi-Fi state.

## Guardrails Observed

- no daemon/service start
- no QRTR nameservice packet or QMI payload
- no Wi-Fi scan/connect/link-up/credential/DHCP/routing
- no rfkill unblock, ICNSS bind/unbind, `driver_override`, recovery, ramdump, or
  assert controls
- no sysfs/debugfs/configfs/control writes
- no debugfs mount
- no reboot or remount

## Next Work

The next useful step is not a generic debugfs inventory by default. Because ICNSS
debugfs is absent and `CONFIG_ICNSS_DEBUG=n`, v283 should be a bounded
start-only readiness-delta observer:

- reuse the validated v261/v279 CNSS start-only primitive;
- capture before/during/after ICNSS/WLFW/QMI dmesg, ICNSS sysfs candidates, and
  WLAN readiness surfaces;
- keep QMI payloads, QRTR nameservice packets, scan/connect/link-up, rfkill
  writes, and ICNSS bind/unbind blocked;
- require clean postflight: no `cnss-daemon`, no `wlan*`, no wiphy unless the
  test explicitly classifies a transient readiness delta and cleanup succeeds.
