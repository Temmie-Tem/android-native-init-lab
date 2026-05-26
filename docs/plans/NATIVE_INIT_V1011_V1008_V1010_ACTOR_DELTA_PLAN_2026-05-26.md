# V1011 V1008/V1010 Actor Delta Plan

## Goal

Compare the V1008 full service-window fd-negative route with the V1010 reduced
service-defaults fd-positive route and choose the next live gate.

## Scope

1. Compare V1008 and V1010 manifests host-only.
2. Confirm V1010's `mdm_helper` service-defaults SELinux transition.
3. Confirm the `per_mgr` lifecycle delta:
   - V1008 full `per_mgr` exits `0`;
   - V1010 `per_mgr_light` remains alive during the fd-positive window.
4. Confirm helper source still contains the after-fd CNSS/service-manager matrix
   mode.
5. Select a bounded next live gate without running device commands.

## Guardrails

V1011 is host-only.

Forbidden:

- serial device command;
- Android boot or ADB command;
- actor start;
- `/dev/esoc-0`, `/dev/subsys_esoc0`, eSoC ioctl, GPIO, sysfs, or debugfs access;
- Wi-Fi scan/connect/link-up;
- credential use;
- DHCP/routes;
- external ping;
- boot image, partition, firmware, or filesystem mutation.

## Success Criteria

V1011 passes if it records:

- V1008 full service-window fd-negative evidence;
- V1010 reduced service-defaults fd-positive evidence;
- `per_mgr` lifecycle delta;
- availability of `wifi-companion-mdm-helper-cnss-service-manager-matrix`;
- no forbidden actions;
- a concrete V1012 route.

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_v1008_v1010_actor_delta_v1011.py
python3 scripts/revalidation/native_wifi_v1008_v1010_actor_delta_v1011.py
```
