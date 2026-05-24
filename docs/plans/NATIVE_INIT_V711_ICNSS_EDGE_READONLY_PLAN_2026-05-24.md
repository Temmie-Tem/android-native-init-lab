# Native Init V711 ICNSS Edge Read-Only Plan

- date: `2026-05-24 KST`
- cycle: `v711`
- type: current-state read-only classifier

## Goal

Rebase the V710 QCA6390/WLFW event-source result onto the actual ICNSS kernel
model and prevent the next work from drifting into unsafe or unsupported
`qca6390` bind writes.

The intended classification is:

```text
ICNSS core bound + QCA6390 context visible
  + V710 service 180/74 + provider + CNSS retry poll wait
  - ICNSS-QMI/WLFW/BDF/FW-ready/wlan0
  => target ICNSS-QMI/WLFW readiness edge, not qca bind/unbind
```

## Scope

Allowed:

- read current `/sys/bus/platform` ICNSS/QCA6390 directories;
- read current `/sys/module/icnss` and `/sys/module/wlan` parameter surfaces;
- read current `/proc/net/dev`, `/proc/net/qrtr`, `/proc/net/netlink`, focused
  `/proc/interrupts`, and focused dmesg tail;
- combine current read-only data with V710 and Android V703 evidence.

Forbidden:

- daemon, service-manager, Wi-Fi HAL, supplicant, wificond, or hostapd start;
- Wi-Fi scan/connect/link-up or credential use;
- DHCP, route changes, or external ping;
- sysfs/debugfs/control writes, including ICNSS bind/unbind, `driver_override`,
  recovery, ramdump, assert, rfkill, or subsystem state writes;
- boot image or partition writes.

## Success Criteria

- current device remains responsive before/after read-only capture;
- ICNSS core device and driver link are visible;
- QCA6390 context node remains visible but is treated as context only;
- WLAN module parameters are visible but `wlan0` is absent;
- V710 input remains the latest post-service74 pre-WLFW blocker;
- output explicitly routes V712 toward ICNSS-QMI/WLFW readiness capture, with
  bind/unbind and connect path still blocked.

## Next Gate

If V711 passes, implement V712 as a helper/window capture that samples the
ICNSS-QMI/WLFW event source during the known service `180/74` positive provider
window. V712 must still avoid Wi-Fi HAL, scan/connect, credentials, DHCP, and
external ping until WLFW/BDF or `wlan0` advances.
