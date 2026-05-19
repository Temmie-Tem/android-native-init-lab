# v365 Report: Service Runtime Repair Packet

- date: `2026-05-20`
- scope: no-daemon/no-link-up service runtime repair packet
- boot image change: none
- native baseline: `A90 Linux init 0.9.61 (v319)`
- plan: `docs/plans/NATIVE_INIT_V365_SERVICE_RUNTIME_REPAIR_PACKET_PLAN_2026-05-20.md`
- result: `PASS`, decision `service-runtime-repair-packet-ready`

## Summary

V365 turns the V364 blockers into a concrete V366 repair-smoke packet. It does
not execute the repair. It only verifies that the inputs required for a bounded,
no-daemon, no-Wi-Fi-link repair smoke are present.

The first live attempt correctly blocked because `/dev/block/sda29` did not
exist as a device node. The script was then corrected to classify this as a
repair candidate when `/proc/partitions` exposes `sda29` with verified
major/minor `259:13`. The second live run passed.

## Evidence

| item | path | decision |
| --- | --- | --- |
| plan mode | `tmp/wifi/v365-service-runtime-repair-packet-plan-20260520/` | `service-runtime-repair-packet-plan-ready` |
| first live mode | `tmp/wifi/v365-service-runtime-repair-packet-live-20260520/` | `service-runtime-repair-packet-blocked` |
| corrected live mode | `tmp/wifi/v365-service-runtime-repair-packet-live-20260520-r2/` | `service-runtime-repair-packet-ready` |

Corrected live summary:

```text
decision: service-runtime-repair-packet-ready
pass: True
reason: V366 no-daemon repair smoke packet is ready
next approval phrase: approve v366 bounded runtime repair smoke only; no service-manager start and no Wi-Fi bring-up
```

## Accepted Prerequisites

```text
v292: binder-open-only-smoke-pass
v320: private-property-lookup-getprop-pass
v362: start-only-pass
v364: hal-service-readiness-blocked
```

## Live Checks

| check | result |
| --- | --- |
| helper `/cache/bin/a90_android_execns_probe` | pass |
| real linkerconfig `/cache/bin/a90_real_ld.config.txt` | pass |
| real apex libraries config `/cache/bin/a90_real_apex.libraries.config.txt` | pass |
| private property root | pass |
| property files `properties_serial`, `property_info` | pass |
| system root `/mnt/system/system` | pass |
| system linker64 | pass |
| `servicemanager` binary | pass |
| `hwservicemanager` binary | pass |
| `/dev/block/sda29` | candidate via `mknodb /dev/block/sda29 259 13` |
| current Binder devnodes | clean / absent |
| current service-manager processes | clean / absent |
| current CNSS processes | clean / absent |
| Wi-Fi link surface | clean / absent |

## V366 Packet

Exact future approval phrase:

```text
approve v366 bounded runtime repair smoke only; no service-manager start and no Wi-Fi bring-up
```

Future command sketch:

```text
mkdir /dev/block
mknodb /dev/block/sda29 259 13
mknodc /dev/binder 10 81
mknodc /dev/hwbinder 10 80
mknodc /dev/vndbinder 10 79
run /cache/bin/a90_android_execns_probe --system-root /mnt/system/system --vendor-block /dev/block/sda29 --vendor-fstype ext4 --target-profile system-getprop --mode property-lookup --null-device-mode dev-null --property-root /mnt/sdext/a90/private-property-v317/dev/__properties__ --property-key ro.build.version.sdk --timeout-sec 10
run /cache/bin/toybox rm -f /dev/binder /dev/hwbinder /dev/vndbinder /dev/block/sda29
```

The sketch is not executed by V365.

## Guardrails

- No service-manager, Wi-Fi HAL, `wificond`, supplicant, hostapd,
  `cnss-daemon`, or `cnss_diag` was started.
- No Wi-Fi scan/connect/link-up was executed.
- No credential, DHCP, routing, rfkill unblock, ICNSS bind/unbind, firmware
  mutation, Android property write, or partition write was performed.

## Decision

- decision: `service-runtime-repair-packet-ready`
- next: V366 bounded runtime repair smoke, still no service-manager start and no
  Wi-Fi bring-up.
