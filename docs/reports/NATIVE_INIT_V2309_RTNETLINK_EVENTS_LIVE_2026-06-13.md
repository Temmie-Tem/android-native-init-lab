# Native Init V2309 RTNETLINK Events Live Validation

Date: 2026-06-13
Scope: Active epic / E2 rtnetlink link-address monitor. Boot-partition-only test image flash, health check, and bounded non-credential event validation.
Resident before flash: `A90 Linux init 0.9.268 (v2237-supplicant-terminate-poll)`.
Rollback target remains: `v2237-supplicant-terminate-poll`.

## Artifact

- Build tag: `v2309-rtnetlink-events`
- Native init: `A90 Linux init 0.9.273 (v2309-rtnetlink-events)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2309_rtnetlink_events.img`
- Boot SHA256: `d1552d5bbafffe64c43ebca85f6fb7cd77bb080f640580e155f0b9ec4bd27718`
- Init SHA256: `495378bace1c219f98e05778376f09020b110bb70e48db5426cb71f62ed80c51`
- Source-build report: `docs/reports/NATIVE_INIT_V2309_RTNETLINK_EVENTS_SOURCE_BUILD_2026-06-13.md`
- Build manifest: `workspace/private/builds/native-init/v2309-rtnetlink-events/manifest.json` (private)

## Selection

- `GOAL.md` active epic selected E2 first because Wi-Fi credentials are absent.
- T1 is saturated and kernel security/observation phases are closed; neither was reopened.
- E1 nl80211 connect-event validation remains parked until credentials are present.

## Flash Gate

- Rollback image confirmed: `workspace/private/inputs/boot_images/boot_linux_v2237_supplicant_terminate_poll.img`, SHA256 `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`.
- Deeper fallback confirmed: `workspace/private/inputs/boot_images/boot_linux_v48.img`.
- Flash path: checked helper `workspace/public/src/scripts/revalidation/native_init_flash.py` only.
- Partition touched: boot only.
- TWRP/recovery handoff: completed through the checked helper.

## Static Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/build_native_init_boot_v2309_rtnetlink_events.py tests/test_build_native_init_boot_v2309_rtnetlink_events.py`: PASS
- `python3 -m unittest discover -s tests -p 'test_build_native_init_boot_v2309_rtnetlink_events.py'`: PASS, 3 tests
- `python3 -m unittest discover -s tests -p 'test_*.py'`: PASS, 975 tests
- Build script: PASS; produced static AArch64 init and boot image.
- `file workspace/private/builds/native-init/v2309-rtnetlink-events/init_v2309_rtnetlink_events`: static AArch64 ELF.
- `git diff --check`: PASS

## Device Validation

### Boot and health

- `native_init_flash.py ... --from-native --verify-protocol selftest`: PASS
- Version after boot: `A90 Linux init 0.9.273 (v2309-rtnetlink-events)`
- `status`: PASS
- `selftest verbose`: `pass=11 warn=1 fail=0`
- Post-validation netservice status: NCM present and tcpctl running; local NCM address redacted.
- Post-validation version: still `0.9.273 (v2309-rtnetlink-events)`.

### `wifi status`

- Command: `wifi status`
- Result: PASS
- Observed no `wlan0` because this validation did not start Wi-Fi, scan, connect, DHCP, or ping.
- `secret_values_logged=0`
- Saved SSID/profile names, MACs, BSSIDs, and IP literals are not reproduced in this report.

### `wifi netevents` idle check

- Command: `wifi netevents 1000`
- Result: PASS
- `socket_open=1`
- `event_count=0`
- `rc=0`
- Decision: `wifi-netevents-timeout-no-events`
- Interpretation: rtnetlink socket bind/subscription works and a no-event timeout is handled as a successful read-only observation.

### `wifi netevents` event check

Validation method: schedule one bounded local `ncm0` down/up transition, then run `wifi netevents 5000`.

- Toggle scope: `ncm0` only; serial ACM stayed available.
- Persistent network configuration: not changed.
- Wi-Fi scan/connect/DHCP/ping: not run.
- Event command: `wifi netevents 5000`
- Result: PASS
- `socket_open=1`
- `event_count=2`
- `stored_count=2`
- Event 0: `type=newlink`, `iface=ncm0`, `operstate=down`, `raw_ip_redacted=1`
- Event 1: `type=newlink`, `iface=ncm0`, `operstate=up`, `carrier=1`, `raw_ip_redacted=1`
- Decision: `wifi-netevents-events-observed`

## Safety Scope

No Wi-Fi credentials were read or logged. No Wi-Fi scan/connect/DHCP/ping was run. No route or DHCP configuration was created. No external ping was attempted. No kernel-security, kernel-observation, FastRPC, Binder, KGSL, `slub_debug`, eSoC, PCIe/MHI, GDSC, PMIC/GPIO, forbidden partition, firmware, EFS, or modem path was touched. The only flash operation was the checked boot-partition flash of the V2309 image.

## Decision

`v2309-rtnetlink-events-live-pass`

E2 is implemented and validated to its no-credential ceiling: the native-init `wifi netevents [timeout_ms]` command subscribes to rtnetlink link/address groups, opens successfully on device, handles idle timeout, and observes bounded `ncm0` link transitions. `v2237` remains the rollback target; V2309 is a validated test artifact, not a promoted safety rollback baseline.
