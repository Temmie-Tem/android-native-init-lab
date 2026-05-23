# Native Init V674 Post-HAL/wificond Classifier

- cycle: `v674`
- date: `2026-05-24`
- runner: `scripts/revalidation/native_wifi_post_hal_wificond_classifier_v674.py`
- evidence: `tmp/wifi/v674-post-hal-wificond-classifier/`
- decision: `v674-post-hal-property-binder-gap-classified`
- pass: `true`
- class: host-only

## Scope

V674 classifies the V673 V671-arm evidence after Wi-Fi HAL legacy/ext,
`wificond`, and fresh `cnss-daemon` have started. It performs no device command,
no live service start, no supplicant, no scan/connect, no DHCP, no route change,
and no external ping.

## Findings

| area | result |
| --- | --- |
| service `74/180` | present |
| Wi-Fi HAL legacy/ext | started, observable, cleanup-safe |
| `wificond` | started, observable, cleanup-safe |
| fresh `cnss-daemon` retry | started, observable, cleanup-safe |
| UID/GID/capability setup | pass |
| SELinux exec context setup | pass |
| Binder/HwBinder FD surface | present |
| property service shim | present, one allowed request |
| WLFW/BDF/firmware-ready/`wlan0` | absent |
| property context lookup failures | present |
| binder transaction/ioctl failures | present |

## Interpretation

The immediate blocker is no longer service `74/180`, process identity,
capability setup, SELinux domain transition, or basic Binder/HwBinder device
materialization. Those surfaces are present in the V673 V671 arm.

The next blocker is post-HAL runtime integration:

- the helper captured many property context lookup failures from Android
  userspace libraries;
- dmesg still shows Binder transaction/ioctl failures from service-manager,
  hwservicemanager, `wificond`, and `cnss-daemon`;
- WLFW service `69`, BDF download, firmware-ready indication, and `wlan0`
  remain absent.

This keeps Wi-Fi connection attempts premature. The next live unit should repair
or capture property/binder registration behavior before enabling supplicant or
scan/connect.

## Next Step

Plan V675 around a targeted property/binder runtime repair or capture:

1. compare Android property files/property contexts against the private runtime;
2. verify which required property lookups need real values rather than log-only
   keys;
3. capture service-manager/HwBinder registration visibility after HAL and
   `wificond` start;
4. only move to scan/connect after WLFW/BDF/`wlan0` appears.
