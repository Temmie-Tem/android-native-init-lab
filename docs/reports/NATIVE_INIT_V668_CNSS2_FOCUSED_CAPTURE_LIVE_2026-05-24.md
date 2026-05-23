# Native Init V668 cnss2 Focused Capture Live Report

- date: `2026-05-24 KST`
- status: `live-pass`; Wi-Fi external ping is **not** complete
- helper: `a90_android_execns_probe v110`
- runner: `scripts/revalidation/native_wifi_cnss2_focused_capture_v668.py`
- live evidence: `tmp/wifi/v668-cnss2-focused-capture-live/`
- decision: `v668-cnss2-focused-capture-gap-classified`

## Scope

V668 reruns the V666 service `74` positive companion/CNSS retry path with helper
v110. The only added behavior is read-only focused capture of the cnss2/icnss
surface immediately after service `74` opens and again during the active
companion/CNSS retry window.

The live proof remains below Wi-Fi bring-up. It does not start the Wi-Fi HAL,
does not scan, does not connect or link up, does not run DHCP, does not change
routes, and does not perform an external ping.

## Prerequisites

Current-boot prerequisites were refreshed before the V668 live proof:

| prerequisite | result |
| --- | --- |
| V641 clean DSP one-shot refresh | pass via timeline/log state |
| V401 SELinuxfs runtime mount surface | pass |
| V490 native SELinux policy-load proof | pass |
| V668 preflight after firmware mount cleanup | ready |

Two operator-facing details matter for repeatability:

- V641 leaves `/vendor/firmware_mnt` and `/vendor/firmware-modem` mounted after
  the clean-DSP refresh; V668 preflight expects a clean mount start, so those
  read-only mounts must be unmounted before the V668 preflight/live runner.
- The first V401 attempt hit the auto menu and returned busy; hiding the menu
  before rerun produced the expected SELinuxfs status-page proof.

## Live Result

The bounded live proof passed its safety contract:

| key | value |
| --- | --- |
| decision | `v668-cnss2-focused-capture-gap-classified` |
| pass | `True` |
| device_mutations | `True` |
| daemon_start_executed | `True` |
| wifi_bringup_executed | `False` |
| external_ping_executed | `False` |
| focused_capture_ready | `True` |

Post-cleanup serial checks confirmed the native shell returned after reboot.

## Focused cnss2 Surface

Both focused capture phases completed:

| phase | icnss driver | icnss device | QCA6390 device | net class | wlan0 | debug icnss | value captures |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `service74_open` | `1` | `1` | `1` | `1` | `0` | `0` | `8` |
| `window` | `1` | `1` | `1` | `1` | `0` | `0` | `8` |

The captured device power attributes were unchanged across both phases:

| path class | `power/control` | `power/runtime_status` |
| --- | --- | --- |
| `18800000.qcom,icnss` | `auto` | `unsupported` |
| `a0000000.qcom,cnss-qca6390` | `auto` | `unsupported` |

The helper also confirmed the platform devices exist:

- `/sys/bus/platform/drivers/icnss` contains `18800000.qcom,icnss`.
- `/sys/bus/platform/devices/18800000.qcom,icnss` is present.
- `/sys/bus/platform/devices/a0000000.qcom,cnss-qca6390` is present.
- `/sys/class/net/wlan0` is absent in both capture phases.
- `/sys/kernel/debug/icnss` is absent or not exposed in the native surface.

## Marker Delta

V668 reproduced the lower service publication positives, but did not advance
into WLFW/BDF/`wlan0`:

| marker | count |
| --- | --- |
| service-notifier `180` | `1` |
| service-notifier `74` | `1` |
| `cnss-daemon` netlink | `10` |
| `cnss-daemon` `cld80211` | `4` |
| binder ioctl unsupported | `2` |
| binder transaction failed | `1` |
| `cnss-daemon` binder transaction failed | `1` |
| QMI server connected | `0` |
| WLFW start | `0` |
| WLFW service request | `0` |
| WLAN-PD | `0` |
| BDF `regdb` | `0` |
| BDF `bdwlan` | `0` |
| WLAN firmware ready | `0` |
| `wlan0` | `0` |
| kernel warning | `1` |

The warning is the known service `74`-adjacent duplicate `pm_qos_add_request`
class. V668 keeps it visible as a remaining attribution item.

## Interpretation

V668 supports the refined dependency model:

```text
modem ONLINE
  -> service-locator can resolve WLAN-PD
  -> service-notifier 180/74 appear
  -> cnss2/icnss should progress QCA6390/WLFW
  -> WLFW service 69, BDF, firmware-ready, wlan0
```

The first two steps are positive again, and the icnss/QCA6390 platform devices
are visible. However, the service `74` open window does not produce `wlan0`,
WLFW service `69`, BDF download, or explicit cnss2/QCA6390 runtime progression
markers.

This reduces the likelihood that the remaining blocker is the mere absence of
the icnss/QCA6390 sysfs devices. The next gate should compare the focused
service74/window sysfs captures against Android and decide whether the missing
piece is a cnss2 notifier callback, an unexposed runtime/debug state transition,
PCIe/MHI power sequencing, or another Android init side effect that happens
after service-notifier `180/74`.

## Next Gate

Plan V669 as a host-only or read-only Android/native delta classifier:

- compare V668 focused icnss/QCA6390 sysfs values with Android boot captures;
- search captured Android dmesg for cnss2/icnss/QCA6390/MHI/PCIe markers after
  service-notifier `180/74`;
- keep Wi-Fi HAL, scan/connect, DHCP, credentials, routes, and external ping
  blocked until WLFW/BDF/`wlan0` evidence advances.
