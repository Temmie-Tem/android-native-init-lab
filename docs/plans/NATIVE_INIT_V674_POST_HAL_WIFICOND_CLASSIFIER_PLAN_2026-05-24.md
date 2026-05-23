# Native Init V674 Post-HAL/wificond Classifier Plan

- date: `2026-05-24 KST`
- cycle: `V674`
- status: planned
- runner: `scripts/revalidation/native_wifi_post_hal_wificond_classifier_v674.py`
- class: host-only evidence classifier

## Goal

V673 proved that the V671 Android-userspace path can pass service `74/180`, run
Wi-Fi HAL legacy/ext, run `wificond`, and run fresh `cnss-daemon`, while still
failing to advance WLFW/BDF/firmware-ready/`wlan0`. V674 classifies that
post-HAL gap using existing V673 evidence.

## Inputs

- `tmp/wifi/v673-same-helper-replay-live-retry2/manifest.json`
- `tmp/wifi/v673-same-helper-replay-live-retry2/arm-v671-v111/live/manifest.json`
- V671 arm `native/dmesg-delta.txt`

## Guardrails

V674 is host-only and does not authorize:

- device commands or live service starts;
- supplicant or hostapd start;
- scan/connect/link-up;
- credential use;
- DHCP, route change, or external ping;
- boot image or partition writes.

## Checks

| check | purpose |
| --- | --- |
| V673 post-HAL input ready | confirm V673 reached the intended V671 post-HAL surface |
| Android-userspace children started | confirm Wi-Fi HAL legacy/ext, `wificond`, and retry CNSS started |
| child preexec identity ready | verify UID/GID/capability/SELinux setup was not the immediate blocker |
| binder FD surface present | verify Binder/HwBinder device exposure for the started children |
| property shim observed | verify property service shim exists and is cleanup-safe |
| Wi-Fi lower markers absent | confirm WLFW/BDF/firmware-ready/`wlan0` did not advance |
| property/binder findings | identify the next runtime surface to repair or capture |

## Next

If property and binder findings are present, V675 should target property
contexts/property-area completeness and service-manager registration/binder
transaction visibility before any supplicant, scan/connect, DHCP, or external
ping attempt.
