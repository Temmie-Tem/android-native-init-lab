# Native Init V2311 Wi-Fi Event Module Live Validation

## Summary

- Cycle: `V2311`
- Track: T2 native-init / WLAN baseline improvement.
- Type: rollbackable boot-only native-init device validation.
- Decision: `v2311-wifi-event-module-live-pass`
- Result: PASS
- Resident artifact after validation: `A90 Linux init 0.9.275 (v2311-wifi-event-module)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2311_wifi_event_module.img`
- Boot SHA256: `77a450380dd37595ee0cb2bb6bd14c3cac5feb67b10c8b2cf8ac3d24a918680f`
- Rollback checkpoint remains: `v2237-supplicant-terminate-poll`

## Purpose

V2309 and V2310 added read-only rtnetlink and nl80211 event monitors to the native `wifi`
surface. V2311 keeps the command behavior unchanged but moves both monitor
implementations out of `a90_wifi.c` into `a90_wifi_events.c`.

This is a structural T2 cleanup with device validation, not a new Wi-Fi
functional claim. Wi-Fi credentials are absent, so connect/DHCP/ping validation
remains parked.

## Source Refactor

- `workspace/public/src/native-init/a90_wifi.c`: reduced to `3339` lines after moving event monitor code.
- `workspace/public/src/native-init/a90_wifi_events.c`: new `1030` line event monitor module.
- `wifi events [timeout_ms]` still dispatches to `a90_wifi_events_once`.
- `wifi netevents [timeout_ms]` still dispatches to `a90_wifi_netevents_once`.
- Default timeout macros now live in `a90_wifi.h`:
  - `A90_WIFI_NL80211_EVENT_DEFAULT_MS`
  - `A90_WIFI_NETEVENT_DEFAULT_MS`

## Static Validation

- Python compile:
  - `workspace/public/src/scripts/revalidation/build_native_init_boot_v2311_wifi_event_module.py`
  - `tests/test_build_native_init_boot_v2311_wifi_event_module.py`
- V2311 unit tests: PASS (`3` tests).
- Full test discovery: PASS (`981` tests).
- Build script: PASS.
- Artifact checks:
  - native init ELF: static AArch64 executable
  - helper ELF: static AArch64 executable
  - boot image: Android boot image
- `git diff --check`: PASS.

## Flash Gate

- Rollback image confirmed:
  - `workspace/private/inputs/boot_images/boot_linux_v2237_supplicant_terminate_poll.img`
  - SHA256 `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`
- Deeper fallback image confirmed:
  - `workspace/private/inputs/boot_images/boot_linux_v48.img`
- TWRP/recovery path confirmed through the checked flash helper.
- Flash helper: `workspace/public/src/scripts/revalidation/native_init_flash.py`
- Boot partition write only.
- Remote pushed image SHA and boot readback SHA matched the expected V2311 SHA.
- Auto-rollback was not needed.

## Live Validation

Evidence directory: `workspace/private/runs/wifi/v2311-wifi-event-module-live-20260613-140906-slow`

The first post-flash collection attempt hit serial echo truncation while parsing
`status`; it did not indicate a device-side command failure. The final evidence
collection used `a90ctl.py --input-mode slow` and passed cleanly.

### Health

- `version`: `A90 Linux init 0.9.275 (v2311-wifi-event-module)`
- `status`: `selftest: pass=11 warn=1 fail=0`
- `selftest verbose`: `pass=11 warn=1 fail=0`

### Wi-Fi Status

- Command: `wifi status`
- Result: PASS to no-credentials ceiling.
- `wlan0_present=0`
- `secret_values_logged=0`
- `decision=wifi-status-wlan0-missing`

`wlan0_present=0` is acceptable for this unit because the selected validation
does not start Wi-Fi, scan, connect, run DHCP, or ping. The purpose is to prove
the event command surfaces still work after the module split.

### nl80211 Events

- Command: `wifi events 1000`
- Result: PASS.
- `socket_open=1`
- `family_id=19`
- multicast groups discovered: `7`
- joined groups:
  - `mlme`
  - `scan`
  - `config`
- `groups_joined=3`
- `event_count=0`
- `secret_values_logged=0`
- `scan_attempted=0`
- `connect_attempted=0`
- `dhcp_attempted=0`
- `external_ping_attempted=0`
- `decision=wifi-events-timeout-no-events`

### rtnetlink Events

- Command: `wifi netevents 1000`
- Result: PASS.
- `socket_open=1`
- groups: `RTMGRP_LINK`, `RTMGRP_IPV4_IFADDR`
- ifaces monitored: `wlan0`, `ncm0`
- `event_count=0`
- `secret_values_logged=0`
- `connect_attempted=0`
- `dhcp_attempted=0`
- `external_ping_attempted=0`
- `decision=wifi-netevents-timeout-no-events`

## Safety Scope

No Wi-Fi scan, connect, DHCP, route change, external ping, credentials,
closed kernel-observation/security work, eSoC/PCIe/MHI/GDSC/PMIC/GPIO path,
platform bind/unbind, or forbidden partition write was performed. The only
device write was the approved boot-partition flash via the checked helper.

`v2237` remains the safety rollback target. V2311 is a validated resident test
artifact, not a promoted rollback checkpoint.

## Parked Validation

The full event-path functional assertion remains parked because Wi-Fi
credentials are absent:

- bounded `wifi connect`
- observed nl80211 `CONNECT` event
- carrier/status agreement
- DHCP
- ping

This does not block the V2311 structural refactor validation.
