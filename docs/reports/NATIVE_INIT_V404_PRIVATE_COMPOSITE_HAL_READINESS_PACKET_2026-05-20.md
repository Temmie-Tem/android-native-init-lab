# Native Init v404 Private-Composite Wi-Fi HAL Readiness Packet

## Summary

V404 completed as a non-mutating readiness packet.

The packet confirms that the V402 private SELinux runtime proof and V403 service-manager pair start-only proof are sufficient to move to a composite helper/runner design. It does not approve or execute Wi-Fi HAL start, `wificond`, supplicant, hostapd, CNSS/diag, scan/connect/link-up, credentials, DHCP, routing, rfkill, firmware mutation, Android partition writes, or persistent daemons.

## Evidence

- V404 packet run: `tmp/wifi/v404-private-composite-hal-readiness-packet-fixed-20260520-090542/`
- V404 manifest: `tmp/wifi/v404-private-composite-hal-readiness-packet-fixed-20260520-090542/manifest.json`
- V404 summary: `tmp/wifi/v404-private-composite-hal-readiness-packet-fixed-20260520-090542/summary.md`
- V402 private proof input: `tmp/wifi/v402-private-selinux-surface-live-20260520-084832/manifest.json`
- V403 live input: `tmp/wifi/v403-service-manager-start-only-retry-live-20260520-085702/manifest.json`
- V210 vendor asset input: `tmp/wifi/v210-vendor-asset-classifier/manifest.json`
- V216 service model input: `tmp/wifi/v216-service-replay-model/manifest.json`
- V287 service-order input: `tmp/wifi/v287-wifi-service-order-replay-model/manifest.json`

Result:

```text
decision: v404-private-composite-hal-readiness-packet-ready
pass: True
reason: private-composite HAL readiness packet ready; HAL start still requires V405 implementation and separate approval
next_step: implement V405 composite helper/runner approval packet
first_hal_candidate: vendor.wifi_hal_ext
live_execution_approved: False
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

## Confirmed Inputs

| input | decision | status |
| --- | --- | --- |
| V402 private runtime proof | `private-selinux-surface-proof-pass` | pass |
| V403 service-manager live | `service-manager-start-only-live-pass` | pass |
| V403 postflight | `service-manager-start-only-live-preflight-ready` | pass |
| V210 vendor assets | `firmware-path-policy-needed` | pass |
| V216 service model | `replay-model-ready` | pass |
| V287 service order | `wifi-service-order-replay-model-ready` | pass |
| V364 global gate refresh | `hal-service-readiness-blocked` | context only |

## Readiness Checks

All blocker checks passed:

- native version and health are current: `A90 Linux init 0.9.61 (v319)`, `status/selftest fail=0`.
- helper v22 is deployed at `/cache/bin/a90_android_execns_probe` with SHA `55f83cfa43ebc69ab37b3181262fbdf0e3ed6b5b11f0e41e63d3b56e7ea080e6`.
- no leftover service-manager process, Wi-Fi process, or Wi-Fi link was observed.
- `/mnt/system/system/bin/servicemanager` and `/mnt/system/system/bin/hwservicemanager` are visible.
- V210 proves both HAL service blocks, init rc files, binaries, and VINTF entries exist in the vendor-root evidence.

Action still needed:

```text
composite-helper-needed: current helper starts one target per invocation; HAL start-only needs one helper-owned namespace supervising service-manager + hwservicemanager + one HAL candidate
```

This is the V405 implementation target, not a V404 blocker.

## HAL Boundary

First candidate:

- service: `vendor.wifi_hal_ext`
- binary: `/vendor/bin/hw/vendor.samsung.hardware.wifi@2.0-service`
- capabilities from V210/V287: `NET_ADMIN`, `NET_RAW`, `SYS_MODULE`
- interfaces from V210: `vendor.samsung.hardware.wifi@2.0::ISehWifi`, `@2.1::ISehWifi`, `@2.2::ISehWifi`

Sibling fallback:

- service: `vendor.wifi_hal_legacy`
- binary: `/vendor/bin/hw/android.hardware.wifi@1.0-service`
- capabilities from V210/V287: `NET_ADMIN`, `NET_RAW`, `SYS_MODULE`
- interfaces from V210: `android.hardware.wifi@1.0::IWifi` through `@1.4::IWifi`

`wificond` is visible but remains later than the first HAL start-only boundary.

## Interpretation

V404 does not mean Wi-Fi is ready to bring up. It means the next technically correct step is no longer another global readiness probe.

The old V364-style global/current gate still sees blockers such as missing global Binder/property/linker visibility and absent `/mnt/system/vendor` paths. V403 and V404 show the correct model is the helper-owned private namespace with temporary vendor/root materialization. Therefore V405 should implement one bounded composite runtime rather than start pieces in separate invocations.

## Next Target

Proceed to V405: composite helper/runner approval packet.

V405 should define and guard a bounded start-only attempt where one helper-owned private namespace supervises:

- `servicemanager`
- `hwservicemanager`
- first HAL candidate `vendor.wifi_hal_ext`

Still excluded until later explicit stages:

- Wi-Fi scan/connect/link-up.
- credentials and supplicant association.
- DHCP/routing/default route.
- hostapd/AP mode.
- CNSS/diag lifecycle changes.
- rfkill, ICNSS bind/unbind, module load/unload, firmware mutation.
