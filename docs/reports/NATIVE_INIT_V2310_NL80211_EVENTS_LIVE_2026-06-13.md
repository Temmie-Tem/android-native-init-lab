# Native Init V2310 NL80211 Events Live Validation

## Summary

- Cycle: `V2310`
- Track: Active epic / E1 nl80211 multicast event subscription.
- Decision: `v2310-nl80211-events-live-pass`
- Result: PASS to the current validation ceiling.
- Resident after run: `A90 Linux init 0.9.274 (v2310-nl80211-events)`
- Rollback checkpoint remains: `A90 Linux init 0.9.268 (v2237-supplicant-terminate-poll)`.
- Source/build report: `docs/reports/NATIVE_INIT_V2310_NL80211_EVENTS_SOURCE_BUILD_2026-06-13.md`
- Private live artifact dir: `workspace/private/runs/wifi/v2310-nl80211-events-live-20260613-134846`

## Artifact Identity

- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2310_nl80211_events.img`
- Boot SHA256: `3908aaeec9cc215ce185aecfca38058fcf12cd41e080d1179798ebbcaf9b2280`
- Init SHA256: `03f22440aabdec46f0636277f1c6cb0e6800e9906e02cbea44031dcd8a6c1806`
- Helper SHA256: `062c7a491bee66bcb7112850f4581e53e58d923719d85dbbe651d9df285ee910`
- Init version: `0.9.274`
- Build tag: `v2310-nl80211-events`

## Static Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/build_native_init_boot_v2310_nl80211_events.py tests/test_build_native_init_boot_v2310_nl80211_events.py` — PASS.
- `python3 -m unittest discover -s tests -p 'test_build_native_init_boot_v2310_nl80211_events.py'` — PASS (`3` tests).
- `python3 workspace/public/src/scripts/revalidation/build_native_init_boot_v2310_nl80211_events.py` — PASS; produced the boot image above.
- `file` confirmed the native init and helper are static AArch64 ELF binaries; boot image is an Android boot image.
- `python3 -m unittest discover -s tests -p 'test_*.py'` — PASS (`978` tests).
- `git diff --check` — PASS.

## Flash / Health Validation

Flashed only the boot image via `workspace/public/src/scripts/revalidation/native_init_flash.py` with pinned SHA256 and `--verify-protocol selftest`.

- Recovery handoff from V2309 native init: PASS.
- ADB recovery ready: PASS.
- Remote image SHA256: matched `3908aaeec9cc215ce185aecfca38058fcf12cd41e080d1179798ebbcaf9b2280`.
- Boot partition write/readback SHA256: matched `3908aaeec9cc215ce185aecfca38058fcf12cd41e080d1179798ebbcaf9b2280`.
- Post-boot `selftest`: `fail=0`.
- Post-boot `version`: `A90 Linux init 0.9.274 (v2310-nl80211-events)`.
- Auto-rollback was not needed.

## Device Command Results

All commands were read-only and used the serial bridge through `a90ctl.py`.

- `version`: rc `0`, reported `0.9.274 (v2310-nl80211-events)`.
- `status`: rc `0`, `BOOT OK`, storage SD backend writable, transport tcpctl ready.
- `selftest verbose`: rc `0`, `pass=11 warn=1 fail=0`.
- `wifi status`: rc `0`, `wlan0_present=0`; no scan/connect was started.
- `wifi events 1000`: rc `0`, `socket_open=1`, `family_id=19`, `mcast_group_count=7`, `mlme`/`scan`/`config` group IDs resolved and all three groups joined, `event_count=0`, decision `wifi-events-timeout-no-events`.
- `wifi netevents 1000`: rc `0`, existing V2309 rtnetlink monitor still opens and times out cleanly.

## E1 Validation Ceiling

This validates the E1 infrastructure available without credentials:

- `CTRL_CMD_GETFAMILY` for `nl80211` works.
- `CTRL_ATTR_MCAST_GROUPS` parsing works.
- `NETLINK_ADD_MEMBERSHIP` succeeds for `mlme`, `scan`, and `config` groups.
- The bounded event loop exits cleanly with no events when no Wi-Fi action is performed.
- Output and logs keep `raw_bssid_redacted=1`, `raw_ip_redacted=1`, and `secret_values_logged=0`.

The full E1 assertion — one bounded `wifi connect` producing `NL80211_CMD_CONNECT` and matching polled carrier — remains parked because Wi-Fi credentials are absent. Per `GOAL.md`, this does not block implementation or boot-health validation, and it does not promote a new safety rollback baseline.

## Safety Scope

No Wi-Fi scan, connect, DHCP, route change, external ping, credentials, kernel module/code change, closed kernel-observation/security work, eSoC/PCIe/MHI/GDSC/PMIC/GPIO path, platform bind/unbind, or forbidden partition write was performed. The only device write was the approved boot-partition flash via the checked helper. `v2237` remains the rollback target.
