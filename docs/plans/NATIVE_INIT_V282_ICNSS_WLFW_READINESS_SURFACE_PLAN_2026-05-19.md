# Native Init v282 ICNSS/WLFW Readiness Surface Plan

## Summary

- target: v282 read-only ICNSS/WLFW readiness surface observer
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- new tool: `scripts/revalidation/wifi_icnss_wlfw_readiness_surface.py`
- packet transmission: none
- daemon execution: none
- QMI payload: none
- sysfs/debugfs/control writes: none
- debugfs mount: none by default

v281 established that the live model is ICNSS core plus WLAN host-driver
registration, with host-driver probe waiting on firmware-ready/WLFW/QMI state.
v282 does not retry daemon start. It first asks a narrower question: does native
read-only state expose any stable ICNSS/WLFW readiness surface that can guide the
next controlled experiment?

## References

- Qualcomm ICNSS source shows WLFW QMI indication registration, firmware-ready
  event handling, and host-driver probe gating through `icnss_register_driver()`:
  https://android.googlesource.com/kernel/msm/+/android-7.1.0_r0.2/drivers/soc/qcom/icnss.c
- Qualcomm ICNSS QMI source shows WLFW service connection state logging:
  https://android.googlesource.com/kernel/msm/+/79a5a3af469e5d38c649dbe3dc7340d96990fd68/drivers/soc/qcom/icnss_qmi.c
- Qualcomm ICNSS devicetree binding describes WLAN FW communication over QMI
  and WLAN on/off messages:
  https://android.googlesource.com/kernel/msm/+/157ab4a1b7d2bf3275a20ee90d855bec184d742e/Documentation/devicetree/bindings/cnss/icnss.txt
- Linux debugfs documentation warns that debugfs is not a stable ABI and has no
  strict file rules, so v282 only inventories names and does not mount or write
  debugfs:
  https://docs.kernel.org/filesystems/debugfs.html
- Linux driver binding documentation remains the reference for sysfs
  driver/device link evidence:
  https://docs.kernel.org/driver-api/driver-model/binding.html

## Scope

Read-only captures:

- ICNSS platform node, `uevent`, driver, and driver-device link
- QCA6390 context and driver-link state
- WLAN and ICNSS module parameter surfaces
- `/proc/mounts`, existing `/sys/kernel/debug`, and existing
  `/sys/kernel/debug/icnss` names only
- `/sys/kernel/shutdown_wlan` presence/readability
- selected config keys from `/proc/config.gz`
- filtered kernel log tail for ICNSS/WLFW/QMI/firmware-ready messages
- process table and WLAN readiness surfaces

## Decision Model

Expected likely decision:

```text
icnss-readiness-surface-limited
```

This means ICNSS binding is present, but no direct read-only WLFW firmware-ready
state file is visible.

Alternative decisions:

- `icnss-wlfw-readiness-surface-visible`: WLAN netdev/wiphy appeared.
- `icnss-debugfs-readiness-candidates-visible`: existing debugfs exposes
  ICNSS readiness-looking entries without mounting debugfs.
- `icnss-wlfw-readiness-log-only`: kernel logs expose readiness history, but no
  stable state file exists.
- `icnss-readiness-sysfs-candidates-limited`: sysfs has state-looking paths, but
  no direct firmware-ready state.
- `icnss-wlfw-readiness-incomplete`: required read-only evidence is missing.

## Guardrails

v282 must not:

- start `cnss-daemon`, `cnss_diag`, HAL, supplicant, wificond, or hostapd
- transmit QRTR nameservice packets or QMI request payloads
- perform Wi-Fi scan/connect/link-up/credential/DHCP/routing
- write to sysfs, debugfs, configfs, rfkill, ICNSS bind/unbind,
  `driver_override`, recovery, ramdump, or assert controls
- mount debugfs by default
- mutate firmware paths or Android partitions
- reboot or remount

## Validation

Static:

```bash
python3 -m py_compile \
  scripts/revalidation/wifi_icnss_wlfw_readiness_surface.py \
  scripts/revalidation/a90ctl.py

git diff --check
```

Live read-only:

```bash
python3 scripts/revalidation/wifi_icnss_wlfw_readiness_surface.py \
  --out-dir tmp/wifi/v282-icnss-wlfw-readiness-surface \
  run
```

Postflight:

```bash
python3 scripts/revalidation/a90ctl.py --json version
python3 scripts/revalidation/a90ctl.py status
python3 scripts/revalidation/a90ctl.py run /cache/bin/toybox pidof cnss-daemon || true
python3 scripts/revalidation/a90ctl.py cat /proc/net/dev
```

## Acceptance

- v282 starts no daemon, sends no QRTR/QMI packets, and performs no writes.
- readiness candidates are classified from existing sysfs/debugfs names and
  kernel log history only.
- postflight remains clean: no `cnss-daemon`, no `wlan*` interface.
- the result determines whether v283 should be debugfs opt-in inventory,
  start-only readiness-delta observation, or another read-only blocker analysis.
