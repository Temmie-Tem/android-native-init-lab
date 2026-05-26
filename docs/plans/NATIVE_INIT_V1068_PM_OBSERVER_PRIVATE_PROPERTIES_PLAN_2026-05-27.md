# Native Init V1068 PM Observer Private Properties Plan

## Goal

Repair the V1067 PM observer namespace gap where the service-manager trio had
binder devices but no private `/dev/__properties__` tree.

## Background

V1067 proved `/dev/binder`, `/dev/hwbinder`, and `/dev/vndbinder` were
materialized for `wifi-companion-pm-service-trigger-observer`, but the same
transcript showed:

```text
context.dev_properties.exists=0
libc: Using old property service protocol ("ro.property_service.version" is not set)
servicemanager signal=6
vndservicemanager signal=6
```

Older service-manager start-only evidence used a private property area and kept
`servicemanager`/`hwservicemanager` alive until timeout. The minimal V1068 fix is
to include PM observer mode in `materialize_private_properties()`.

## Gate

- Build static `a90_android_execns_probe v186`.
- Deploy only `/cache/bin/a90_android_execns_probe` over NCM.
- Re-run bounded PM observer with the existing V1066 runner and V1068 helper.

## Forbidden

- No `mdm_helper` start.
- No CNSS daemon start.
- No Wi-Fi HAL start.
- No scan/connect/DHCP/route/external ping.
- No `/dev/esoc*` or subsystem trigger.
- No boot image write or reboot unless cleanup is required.

## Success Criteria

- Helper v186 builds as static aarch64 and deploys with matching sha256.
- PM observer transcript shows `context.dev_properties.exists=1`.
- Old property-service protocol warning disappears.
- Postflight remains safe with no forbidden actor or Wi-Fi bring-up action.

## Failure Criteria

- Private property area is still absent.
- Service-manager trio still aborts after private property repair.
- Any forbidden actor/action appears in transcript or postflight scan.
